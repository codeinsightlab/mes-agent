import json
from pathlib import Path
import sys
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(BACKEND_DIR))

from ...v1.orchestrator.agent_orchestrator import (  # noqa: E402
    AgentOrchestrator,
    AgentRunInput,
    PlanExecutionAdapter,
)
from ...v1.planner.planner import DebuggablePlanner  # noqa: E402
from app.agent.execution.tools.text_to_sql.models import SqlExecutionResult, TextToSqlGeneration  # noqa: E402
from app.agent.execution.tools.text_to_sql.normalizer import ResultNormalizer  # noqa: E402
from app.agent.execution.tools.text_to_sql.schema_provider import HeatTreatmentSchemaProvider  # noqa: E402
from app.agent.execution.tools.text_to_sql.validator import SqlValidator  # noqa: E402
from app.agent.execution.tools.registry import ToolRegistry  # noqa: E402
from app.agent.execution.tools.repository.heat_treatment_repository import (  # noqa: E402
    HeatTreatmentRepository,
)
from app.core.type_defs import JsonObject  # noqa: E402

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


RESULTS_DIR = BACKEND_DIR / "results"
JSON_REPORT_PATH = RESULTS_DIR / "agent_mvp_evaluation_report.json"
MD_REPORT_PATH = RESULTS_DIR / "agent_mvp_evaluation_report.md"


CASES = [
    {
        "id": "explicit_heat_status",
        "input": "HT20260603-007热处理状态",
        "expected_capability": "heat_current_stage",
        "expected_status": "success",
        "expected_execution_type": "tool",
    },
    {
        "id": "synonym_heat_step",
        "input": "HT20260603-007这个热处理做到哪一步了",
        "expected_capability": "heat_current_stage",
        "expected_status": "success",
        "expected_execution_type": "tool",
    },
    {
        "id": "synonym_current_status",
        "input": "HT20260603-007当前状态怎么样",
        "expected_capability": "heat_current_stage",
        "expected_status": "success",
        "expected_execution_type": "tool",
    },
    {
        "id": "missing_heat_target",
        "input": "查一下热处理",
        "expected_capability": None,
        "expected_status": "failed",
        "expected_clarification": True,
    },
    {
        "id": "ambiguous_product_question",
        "input": "这个产品怎么样",
        "expected_capability": None,
        "expected_status": "failed",
        "expected_clarification": True,
    },
    {
        "id": "heat_completion_count",
        "input": "本月热处理完成多少批",
        "expected_capability": "heat_completion_count_monthly",
        "expected_status": "success",
        "expected_execution_type": "readonly_sql",
    },
]


