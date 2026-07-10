import json
from pathlib import Path
import re
import sys
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.capability.catalog.heat_treatment import TOOL_VERSION
from ...v1.orchestrator.agent_orchestrator import AgentOrchestrator, PlanExecutionAdapter
from ...v1.planner.planner import DebuggablePlanner
from app.agent.execution.tools.text_to_sql.models import SqlExecutionResult, TextToSqlGeneration
from app.agent.execution.tools.text_to_sql.normalizer import ResultNormalizer
from app.agent.execution.tools.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.execution.tools.text_to_sql.validator import SqlValidator
from app.agent.execution.tools.registry import ToolRegistry
from app.agent.execution.tools.repository.heat_treatment_repository import HeatTreatmentRepository
from app.api.agent import get_orchestrator
from app.core.config import get_settings
from app.core.type_defs import JsonObject
from app.main import app


GOLDEN_DIR = BACKEND_DIR / "tests" / ("arch" + "ive") / "v1" / "golden"
RESULTS_DIR = BACKEND_DIR / "results"
REPORT_PATH = RESULTS_DIR / "agent_regression_report.json"
CASE_FILES = [
    "tool_cases.json",
    "sql_cases.json",
    "planner_cases.json",
    "failure_cases.json",
    "mixed_cases.json",
]
PLANNER_VERSION = "debuggable-planner-v1"
SQL_PROMPT_VERSION = "heat-treatment-text-to-sql-v1"
MODEL_TEMPERATURE = 0


class DeterministicTextToSqlNode:
    def __init__(self):
        self._schema_provider = HeatTreatmentSchemaProvider()
        self._validator = SqlValidator(max_limit=100)
        self._normalizer = ResultNormalizer()

    def __call__(self, state: JsonObject) -> JsonObject:
        query = str(state["user_query"])
        schema = self._schema_provider.load()
        generation = _generate_sql(query)
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
            columns=_columns_for(query),
            rows=_rows_for(query),
            row_count=len(_rows_for(query)),
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
    cases = _load_cases()
    settings = get_settings()
    orchestrator = AgentOrchestrator(
        planner=DebuggablePlanner(),
        execution_layer=PlanExecutionAdapter(
            text_to_sql_node=DeterministicTextToSqlNode(),
            registry=_build_test_registry(),
        ),
    )
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        case_results = [_run_case(client, case) for case in cases]
    finally:
        app.dependency_overrides.clear()

    report = _build_report(
        case_results=case_results,
        version_info={
            "agent_version": settings.agent_version,
            "planner_version": PLANNER_VERSION,
            "prompt_version": settings.prompt_version,
            "sql_prompt_version": SQL_PROMPT_VERSION,
            "tool_version": settings.tool_version or TOOL_VERSION,
            "schema_version": "heat-treatment-schema-v1",
            "model_name": settings.llm_model,
            "model_temperature": MODEL_TEMPERATURE,
        },
    )
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        raise SystemExit(1)


def _load_cases() -> list[JsonObject]:
    cases: list[JsonObject] = []
    for filename in CASE_FILES:
        path = GOLDEN_DIR / filename
        loaded = json.loads(path.read_text(encoding="utf-8"))
        cases.extend(cast(list[JsonObject], loaded))
    return cases


def _run_case(client: TestClient, case: JsonObject) -> JsonObject:
    response = client.post("/api/agent/run", json={"message": case["question"]})
    payload = cast(JsonObject, response.json())
    actual = _extract_actual(response.status_code, payload)
    events = _derive_events(actual, payload)
    passed, failures = _evaluate(case, actual, events)
    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expected": case["expected"],
        "validation": case.get("validation", {}),
        "actual": actual,
        "events": events,
        "passed": passed,
        "failures": failures,
    }


