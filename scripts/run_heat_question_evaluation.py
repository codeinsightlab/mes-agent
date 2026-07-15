#!/usr/bin/env python3
"""Evaluate the V1 heat-treatment business question set against current V2 reasoning."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Literal, cast

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.agents.heat_treatment.business_facts import (  # noqa: E402
    HEAT_TREATMENT_BUSINESS_FACTS,
)
from app.agent.capability.catalog.loader import CapabilityLoader  # noqa: E402
from app.agent.reasoning import CapabilityReasoner  # noqa: E402
from app.agent.reasoning.capability_reasoning.validator import (  # noqa: E402
    CapabilityReasoningValidator,
)
from app.agent.runtime.llm import LlmRuntime  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.infrastructure.agent.langchain_factory import create_agent_chat_model  # noqa: E402


DEFAULT_INPUT = (
    ROOT_DIR
    / "docs"
    / "business-scenarios"
    / "heat-treatment"
    / "heat-treatment-question-set-v1.yaml"
)
DEFAULT_OUTPUT = ROOT_DIR / "results" / "heat-treatment-question-evaluation.json"

EvaluationStatus = Literal[
    "supported",
    "missing_capability",
    "missing_fact",
    "need_clarification",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the current heat-treatment Capability Reasoning over a YAML question set."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def load_questions(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise ValueError("Question set must contain a questions list.")
    raw_questions = cast(list[object], payload["questions"])
    if not all(isinstance(item, dict) for item in raw_questions):
        raise ValueError("Every question must be an object.")
    questions = cast(list[dict[str, Any]], raw_questions)
    ids = [item.get("id") for item in questions]
    if any(not isinstance(item_id, str) for item_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Every question must be an object with a unique id.")
    return questions


def classify(
    question: dict[str, Any],
    selected_capability: str | None,
    confidence: float,
    validation_status: str,
    validation_reason: str | None,
    runtime_capabilities: set[str],
) -> dict[str, Any]:
    expected = question.get("expected_capability")
    expected_behavior = question.get("expected_behavior")

    if expected is not None and expected not in runtime_capabilities:
        status: EvaluationStatus = "missing_capability"
        result = "当前运行时 Catalog 不包含完成该业务目标所需的 Capability。"
        reason = f"期望能力 {expected} 不在当前运行时 Capability Catalog。"
    elif expected is not None and selected_capability != expected:
        status = "missing_fact"
        result = "当前 Reasoning 未选择已存在的目标 Capability。"
        reason = (
            f"期望选择 {expected}，实际选择 {selected_capability or 'none'}；"
            "现有 Business Facts/表达映射不足。"
        )
    elif validation_status == "capability_not_executable":
        status = "missing_capability"
        result = "Reasoning 正确，但当前 Capability 没有可用执行链。"
        reason = "API/Execution 缺口：" + (
            validation_reason or f"{selected_capability} 当前不可执行。"
        )
    elif expected is None and validation_status != "matched":
        status = "need_clarification"
        result = "问题目标不明确，当前链路安全进入澄清。"
        reason = validation_reason or "未稳定选择唯一 Capability。"
    elif expected_behavior == "clarify" and validation_status in {
        "missing_required_entities",
        "need_clarification",
    }:
        status = "need_clarification"
        result = "已识别业务方向，但缺少执行所需条件。"
        reason = validation_reason or "缺少必要业务实体。"
    elif expected_behavior == "execute" and validation_status == "matched":
        status = "supported"
        result = "当前 Reasoning 与 Validator 可进入预期 Capability 执行链。"
        reason = f"正确选择 {selected_capability}，置信度 {confidence:.2f}。"
    else:
        status = "missing_fact"
        result = "当前行为与问题预期不一致。"
        reason = (
            f"expected_behavior={expected_behavior}, "
            f"selected={selected_capability or 'none'}, validation={validation_status}."
        )

    return {
        "question": question["question"],
        "result": result,
        "selected_capability": selected_capability,
        "confidence": round(confidence, 4),
        "status": status,
        "reason": reason,
    }


def evaluate(questions: list[dict[str, Any]]) -> dict[str, Any]:
    registry = CapabilityLoader().load()
    reasoner = CapabilityReasoner(
        registry,
        LlmRuntime(create_agent_chat_model(get_settings())),
    )
    validator = CapabilityReasoningValidator(registry)
    runtime_capabilities = set(registry.names())
    results: list[dict[str, Any]] = []

    for question in questions:
        reasoning = reasoner.reason(
            str(question["question"]),
            HEAT_TREATMENT_BUSINESS_FACTS,
        )
        validation = validator.validate(reasoning)
        result = classify(
            question,
            reasoning.selected_capability_name,
            reasoning.confidence,
            validation.status,
            validation.clarification_reason,
            runtime_capabilities,
        )
        results.append({"id": question["id"], **result})

    status_counts = Counter(item["status"] for item in results)
    api_execution_count = sum(
        1 for item in results if item["reason"].startswith("API/Execution 缺口")
    )
    supported_count = status_counts["supported"]
    return {
        "metadata": {
            "question_set": str(DEFAULT_INPUT.relative_to(ROOT_DIR)),
            "business_facts": "HEAT_TREATMENT_BUSINESS_FACTS",
            "capability_catalog": "heat-treatment.yaml",
            "reasoning": "current CapabilityReasoning",
        },
        "summary": {
            "total": len(results),
            "supported": supported_count,
            "support_rate": round(supported_count / len(results), 4) if results else 0,
            "missing_capability": status_counts["missing_capability"],
            "missing_fact": status_counts["missing_fact"],
            "need_clarification": status_counts["need_clarification"],
            "missing_api_execution_detail": api_execution_count,
        },
        "results": results,
    }


def main() -> int:
    args = parse_args()
    questions = load_questions(args.input)
    evaluation = evaluate(questions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evaluation["summary"], ensure_ascii=False))
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
