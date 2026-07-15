import json
from pathlib import Path
import sys
import uuid
from typing import Any

from sqlalchemy import create_engine


BACKEND_DIR = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.capability.catalog.loader import CapabilityLoader  # noqa: E402
from ...deprecated.capability_reasoning_v1.audit import (  # noqa: E402
    CapabilityReasoningAuditRepository,
)
from ...deprecated.capability_reasoning_v1.reasoner import (  # noqa: E402
    CapabilityReasoner,
    default_heat_treatment_business_facts,
)
from ...deprecated.capability_reasoning_v1.validator import (  # noqa: E402
    CapabilityReasoningValidator,
)
from app.core.type_defs import JsonObject  # noqa: E402


RESULTS_DIR = BACKEND_DIR / "results"
JSON_REPORT_PATH = RESULTS_DIR / "capability_reasoning_experiment_report.json"
MD_REPORT_PATH = RESULTS_DIR / "capability_reasoning_experiment_report.md"
AUDIT_DB_PATH = RESULTS_DIR / "capability_reasoning_audit.sqlite"


CASES = [
    ("status_001", "TRACE-HTR-B-H-001什么状态", "heat_current_stage"),
    ("status_002", "TRACE-HTR-B-H-002热处理状态", "heat_current_stage"),
    ("status_003", "TRACE-HTR-B-H-003做到哪一步了", "heat_current_stage"),
    ("status_004", "TRACE-HTR-B-H-004做完了吗", "heat_current_stage"),
    ("status_005", "TRACE-HTR-B-H-005当前情况", "heat_current_stage"),
    ("status_006", "HT20260603-007热处理的状态", "heat_current_stage"),
    ("status_007", "HT20260603-008现在到哪了", "heat_current_stage"),
    ("status_008", "查TRACE-HTR-B-H-008进度", "heat_current_stage"),
    ("status_009", "TRACE-HTR-B-H-009完成了吗", "heat_current_stage"),
    ("status_010", "TRACE-HTR-B-H-010目前哪一步", "heat_current_stage"),
    ("device_001", "TRACE-HTR-B-H-001在哪个设备进行", "heat_device_trace"),
    ("device_002", "TRACE-HTR-B-H-002在哪个炉子完成", "heat_device_trace"),
    ("device_003", "TRACE-HTR-B-H-003哪台炉做的", "heat_device_trace"),
    ("device_004", "TRACE-HTR-B-H-004生产设备是什么", "heat_device_trace"),
    ("device_005", "TRACE-HTR-B-H-005用的哪个炉", "heat_device_trace"),
    ("device_006", "这个热处理在哪个设备 TRACE-HTR-B-H-006", "heat_device_trace"),
    ("device_007", "TRACE-HTR-B-H-007设备追溯", "heat_device_trace"),
    ("device_008", "TRACE-HTR-B-H-008在哪完成", "heat_device_trace"),
    ("analysis_001", "本月热处理完成多少批", "heat_completion_count_monthly"),
    ("analysis_002", "统计本月热处理完成数量", "heat_completion_count_monthly"),
    ("analysis_003", "这个月热处理完成多少批次", "heat_completion_count_monthly"),
    ("analysis_004", "热处理本月完成数量是多少", "heat_completion_count_monthly"),
    ("analysis_005", "帮我统计热处理完成多少批", "heat_completion_count_monthly"),
    ("ambiguous_001", "这个热处理怎么样", None),
    ("ambiguous_002", "这个产品怎么样", None),
    ("missing_001", "查热处理状态", "heat_current_stage"),
    ("missing_002", "查一下热处理", None),
    ("missing_003", "这个热处理在哪个炉子完成", "heat_device_trace"),
    ("unrelated_001", "今天天气怎么样", None),
    ("unrelated_002", "帮我写一首诗", None),
]


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    registry = CapabilityLoader().load()
    reasoner = CapabilityReasoner(registry)
    validator = CapabilityReasoningValidator(registry)
    audit = CapabilityReasoningAuditRepository(
        create_engine(f"sqlite:///{AUDIT_DB_PATH}", future=True)
    )
    case_results = []
    for case_id, user_input, expected in CASES:
        case_result = _run_case(reasoner, validator, audit, case_id, user_input, expected)
        case_results.append(case_result)
    report = _build_report(case_results)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    MD_REPORT_PATH.write_text(_markdown_report(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def _run_case(
    reasoner: CapabilityReasoner,
    validator: CapabilityReasoningValidator,
    audit: CapabilityReasoningAuditRepository,
    case_id: str,
    user_input: str,
    expected: str | None,
) -> JsonObject:
    catalog_only = reasoner.reason_catalog_only(user_input)
    with_facts = reasoner.reason_with_business_facts(
        user_input,
        default_heat_treatment_business_facts(),
    )
    final_result = reasoner.reason(user_input)
    validation = validator.validate(final_result)
    execution_result: JsonObject = {
        "would_execute": validation.status == "matched",
        "validation_status": validation.status,
        "execution_type": validation.execution_type,
    }
    request_id = uuid.uuid4().hex
    audit.record(
        request_id=request_id,
        user_input=user_input,
        reasoning_result=final_result,
        validation_result=validation,
        execution_result=execution_result,
    )
    return {
        "id": case_id,
        "request_id": request_id,
        "user_input": user_input,
        "expected_capability": expected,
        "catalog_only": _case_view(catalog_only),
        "catalog_with_business_facts": _case_view(with_facts),
        "final": _case_view(final_result),
        "validation": validation.model_dump(mode="json"),
        "top1_pass": _top1_pass(final_result.selected_capability, expected),
        "top3_pass": _top3_pass(final_result, expected),
        "catalog_only_top1_pass": _top1_pass(catalog_only.selected_capability, expected),
        "business_facts_top1_pass": _top1_pass(with_facts.selected_capability, expected),
    }


def _case_view(result) -> JsonObject:
    return {
        "context_level": result.context_level,
        "selected_capability": result.selected_capability,
        "confidence": result.confidence,
        "need_clarification": result.need_clarification,
        "entities": result.entities,
        "candidates": [
            item.model_dump(mode="json") for item in result.candidate_capabilities
        ],
    }


def _build_report(case_results: list[JsonObject]) -> JsonObject:
    total = len(case_results)
    expected_selectable = [
        item for item in case_results if item["expected_capability"] is not None
    ]
    top1 = sum(1 for item in case_results if item["top1_pass"])
    top3 = sum(1 for item in expected_selectable if item["top3_pass"])
    catalog_only_top1 = sum(1 for item in case_results if item["catalog_only_top1_pass"])
    business_facts_top1 = sum(
        1 for item in case_results if item["business_facts_top1_pass"]
    )
    failures = [item for item in case_results if not item["top1_pass"]]
    return {
        "summary": {
            "total": total,
            "top1_capability_accuracy": top1 / total if total else 0,
            "top3_candidate_coverage": (
                top3 / len(expected_selectable) if expected_selectable else 0
            ),
            "catalog_only_top1_accuracy": catalog_only_top1 / total if total else 0,
            "business_facts_top1_accuracy": business_facts_top1 / total if total else 0,
            "business_facts_lift": (
                business_facts_top1 - catalog_only_top1
            ) / total
            if total
            else 0,
            "failed": len(failures),
            "system_status": "PASS" if not failures else "REVIEW",
            "audit_db_path": str(AUDIT_DB_PATH),
        },
        "cases": case_results,
        "failures": failures,
    }


def _markdown_report(report: JsonObject) -> str:
    summary = report["summary"]
    lines = [
        "# Capability Reasoning Experiment V1",
        "",
        "## Summary",
        "",
        f"- Total: {summary['total']}",
        f"- Top1 capability accuracy: {summary['top1_capability_accuracy']:.2f}",
        f"- Top3 candidate coverage: {summary['top3_candidate_coverage']:.2f}",
        f"- Catalog-only top1 accuracy: {summary['catalog_only_top1_accuracy']:.2f}",
        f"- Business-facts top1 accuracy: {summary['business_facts_top1_accuracy']:.2f}",
        f"- Business-facts lift: {summary['business_facts_lift']:.2f}",
        f"- Failed: {summary['failed']}",
        f"- System status: {summary['system_status']}",
        f"- Audit DB: {summary['audit_db_path']}",
        "",
        "## Cases",
        "",
    ]
    for item in report["cases"]:
        final = item["final"]
        validation = item["validation"]
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Input: {item['user_input']}",
                f"- Expected: {item['expected_capability']}",
                f"- Selected: {final['selected_capability']}",
                f"- Context: {final['context_level']}",
                f"- Confidence: {final['confidence']}",
                f"- Validation: {validation['status']}",
                f"- Top1 pass: {item['top1_pass']}",
                "",
            ]
        )
    return "\n".join(lines)


def _top1_pass(selected: str | None, expected: str | None) -> bool:
    return selected == expected


def _top3_pass(result, expected: str | None) -> bool:
    if expected is None:
        return result.selected_capability is None
    return expected in [item.name for item in result.candidate_capabilities[:3]]


if __name__ == "__main__":
    main()
