#!/usr/bin/env python3
"""Run a real-LLM benchmark for Capability Reasoning V2 without executing capabilities."""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.agents.heat_treatment.business_facts import (  # noqa: E402
    HEAT_TREATMENT_BUSINESS_FACTS,
)
from app.agent.capability.catalog.loader import CapabilityLoader  # noqa: E402
from app.agent.reasoning import CapabilityReasoner  # noqa: E402
from app.agent.reasoning.capability_reasoning.audit import (  # noqa: E402
    CapabilityReasoningAuditRecord,
)
from app.agent.runtime.llm import LlmRuntime  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.infrastructure.agent.langchain_factory import create_agent_chat_model  # noqa: E402


QUESTION_SET = (
    ROOT_DIR
    / "docs"
    / "business-scenarios"
    / "heat-treatment"
    / "heat-treatment-question-set-v1.yaml"
)
OUTPUT_PATH = ROOT_DIR / "results" / "capability-reasoning-v2-benchmark.json"
BENCHMARK_IDS = [
    "HT-Q-001", "HT-Q-002", "HT-Q-003", "HT-Q-004", "HT-Q-005", "HT-Q-006",
    "HT-Q-007", "HT-Q-008", "HT-Q-009", "HT-Q-010", "HT-Q-011", "HT-Q-012",
    "HT-Q-013", "HT-Q-014", "HT-Q-017", "HT-Q-019", "HT-Q-025", "HT-Q-026",
    "HT-Q-027", "HT-Q-033", "HT-Q-034", "HT-Q-035", "HT-Q-038", "HT-Q-039",
    "HT-Q-041", "HT-Q-042", "HT-Q-043", "HT-Q-044", "HT-Q-046", "HT-Q-047",
]


class CollectingAuditSink:
    def __init__(self):
        self.records: list[CapabilityReasoningAuditRecord] = []

    def record(self, audit: CapabilityReasoningAuditRecord) -> None:
        self.records.append(audit)


def load_cases() -> list[dict[str, Any]]:
    payload = yaml.safe_load(QUESTION_SET.read_text(encoding="utf-8"))
    all_cases = {item["id"]: item for item in payload["questions"]}
    return [all_cases[item_id] for item_id in BENCHMARK_IDS]


def main() -> int:
    settings = get_settings()
    registry = CapabilityLoader().load()
    runtime_names = set(registry.names())
    audit = CollectingAuditSink()
    reasoner = CapabilityReasoner(
        registry,
        LlmRuntime(create_agent_chat_model(settings)),
        audit,
    )
    results: list[dict[str, Any]] = []

    for case in load_cases():
        expected_name = case.get("expected_capability")
        expected_selection = expected_name if expected_name in runtime_names else None
        started = time.perf_counter()
        try:
            reasoning = reasoner.reason(case["question"], HEAT_TREATMENT_BUSINESS_FACTS)
            actual = reasoning.selected_capability_name
            selection_ok = actual == expected_selection
            clarification_ok = (
                not reasoning.need_clarification
                if expected_selection is not None
                else reasoning.need_clarification and actual is None
            )
            passed = selection_ok and clarification_ok
            error = None
            output = reasoning.model_dump(mode="json")
        except Exception as exc:
            actual = None
            selection_ok = False
            clarification_ok = False
            passed = False
            error = f"{type(exc).__name__}: {exc}"
            output = None
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected_capability": expected_selection,
                "actual_capability": actual,
                "selection_ok": selection_ok,
                "clarification_ok": clarification_ok,
                "passed": passed,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "reasoning_output": output,
                "error": error,
            }
        )
        print(
            f"{case['id']} expected={expected_selection} actual={actual} "
            f"passed={passed}"
        )

    passed_count = sum(1 for item in results if item["passed"])
    selection_count = sum(1 for item in results if item["selection_ok"])
    clarification_count = sum(1 for item in results if item["clarification_ok"])
    errors = sum(1 for item in results if item["error"] is not None)
    category_stats = {
        category: {
            "total": len(items),
            "passed": sum(1 for item in items if item["passed"]),
        }
        for category in sorted({item["category"] for item in results})
        for items in [[item for item in results if item["category"] == category]]
    }
    payload = {
        "metadata": {
            "benchmark_version": "capability-reasoning-v2-benchmark-v1",
            "prompt_version": "capability-reasoning-v2",
            "model": settings.llm_model,
            "base_url": settings.llm_base_url,
            "question_set": str(QUESTION_SET.relative_to(ROOT_DIR)),
            "case_ids": BENCHMARK_IDS,
        },
        "summary": {
            "total": len(results),
            "passed": passed_count,
            "pass_rate": round(passed_count / len(results), 4),
            "selection_accuracy": round(selection_count / len(results), 4),
            "clarification_accuracy": round(clarification_count / len(results), 4),
            "errors": errors,
            "actual_capability_distribution": dict(
                Counter(item["actual_capability"] or "none" for item in results)
            ),
            "category_stats": category_stats,
        },
        "results": results,
        "reasoning_audit": [item.model_dump(mode="json") for item in audit.records],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    print(f"output={OUTPUT_PATH}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
