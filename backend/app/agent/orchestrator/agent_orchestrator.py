import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.agent.execution_loop import (
    ExecutionFeedbackLoop,
    ExecutionLoopResult,
    classify_failure,
)
from app.agent.execution_observation import (
    ExecutionObservation,
    ExecutionQuality,
    ExecutionTrace,
    FailureClassificationReport,
    ObservationFacts,
)
from app.agent.planner.models import PlannerPlan, PlannerRequest, PlanStep
from app.agent.planner.planner import DebuggablePlanner
from app.agent.text_to_sql.models import NormalizedTextToSqlResult
from app.agent.nodes.text_to_sql import TextToSqlNode
from app.agent.tools.registry import DEFAULT_TOOL_REGISTRY, ToolRegistry


class AgentRunContext(BaseModel):
    conversation_key: str | None = None
    visitor_id: str | None = None


class AgentRunInput(BaseModel):
    message: str
    context: AgentRunContext | None = None


class NormalizedError(BaseModel):
    error_type: str
    message: str
    recoverable: bool


class AgentFinalResult(BaseModel):
    status: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: NormalizedError | None = None


class AgentRunResult(BaseModel):
    trace_id: str
    plan_trace: dict[str, Any]
    execution_trace: list[dict[str, Any]]
    final_result: AgentFinalResult
    debug: dict[str, Any]


class AgentOrchestrator:
    def __init__(
        self,
        planner: DebuggablePlanner,
        execution_layer,
    ):
        self._planner = planner
        self._execution_layer = execution_layer

    def run(self, request: AgentRunInput) -> AgentRunResult:
        trace_id = uuid.uuid4().hex
        planner_request = PlannerRequest(user_query=request.message)
        try:
            loop_result = ExecutionFeedbackLoop(
                planner=self._planner,
                execution_layer=self._execution_layer,
            ).run(planner_request)
        except Exception as exc:
            return _error_result(
                trace_id=trace_id,
                error_type="execution_error",
                message="Agent orchestration failed.",
                recoverable=False,
                detail=str(exc),
            )

        return _normalize_loop_result(trace_id, loop_result)