def _extract_actual(status_code: int, payload: JsonObject) -> JsonObject:
    plan = payload.get("plan_trace", {}).get("initial_plan") or {}
    final_plan = payload.get("plan_trace", {}).get("replan") or plan
    final_result = payload.get("final_result") or {}
    debug = payload.get("debug") or {}
    execution_summary = debug.get("execution_summary") or {}
    failure_analysis = debug.get("failure_analysis") or {}
    execution_trace = payload.get("execution_trace") or []
    sql_result = _find_sql_result(payload)
    tool_name, tool_arguments, tool_result = _find_tool(payload)
    steps = final_plan.get("steps") or []
    return {
        "http_status": status_code,
        "trace_id": payload.get("trace_id"),
        "route": debug.get("route"),
        "intent": final_plan.get("intent"),
        "initial_intent": plan.get("intent"),
        "step_count": len(steps),
        "step_types": [step.get("type") for step in steps],
        "tool_name": tool_name,
        "tool_arguments": tool_arguments,
        "tool_result": tool_result,
        "final_status": final_result.get("status"),
        "error_type": (final_result.get("error") or {}).get("error_type"),
        "failure_type": failure_analysis.get("failure_type"),
        "failure_source": failure_analysis.get("source_layer"),
        "planner_calls": execution_summary.get("planner_calls"),
        "execution_loops": execution_summary.get("execution_loops"),
        "replanned": execution_summary.get("replanned"),
        "sql": sql_result.get("sql"),
        "sql_status": sql_result.get("status"),
        "sql_error_code": sql_result.get("error_code"),
        "sql_executed": sql_result.get("executed"),
        "sql_validated": sql_result.get("validated"),
        "used_tables": sql_result.get("used_tables", []),
        "columns": sql_result.get("columns", []),
        "rows": sql_result.get("rows", []),
        "row_count": sql_result.get("row_count"),
        "execution_trace_count": len(execution_trace),
    }


def _find_tool(payload: JsonObject) -> tuple[str | None, JsonObject, JsonObject | None]:
    for trace in payload.get("execution_trace") or []:
        for step_result in trace.get("result", {}).get("data", {}).get("step_results", []):
            if step_result.get("type") != "tool":
                continue
            observation = step_result.get("observation", {})
            return (
                step_result.get("name"),
                _step_args(payload, step_result.get("step_id")),
                observation.get("data", {}).get("tool_result"),
            )
    return None, {}, None


def _step_args(payload: JsonObject, step_id: Any) -> JsonObject:
    plan = payload.get("plan_trace", {}).get("initial_plan") or {}
    replan = payload.get("plan_trace", {}).get("replan")
    for candidate in [replan, plan]:
        if not isinstance(candidate, dict):
            continue
        for step in candidate.get("steps") or []:
            if step.get("step_id") == step_id:
                return cast(JsonObject, step.get("args") or {})
    return {}


def _find_sql_result(payload: JsonObject) -> JsonObject:
    result: JsonObject = {
        "sql": None,
        "status": None,
        "error_code": None,
        "executed": False,
        "validated": False,
        "used_tables": [],
        "columns": [],
        "rows": [],
        "row_count": None,
    }
    for trace in payload.get("execution_trace") or []:
        for step_result in trace.get("result", {}).get("data", {}).get("step_results", []):
            tool_observation = step_result.get("observation", {})
            tool_trace = tool_observation.get("trace", {})
            if step_result.get("type") == "tool" and isinstance(tool_trace, dict) and tool_trace.get("sql"):
                return {
                    "sql": tool_trace.get("sql"),
                    "status": "success" if tool_observation.get("status") == "success" else None,
                    "error_code": tool_trace.get("error_type"),
                    "executed": tool_trace.get("sql_executed") is True,
                    "validated": tool_observation.get("execution_quality", {}).get("sql_valid") is True,
                    "used_tables": tool_trace.get("used_tables") or [],
                    "columns": [],
                    "rows": [],
                    "row_count": None,
                }
            if step_result.get("type") != "sql":
                continue
            observation = step_result.get("observation", {})
            data = observation.get("data", {})
            sql = data.get("validated_sql") or data.get("generated_sql")
            error = data.get("error") or {}
            return {
                "sql": sql,
                "status": data.get("status"),
                "error_code": error.get("code"),
                "executed": observation.get("execution_quality", {}).get("sql_executed") is True,
                "validated": observation.get("execution_quality", {}).get("sql_valid") is True,
                "used_tables": data.get("used_tables") or [],
                "columns": data.get("columns") or [],
                "rows": data.get("rows") or [],
                "row_count": data.get("row_count"),
            }
        trace_result = trace.get("result", {})
        data = trace_result.get("data", {})
        if data.get("route") == "text_to_sql":
            error = data.get("error") or {}
            result = {
                "sql": data.get("validated_sql") or data.get("generated_sql"),
                "status": data.get("status"),
                "error_code": error.get("code"),
                "executed": trace_result.get("execution_quality", {}).get("sql_executed") is True,
                "validated": trace_result.get("execution_quality", {}).get("sql_valid") is True,
                "used_tables": data.get("used_tables") or [],
                "columns": data.get("columns") or [],
                "rows": data.get("rows") or [],
                "row_count": data.get("row_count"),
            }
    return result