class DeterministicTextToSqlNode:
    def __init__(self):
        self._schema_provider = HeatTreatmentSchemaProvider()
        self._validator = SqlValidator(max_limit=100)
        self._normalizer = ResultNormalizer()

    def __call__(self, state: JsonObject) -> JsonObject:
        query = state["user_query"]
        schema = self._schema_provider.load()
        generation = TextToSqlGeneration(
            sql=(
                "SELECT COUNT(id) AS completed_count "
                "FROM mes_heat_treatment_record "
                "WHERE status IN ('FINISHED','TRANSFERRED','ENDED') "
                "AND finished_time IS NOT NULL "
                "AND finished_time >= DATE_FORMAT(CURDATE(), '%Y-%m-01') "
                "LIMIT 100"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent=str(query),
            assumptions=["本月按 finished_time 过滤。"],
        )
        validation = self._validator.validate(generation.sql, schema)
        if validation.status != "validated":
            normalized = self._normalizer.normalize_validation_error(
                generation,
                validation,
                schema_version=schema.schema_version,
            )
            return {**state, "tool_result": normalized.model_dump(mode="json")}

        execution = SqlExecutionResult(
            status="success",
            columns=["completed_count"],
            rows=[{"completed_count": 12}],
            row_count=1,
            duration_ms=1,
        )
        normalized = self._normalizer.normalize_success(
            generation,
            validation,
            execution,
            schema_version=schema.schema_version,
        )
        return {**state, "tool_result": normalized.model_dump(mode="json")}


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(
            text_to_sql_node=DeterministicTextToSqlNode(),
            registry=ToolRegistry(heat_treatment_repository=_build_repository()),
        ),
    )
    case_results = [_run_case(orchestrator, case) for case in CASES]
    report = _build_report(case_results)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    MD_REPORT_PATH.write_text(_markdown_report(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def _run_case(orchestrator: AgentOrchestrator, case: dict[str, Any]) -> JsonObject:
    result = orchestrator.run(AgentRunInput(message=case["input"]))
    payload = result.model_dump(mode="json")
    trace = _last_trace(payload)
    semantic = trace.get("semantic_router_result") or {}
    capability_name = trace.get("capability_name")
    final_status = ((payload.get("final_result") or {}).get("status") or "")
    passed = (
        final_status == case["expected_status"]
        and capability_name == case["expected_capability"]
        and (
            "expected_execution_type" not in case
            or trace.get("execution_type") == case["expected_execution_type"]
        )
        and (
            "expected_clarification" not in case
            or bool(semantic.get("need_clarification")) is case["expected_clarification"]
        )
    )
    return {
        "id": case["id"],
        "input": case["input"],
        "passed": passed,
        "expected": case,
        "actual": {
            "final_status": final_status,
            "semantic_router_result": semantic,
            "plan": (payload.get("plan_trace") or {}).get("initial_plan"),
            "capability_name": capability_name,
            "routing_source": trace.get("routing_source"),
            "legacy_used": trace.get("legacy_used"),
            "execution_type": trace.get("execution_type"),
            "success": trace.get("success"),
            "error_reason": trace.get("error_reason"),
        },
    }


def _last_trace(payload: JsonObject) -> JsonObject:
    execution_trace = payload.get("execution_trace")
    if not isinstance(execution_trace, list) or not execution_trace:
        return {}
    result = execution_trace[-1].get("result")
    if not isinstance(result, dict):
        return {}
    trace = result.get("trace")
    return trace if isinstance(trace, dict) else {}


def _build_report(case_results: list[JsonObject]) -> JsonObject:
    total = len(case_results)
    passed = sum(1 for item in case_results if item["passed"])
    capability_hits = sum(1 for item in case_results if item["actual"]["capability_name"])
    clarifications = sum(
        1
        for item in case_results
        if item["actual"]["semantic_router_result"].get("need_clarification")
    )
    legacy_used = sum(1 for item in case_results if item["actual"]["legacy_used"])
    failures = [item for item in case_results if not item["passed"]]
    return {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": len(failures),
            "success_rate": passed / total if total else 0,
            "capability_hit_rate": capability_hits / total if total else 0,
            "clarification_rate": clarifications / total if total else 0,
            "legacy_usage_rate": legacy_used / total if total else 0,
            "system_status": "PASS" if not failures else "REVIEW",
        },
        "cases": case_results,
        "failures": failures,
    }


def _markdown_report(report: JsonObject) -> str:
    summary = report["summary"]
    lines = [
        "# MES Agent MVP Evaluation",
        "",
        "## Summary",
        "",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Success rate: {summary['success_rate']:.2f}",
        f"- Capability hit rate: {summary['capability_hit_rate']:.2f}",
        f"- Clarification rate: {summary['clarification_rate']:.2f}",
        f"- Legacy usage rate: {summary['legacy_usage_rate']:.2f}",
        f"- System status: {summary['system_status']}",
        "",
        "## Cases",
        "",
    ]
    for item in report["cases"]:
        actual = item["actual"]
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Input: {item['input']}",
                f"- Passed: {item['passed']}",
                f"- Capability: {actual['capability_name']}",
                f"- Routing source: {actual['routing_source']}",
                f"- Execution type: {actual['execution_type']}",
                f"- Final status: {actual['final_status']}",
                f"- Error reason: {actual['error_reason']}",
                "",
            ]
        )
    return "\n".join(lines)


def _build_repository() -> HeatTreatmentRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE mes_heat_treatment_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_no TEXT UNIQUE,
                    status TEXT,
                    finished_time TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO mes_heat_treatment_record (record_no, status, finished_time)
                VALUES
                    ('TRACE-HTR-K2-T-FG-001', 'FINISHED', '2026-07-01'),
                    ('HT20260603-007', 'RUNNING', NULL),
                    ('HT001', 'FINISHED', '2026-07-02')
                """
            )
        )
    return HeatTreatmentRepository(engine=engine)


if __name__ == "__main__":
    main()