class PlanExecutionAdapter:
    def __init__(
        self,
        text_to_sql_node: TextToSqlNode,
        registry: ToolRegistry = DEFAULT_TOOL_REGISTRY,
    ):
        self._text_to_sql_node = text_to_sql_node
        self._registry = registry

    def execute(self, plan: PlannerPlan) -> ExecutionObservation:
        if not plan.steps:
            return ExecutionObservation(
                status="fail",
                observation=ObservationFacts(
                    missing_facts=["plan.steps"],
                    failure_type="missing_param",
                ),
                execution_quality=ExecutionQuality(),
            )

        step_results: list[dict[str, Any]] = []
        for step in plan.steps:
            observation = self._execute_step(plan, step)
            step_results.append(
                {
                    "step_id": step.step_id,
                    "type": step.type,
                    "name": step.name,
                    "observation": observation.model_dump(),
                }
            )
            if observation.status != "success":
                return observation.model_copy(
                    update={
                        "data": {
                            **observation.data,
                            "step_results": step_results,
                        }
                    }
                )

        return ExecutionObservation(
            status="success",
            data={
                "step_results": step_results,
                "last_result": step_results[-1]["observation"]["data"] if step_results else {},
            },
            observation=ObservationFacts(
                facts_found=[f"step_{item['step_id']}" for item in step_results],
                decision_signals=["all_planned_steps_succeeded"],
            ),
            execution_quality=ExecutionQuality(
                tool_hit=any(item["type"] == "tool" for item in step_results) or None,
                sql_valid=True if any(item["type"] == "sql" for item in step_results) else None,
                sql_executed=True if any(item["type"] == "sql" for item in step_results) else None,
            ),
            trace=ExecutionTrace(
                used_tables=_collect_used_tables(step_results),
            ),
        )

    def _execute_step(self, plan: PlannerPlan, step: PlanStep) -> ExecutionObservation:
        if step.skip_reason:
            return ExecutionObservation(
                status="success",
                data={"skipped": True, "skip_reason": step.skip_reason},
                observation=ObservationFacts(
                    facts_found=[step.query_goal],
                    decision_signals=["reused_execution_history"],
                ),
                execution_quality=ExecutionQuality(),
                trace=ExecutionTrace(tool_name=step.name),
            )
        if step.type == "tool":
            return self._execute_tool_step(step)
        return self._execute_sql_step(plan, step)

    def _execute_tool_step(self, step: PlanStep) -> ExecutionObservation:
        if not step.name:
            return ExecutionObservation(
                status="fail",
                observation=ObservationFacts(
                    missing_facts=["tool_name"],
                    failure_type="missing_param",
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
            )
        try:
            data = self._registry.execute(step.name, step.args)
            return ExecutionObservation(
                status="success",
                data={"tool_result": data},
                observation=ObservationFacts(
                    facts_found=[step.name],
                    decision_signals=["tool_executed"],
                ),
                execution_quality=ExecutionQuality(tool_hit=True),
                trace=ExecutionTrace(tool_name=step.name),
            )
        except Exception as exc:
            failure_type = "tool_miss"
            missing_facts = [step.name]
            if "required" in str(exc).lower() or "missing" in str(exc).lower():
                failure_type = "missing_param"
                missing_facts = [f"{step.name}.args"]
            return ExecutionObservation(
                status="fail",
                data={"error": str(exc)},
                observation=ObservationFacts(
                    missing_facts=missing_facts,
                    decision_signals=["tool_failed"],
                    failure_type=failure_type,
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
                trace=ExecutionTrace(tool_name=step.name),
            )

    def _execute_sql_step(self, plan: PlannerPlan, step: PlanStep) -> ExecutionObservation:
        state = {
            "user_query": step.args.get("question") or plan.goal,
            "conversation_key": None,
            "agent_version": "orchestrator-v1",
            "prompt_version": "orchestrator-v1",
            "tool_version": "orchestrator-v1",
        }
        result_state = self._text_to_sql_node(state)
        result = result_state.get("tool_result") or {}
        normalized = NormalizedTextToSqlResult.model_validate(result)
        if normalized.status == "success":
            return ExecutionObservation(
                status="success",
                data=normalized.model_dump(),
                observation=ObservationFacts(
                    facts_found=["sql_result"],
                    decision_signals=["sql_validated", "sql_executed"],
                ),
                execution_quality=ExecutionQuality(
                    sql_valid=True,
                    sql_executed=True,
                ),
                trace=ExecutionTrace(
                    sql=normalized.validated_sql or normalized.generated_sql,
                    used_tables=normalized.used_tables,
                ),
            )

        error_code = normalized.error.get("code") if normalized.error else None
        failure_type = _sql_failure_type(error_code)
        status = "partial" if failure_type == "missing_param" else "fail"
        return ExecutionObservation(
            status=status,
            data=normalized.model_dump(),
            observation=ObservationFacts(
                missing_facts=_sql_missing_facts(error_code),
                decision_signals=["sql_failed"],
                failure_type=failure_type,
            ),
            execution_quality=ExecutionQuality(
                sql_valid=normalized.validated_sql is not None,
                sql_executed=False,
            ),
            trace=ExecutionTrace(
                sql=normalized.validated_sql or normalized.generated_sql,
                used_tables=normalized.used_tables,
            ),
        )


def _normalize_loop_result(trace_id: str, loop_result: ExecutionLoopResult) -> AgentRunResult:
    final_observation = loop_result.observations[-1]
    failure_report = loop_result.failure_report or classify_failure(final_observation)
    error = _normalized_error(failure_report)
    return AgentRunResult(
        trace_id=trace_id,
        plan_trace={
            "initial_plan": loop_result.initial_plan.model_dump(),
            "replan": (
                loop_result.final_plan.model_dump()
                if loop_result.attempts > 1
                else None
            ),
        },
        execution_trace=[
            {"step": index + 1, "result": observation.model_dump()}
            for index, observation in enumerate(loop_result.observations)
        ],
        final_result=AgentFinalResult(
            status=_final_status(final_observation.status),
            data=final_observation.data,
            error=error,
        ),
        debug={
            "route": loop_result.final_plan.intent,
            "failure_analysis": failure_report.model_dump() if failure_report else None,
            "execution_summary": {
                "planner_calls": loop_result.attempts,
                "execution_loops": loop_result.attempts,
                "replanned": loop_result.attempts > 1,
                "max_execution_loop": 2,
                "max_planner_call": 2,
            },
            "observation_trace": [
                observation.observation.model_dump()
                for observation in loop_result.observations
            ],
        },
    )


def _error_result(
    trace_id: str,
    error_type: str,
    message: str,
    recoverable: bool,
    detail: str | None = None,
) -> AgentRunResult:
    error = NormalizedError(
        error_type=error_type,
        message=message,
        recoverable=recoverable,
    )
    return AgentRunResult(
        trace_id=trace_id,
        plan_trace={"initial_plan": None, "replan": None},
        execution_trace=[],
        final_result=AgentFinalResult(
            status="failed",
            data={"detail": detail} if detail else {},
            error=error,
        ),
        debug={
            "route": "error",
            "failure_analysis": error.model_dump(),
            "execution_summary": {
                "planner_calls": 0,
                "execution_loops": 0,
                "replanned": False,
                "max_execution_loop": 2,
                "max_planner_call": 2,
            },
        },
    )


def _normalized_error(
    failure_report: FailureClassificationReport | None,
) -> NormalizedError | None:
    if failure_report is None:
        return None
    mapping = {
        "planner": "planner_error",
        "tool": "tool_error",
        "sql": "sql_error",
        "schema": "sql_error",
        "execution": "execution_error",
        "unknown": "execution_error",
    }
    return NormalizedError(
        error_type=mapping.get(failure_report.source_layer, "execution_error"),
        message=failure_report.reason,
        recoverable=failure_report.failure_type
        in {"tool_miss", "missing_param", "schema_gap"},
    )


def _final_status(status: str) -> str:
    if status == "fail":
        return "failed"
    return status


def _sql_failure_type(error_code: str | None) -> str:
    if error_code in {"mes_db_configuration_error", "mes_sql_execution_error"}:
        return "execution_error"
    if error_code in {"missing_param", "unbounded_scan"}:
        return "missing_param"
    if error_code in {"unknown_column", "forbidden_table", "forbidden_column"}:
        return "schema_gap"
    return "sql_error"


def _sql_missing_facts(error_code: str | None) -> list[str]:
    if error_code == "missing_param":
        return ["sql_parameter"]
    if error_code == "unbounded_scan":
        return ["query_filter"]
    return []


def _collect_used_tables(step_results: list[dict[str, Any]]) -> list[str]:
    tables: set[str] = set()
    for item in step_results:
        trace = item.get("observation", {}).get("trace", {})
        for table in trace.get("used_tables") or []:
            tables.add(table)
    return sorted(tables)