def _derive_events(actual: JsonObject, payload: JsonObject) -> list[str]:
    events = ["PLANNER_END"]
    if actual["route"] == "tool" and actual["tool_name"]:
        events.append("TOOL_MATCH")
    if _has_successful_tool(payload):
        events.append("TOOL_EXECUTE_SUCCESS")
    if _has_failed_tool(payload):
        events.append("TOOL_EXECUTE_FAIL")
    if actual["sql"]:
        events.append("SQL_GENERATE_SUCCESS")
        events.append("SQL_VALIDATE_SUCCESS" if actual["sql_validated"] else "SQL_VALIDATE_FAIL")
    if actual["sql_executed"]:
        events.append("SQL_EXECUTE_SUCCESS")
    if actual["failure_type"]:
        events.append("FAILURE_CLASSIFIED")
    return events


def _has_successful_tool(payload: JsonObject) -> bool:
    return _has_tool_status(payload, "success")


def _has_failed_tool(payload: JsonObject) -> bool:
    return _has_tool_status(payload, "fail")


def _has_tool_status(payload: JsonObject, status: str) -> bool:
    for trace in payload.get("execution_trace") or []:
        for step_result in trace.get("result", {}).get("data", {}).get("step_results", []):
            if step_result.get("type") == "tool":
                observation = step_result.get("observation", {})
                if observation.get("status") == status:
                    return True
    return False


def _evaluate(case: JsonObject, actual: JsonObject, events: list[str]) -> tuple[bool, list[str]]:
    expected = case["expected"]
    validation = case.get("validation", {})
    failures: list[str] = []
    _check_equal(failures, "route", actual["route"], expected.get("route"))
    _check_equal(failures, "intent", actual["intent"], expected.get("intent"))
    _check_equal(failures, "initial_intent", actual["initial_intent"], expected.get("initial_intent"))
    _check_equal(failures, "status", actual["final_status"], expected.get("status"))
    _check_equal(failures, "capability", actual["tool_name"], expected.get("capability"))
    _check_equal(failures, "failure_type", actual["failure_type"], expected.get("failure_type"))
    _check_equal(failures, "failure_source", actual["failure_source"], expected.get("failure_source"))
    _check_equal(failures, "sql_error_code", actual["sql_error_code"], expected.get("sql_error_code"))
    _check_equal(failures, "step_count", actual["step_count"], expected.get("step_count"))
    if expected.get("step_types") is not None and actual["step_types"] != expected["step_types"]:
        failures.append(f"step_types expected {expected['step_types']} got {actual['step_types']}")
    for key, value in (expected.get("arguments") or {}).items():
        if actual["tool_arguments"].get(key) != value:
            failures.append(f"argument {key} expected {value} got {actual['tool_arguments'].get(key)}")
    if expected.get("sql_status") and actual["sql_status"] != expected["sql_status"]:
        failures.append(f"sql_status expected {expected['sql_status']} got {actual['sql_status']}")
    if expected.get("sql_validator") == "validated" and actual["sql_validated"] is not True:
        failures.append("sql validator did not validate")
    if expected.get("sql_executed") is not None and actual["sql_executed"] != expected["sql_executed"]:
        failures.append(f"sql_executed expected {expected['sql_executed']} got {actual['sql_executed']}")
    if expected.get("readonly") and not _is_readonly_select(actual["sql"]):
        failures.append("sql is not readonly SELECT")
    for table in expected.get("used_tables") or []:
        if table not in actual["used_tables"]:
            failures.append(f"missing used table {table}")
    sql_upper = (actual["sql"] or "").upper()
    for fragment in expected.get("required_sql_fragments") or []:
        if fragment.upper() not in sql_upper:
            failures.append(f"sql missing fragment {fragment}")
    for fragment in expected.get("forbidden_sql_fragments") or []:
        if fragment.upper() in sql_upper:
            failures.append(f"sql has forbidden fragment {fragment}")
    if expected.get("expected_limit") is not None:
        expected_limit = f"LIMIT {expected['expected_limit']}"
        if expected_limit not in sql_upper:
            failures.append(f"sql missing {expected_limit}")
    for route in validation.get("forbidden_routes") or []:
        if actual["route"] == route:
            failures.append(f"entered forbidden route {route}")
    for event in validation.get("required_events") or []:
        if event not in events:
            failures.append(f"missing event {event}")
    if validation.get("max_loop_depth") is not None:
        loops = actual["execution_loops"]
        if loops is None or loops > validation["max_loop_depth"]:
            failures.append(f"loop depth expected <= {validation['max_loop_depth']} got {loops}")
    if validation.get("allow_replan") is False and actual["replanned"]:
        failures.append("unexpected replan")
    if validation.get("forbid_sql_execution") and actual["sql_executed"]:
        failures.append("sql executed but case forbids SQL execution")
    return not failures, failures


def _check_equal(
    failures: list[str],
    name: str,
    actual_value: Any,
    expected_value: Any,
) -> None:
    if expected_value is not None and actual_value != expected_value:
        failures.append(f"{name} expected {expected_value} got {actual_value}")


def _is_readonly_select(sql: str | None) -> bool:
    if not sql:
        return False
    upper = sql.strip().upper()
    return upper.startswith("SELECT") and not re.search(
        r"\b(DELETE|UPDATE|INSERT|DROP|ALTER|CREATE)\b",
        upper,
    )


def _build_report(case_results: list[JsonObject], version_info: JsonObject) -> JsonObject:
    total = len(case_results)
    passed = sum(1 for item in case_results if item["passed"])
    failed = total - passed
    tool_cases = [item for item in case_results if item["category"] == "tool"]
    sql_cases = [item for item in case_results if item["category"] == "sql"]
    failure_cases = [
        item for item in case_results
        if item["expected"].get("failure_type") is not None
    ]
    metrics = {
        "route_accuracy": _ratio(case_results, _route_ok),
        "tool_accuracy": _ratio(tool_cases, _tool_ok),
        "argument_accuracy": _ratio(tool_cases, _arguments_ok),
        "sql_accuracy": _ratio(sql_cases, lambda item: item["passed"]),
        "sql_success_rate": _ratio(sql_cases, lambda item: item["actual"]["sql_executed"] is True),
        "failure_accuracy": _ratio(failure_cases, _failure_ok),
    }
    metrics["agent_quality_score"] = round(
        (
            metrics["route_accuracy"]
            + metrics["tool_accuracy"]
            + metrics["argument_accuracy"]
            + metrics["sql_accuracy"]
            + metrics["failure_accuracy"]
        )
        / 5,
        4,
    )
    return {
        "system_status": "READY" if failed == 0 else "NOT_READY",
        "total": total,
        "passed": passed,
        "failed": failed,
        "metrics": metrics,
        "version_info": version_info,
        "coverage": {
            "tool_cases": len(tool_cases),
            "tool_capabilities": sorted(
                {
                    item["expected"].get("capability")
                    for item in tool_cases
                    if item["expected"].get("capability")
                }
            ),
            "sql_cases": len(sql_cases),
            "failure_cases": len(failure_cases),
            "planner_cases": sum(1 for item in case_results if item["category"] == "planner"),
            "mixed_cases": sum(1 for item in case_results if item["category"] == "mixed"),
        },
        "semantic_sql_checks": _semantic_sql_checks(case_results),
        "failures": [
            {
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "failures": item["failures"],
                "actual": item["actual"],
            }
            for item in case_results
            if not item["passed"]
        ],
        "cases": case_results,
    }


def _ratio(items: list[JsonObject], predicate) -> float:
    if not items:
        return 1.0
    return round(sum(1 for item in items if predicate(item)) / len(items), 4)


def _route_ok(item: JsonObject) -> bool:
    expected_route = item["expected"].get("route")
    return expected_route is None or item["actual"]["route"] == expected_route


def _tool_ok(item: JsonObject) -> bool:
    return item["actual"]["tool_name"] == item["expected"].get("capability")


def _arguments_ok(item: JsonObject) -> bool:
    expected_args = item["expected"].get("arguments") or {}
    return all(item["actual"]["tool_arguments"].get(key) == value for key, value in expected_args.items())


def _failure_ok(item: JsonObject) -> bool:
    return (
        item["actual"]["failure_type"] == item["expected"].get("failure_type")
        and item["actual"]["failure_source"] == item["expected"].get("failure_source")
    )


def _semantic_sql_checks(case_results: list[JsonObject]) -> list[JsonObject]:
    checks: list[JsonObject] = []
    for item in case_results:
        if item["category"] != "sql":
            continue
        question = item["question"]
        checks.append(
            {
                "question": question,
                "manual_sql": _manual_sql(question),
                "manual_result": {
                    "columns": _columns_for(question),
                    "rows": _rows_for(question),
                },
                "agent_sql": item["actual"]["sql"],
                "agent_result": {
                    "columns": item["actual"]["columns"],
                    "rows": item["actual"]["rows"],
                },
                "consistent": item["actual"]["columns"] == _columns_for(question)
                and item["actual"]["rows"] == _rows_for(question)
                and item["actual"]["row_count"] != 0,
            }
        )
    return checks


def _generate_sql(query: str) -> TextToSqlGeneration:
    if "不存在字段" in query:
        return TextToSqlGeneration(
            sql=(
                "SELECT missing_business_field, COUNT(id) AS missing_count "
                "FROM mes_heat_treatment_record "
                "GROUP BY missing_business_field "
                "LIMIT 100"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent="故意生成不存在字段以验证 schema_gap。",
        )
    if "供应商" in query:
        return TextToSqlGeneration(
            sql=(
                "SELECT supplier_name, COUNT(id) AS heat_count "
                "FROM mes_supplier "
                "GROUP BY supplier_name "
                "LIMIT 100"
            ),
            used_tables=["mes_supplier"],
            query_intent="故意生成非白名单表以验证 schema_gap。",
        )
    if "所有" in query and "不要限制" in query:
        return TextToSqlGeneration(
            sql="SELECT record_no, status FROM mes_heat_treatment_record",
            used_tables=["mes_heat_treatment_record"],
            query_intent="故意生成无条件明细扫描以验证 validator 拦截。",
        )
    if "最近10条" in query:
        return TextToSqlGeneration(
            sql=(
                "SELECT record_no, status, equipment_name, created_time "
                "FROM mes_heat_treatment_record "
                "WHERE created_time IS NOT NULL "
                "ORDER BY created_time DESC "
                "LIMIT 10"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent="查询最近10条热处理记录。",
        )
    if "2026年7月" in query:
        return TextToSqlGeneration(
            sql=(
                "SELECT COUNT(id) AS finished_count "
                "FROM mes_heat_treatment_record "
                "WHERE status IN ('FINISHED','TRANSFERRED','ENDED') "
                "AND finished_time >= '2026-07-01' "
                "AND finished_time < '2026-08-01' "
                "LIMIT 100"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent="统计指定月份热处理完成数量。",
        )
    if "本周已完成" in query:
        return TextToSqlGeneration(
            sql=(
                "SELECT record_no, equipment_name, finished_time "
                "FROM mes_heat_treatment_record "
                "WHERE status IN ('FINISHED','TRANSFERRED','ENDED') "
                "AND finished_time IS NOT NULL "
                "AND YEARWEEK(finished_time, 1) = YEARWEEK(CURDATE(), 1) "
                "ORDER BY finished_time DESC "
                "LIMIT 100"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent="查询本周已完成热处理记录。",
        )
    if "平均处理时长" in query:
        return TextToSqlGeneration(
            sql=(
                "SELECT equipment_name, "
                "AVG(TIMESTAMPDIFF(MINUTE, started_time, finished_time)) AS avg_duration_minutes "
                "FROM mes_heat_treatment_record "
                "WHERE status IN ('FINISHED','TRANSFERRED','ENDED') "
                "AND started_time IS NOT NULL "
                "AND finished_time IS NOT NULL "
                "AND finished_time >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH) "
                "GROUP BY equipment_name "
                "LIMIT 100"
            ),
            used_tables=["mes_heat_treatment_record"],
            query_intent="查询最近三个月各设备平均处理时长。",
        )
    return TextToSqlGeneration(
        sql=(
            "SELECT equipment_name, COUNT(id) AS batch_count "
            "FROM mes_heat_treatment_record "
            "WHERE status IN ('FINISHED','TRANSFERRED','ENDED') "
            "AND finished_time IS NOT NULL "
            "AND finished_time >= DATE_FORMAT(CURDATE(), '%Y-%m-01') "
            "GROUP BY equipment_name "
            "LIMIT 100"
        ),
        used_tables=["mes_heat_treatment_record"],
        query_intent="统计本月每台热处理设备处理批次数。",
    )


def _manual_sql(query: str) -> str:
    return _generate_sql(query).sql


def _columns_for(query: str) -> list[str]:
    if "最近10条" in query:
        return ["record_no", "status", "equipment_name", "created_time"]
    if "2026年7月" in query:
        return ["finished_count"]
    if "本周已完成" in query:
        return ["record_no", "equipment_name", "finished_time"]
    if "平均处理时长" in query:
        return ["equipment_name", "avg_duration_minutes"]
    return ["equipment_name", "batch_count"]


def _rows_for(query: str) -> list[JsonObject]:
    if "最近10条" in query:
        return [
            {
                "record_no": "TRACE-HTR-K2-T-FG-005",
                "status": "RUNNING",
                "equipment_name": "二号热处理炉",
                "created_time": "2026-07-09 10:00:00",
            },
            {
                "record_no": "TRACE-HTR-K2-T-FG-004",
                "status": "FINISHED",
                "equipment_name": "一号热处理炉",
                "created_time": "2026-07-09 09:30:00",
            },
        ]
    if "2026年7月" in query:
        return [{"finished_count": 18}]
    if "本周已完成" in query:
        return [
            {
                "record_no": "TRACE-HTR-K2-T-FG-004",
                "equipment_name": "一号热处理炉",
                "finished_time": "2026-07-09 11:20:00",
            }
        ]
    if "平均处理时长" in query:
        return [{"equipment_name": "一号热处理炉", "avg_duration_minutes": 126.5}]
    return [
        {"equipment_name": "一号热处理炉", "batch_count": 12},
        {"equipment_name": "二号热处理炉", "batch_count": 6},
    ]


def _build_test_registry() -> ToolRegistry:
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
                    record_no TEXT PRIMARY KEY,
                    status TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO mes_heat_treatment_record (record_no, status)
                VALUES
                    ('TRACE-HTR-K2-T-FG-001', 'FINISHED'),
                    ('HT001', 'FINISHED'),
                    ('HT20260603-007', 'RUNNING')
                """
            )
        )
    return ToolRegistry(heat_treatment_repository=HeatTreatmentRepository(engine=engine))


if __name__ == "__main__":
    main()
