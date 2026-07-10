import logging
import time
import uuid
from typing import cast

from pydantic import BaseModel, Field

from app.agent.capability.loader import CapabilityLoader
from app.agent.capability.router import (
    CapabilityExecutionPlan,
    CapabilityRouter,
    SemanticIntent,
)
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
    FailureType,
    ObservationFacts,
)
from app.agent.planner.models import PlannerPlan, PlannerRequest, PlanStep
from app.agent.planner.planner import DebuggablePlanner
from app.agent.semantic_router import SemanticRouter
from app.agent.state import AgentState
from app.agent.text_to_sql.models import NormalizedTextToSqlResult
from app.agent.nodes.text_to_sql import TextToSqlNode
from app.agent.tools.registry import DEFAULT_TOOL_REGISTRY, ToolRegistry
from app.analytics.event.collector import AgentEventCollector
from app.core.logging import log_event, reset_trace_id, set_trace_id
from app.core.type_defs import JsonObject, JsonValue
from app.domain.persistence.exceptions import PersistenceError


logger = logging.getLogger(__name__)
agent_logger = logging.getLogger("agent")
semantic_logger = logging.getLogger("agent.semantic_router")
planner_logger = logging.getLogger("agent.planner")
capability_logger = logging.getLogger("agent.capability_router")
execution_logger = logging.getLogger("agent.execution")
sql_logger = logging.getLogger("agent.sql")


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
    data: JsonObject = Field(default_factory=dict)
    error: NormalizedError | None = None


class AgentRunResult(BaseModel):
    trace_id: str
    plan_trace: JsonObject
    execution_trace: list[JsonObject]
    final_result: AgentFinalResult
    debug: JsonObject


class AgentOrchestrator:
    def __init__(
        self,
        planner: DebuggablePlanner,
        execution_layer,
        event_collector: AgentEventCollector | None = None,
        semantic_router: SemanticRouter | None = None,
    ):
        self._planner = planner
        self._execution_layer = execution_layer
        self._event_collector = event_collector
        self._semantic_router = semantic_router or SemanticRouter()

    def run(self, request: AgentRunInput) -> AgentRunResult:
        trace_id = uuid.uuid4().hex
        trace_token = set_trace_id(trace_id)
        started_at = time.perf_counter()
        try:
            log_event(
                agent_logger,
                logging.INFO,
                "agent.request.start",
                user_input=request.message,
            )
            semantic_router_result = self._semantic_router.route(request.message)
            log_event(
                semantic_logger,
                logging.INFO,
                "semantic_router.completed",
                domain=semantic_router_result.domain,
                intent=semantic_router_result.intent,
                confidence=semantic_router_result.confidence,
                need_clarification=semantic_router_result.need_clarification,
            )
            log_event(
                semantic_logger,
                logging.DEBUG,
                "semantic_router.entities",
                entities=semantic_router_result.entities,
            )
            planner_request = PlannerRequest(
                user_query=request.message,
                semantic_router_result=semantic_router_result,
            )
            loop_result = ExecutionFeedbackLoop(
                planner=self._planner,
                execution_layer=self._execution_layer,
            ).run(planner_request)
            log_event(
                planner_logger,
                logging.INFO,
                "planner.completed",
                step_count=len(loop_result.initial_plan.steps),
            )
            log_event(
                planner_logger,
                logging.DEBUG,
                "planner.plan",
                plan=_model_json_object(loop_result.initial_plan),
            )
        except Exception as exc:
            duration_ms = elapsed_ms(started_at)
            log_event(
                agent_logger,
                logging.ERROR,
                "agent.request.failed",
                error=type(exc).__name__,
                total_duration_ms=duration_ms,
            )
            result = _error_result(
                trace_id=trace_id,
                error_type="execution_error",
                message="Agent orchestration failed.",
                recoverable=False,
                detail=str(exc),
            )
            self._record_error_trace(request, result, duration_ms)
            log_event(
                agent_logger,
                logging.INFO,
                "agent.request.finished",
                total_duration_ms=duration_ms,
                success=False,
            )
            reset_trace_id(trace_token)
            return result

        duration_ms = elapsed_ms(started_at)
        result = _normalize_loop_result(trace_id, loop_result)
        log_event(
            agent_logger,
            logging.INFO,
            "agent.request.finished",
            total_duration_ms=duration_ms,
            success=result.final_result.status == "success",
            final_status=result.final_result.status,
            planner_intent=loop_result.initial_plan.intent,
            replanned=loop_result.attempts > 1,
            planner_calls=loop_result.attempts,
            execution_loops=loop_result.attempts,
        )
        self._record_success_trace(request, loop_result, result, duration_ms)
        reset_trace_id(trace_token)
        return result

    def _record_success_trace(
        self,
        request: AgentRunInput,
        loop_result: ExecutionLoopResult,
        result: AgentRunResult,
        duration_ms: int,
    ) -> None:
        if self._event_collector is None:
            return
        try:
            _record_loop_events(self._event_collector, result.trace_id, loop_result, duration_ms)
            self._event_collector.record_trace(
                trace_id=result.trace_id,
                user_query=request.message,
                plan_json=result.plan_trace,
                final_result=_model_json_object(result.final_result),
                status=result.final_result.status,
                loop_depth=loop_result.attempts,
            )
            if result.final_result.error is not None:
                failure_report = loop_result.failure_report or classify_failure(
                    loop_result.observations[-1]
                )
                self._event_collector.record_failure(
                    trace_id=result.trace_id,
                    failure_type=(
                        failure_report.failure_type if failure_report is not None else None
                    ),
                    source_layer=(
                        failure_report.source_layer if failure_report is not None else None
                    ),
                    error_code=result.final_result.error.error_type,
                    summary=result.final_result.error.message,
                    detail_json=_optional_json_object(result.debug.get("failure_analysis")),
                )
        except PersistenceError as exc:
            logger.error("Agent analytics persistence failed exception_type=%s", type(exc).__name__)

    def _record_error_trace(
        self,
        request: AgentRunInput,
        result: AgentRunResult,
        duration_ms: int,
    ) -> None:
        if self._event_collector is None:
            return
        try:
            self._event_collector.record_event(
                event_type="LOOP_START",
                trace_id=result.trace_id,
                component="execution_loop",
                input_json={"message": request.message},
            )
            self._event_collector.record_event(
                event_type="LOOP_END",
                trace_id=result.trace_id,
                component="execution_loop",
                output_json={"status": result.final_result.status},
                latency_ms=duration_ms,
            )
            self._event_collector.record_trace(
                trace_id=result.trace_id,
                user_query=request.message,
                plan_json=result.plan_trace,
                final_result=_model_json_object(result.final_result),
                status=result.final_result.status,
                loop_depth=0,
            )
            self._event_collector.record_failure(
                trace_id=result.trace_id,
                failure_type="execution_error",
                source_layer="execution",
                error_code=result.final_result.error.error_type if result.final_result.error else None,
                summary=(
                    result.final_result.error.message
                    if result.final_result.error
                    else "Agent orchestration failed."
                ),
                detail_json=_optional_json_object(result.debug.get("failure_analysis")),
            )
        except PersistenceError as exc:
            logger.error("Agent analytics persistence failed exception_type=%s", type(exc).__name__)


class PlanExecutionAdapter:
    def __init__(
        self,
        text_to_sql_node: TextToSqlNode,
        registry: ToolRegistry = DEFAULT_TOOL_REGISTRY,
        capability_router: CapabilityRouter | None = None,
    ):
        self._text_to_sql_node = text_to_sql_node
        self._registry = registry
        self._capability_router = capability_router or CapabilityRouter(CapabilityLoader().load())

    def execute(self, plan: PlannerPlan) -> ExecutionObservation:
        if not plan.steps:
            log_event(
                planner_logger,
                logging.WARNING,
                "planner.empty_plan",
                intent=plan.intent,
            )
            return ExecutionObservation(
                status="fail",
                observation=ObservationFacts(
                    missing_facts=["plan.steps"],
                    failure_type="missing_param",
                ),
                execution_quality=ExecutionQuality(),
                trace=ExecutionTrace(
                    user_input=plan.user_input,
                    semantic_router_result=plan.semantic_router_result,
                    semantic_router_version=plan.semantic_router_version,
                    routing_source=plan.routing_source,
                    legacy_used=plan.routing_source == "legacy_fallback",
                    success=False,
                    error_reason="plan.steps",
                ),
            )

        step_results: list[JsonObject] = []
        for step in plan.steps:
            log_event(
                execution_logger,
                logging.INFO,
                "execution.step.started",
                step_id=step.step_id,
                step_type=step.type,
                capability_name=step.name,
                argument_keys=sorted(step.args.keys()),
            )
            observation = _with_plan_trace_metadata(self._execute_step(plan, step), plan)
            log_event(
                execution_logger,
                logging.INFO,
                "execution.completed",
                step_id=step.step_id,
                step_type=step.type,
                capability_name=observation.trace.capability_name,
                tool_name=observation.trace.tool_name,
                execution_type=observation.trace.execution_type,
                success=observation.status == "success",
                error_reason=(
                    observation.observation.failure_type
                    or observation.trace.error_type
                    or observation.trace.error_reason
                ),
                missing_fields=observation.observation.missing_facts,
            )
            step_results.append(
                {
                    "step_id": step.step_id,
                    "type": step.type,
                    "name": step.name,
                    "observation": _model_json_object(observation),
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
                "last_result": _last_step_data(step_results),
            },
            observation=ObservationFacts(
                facts_found=[f"step_{item['step_id']}" for item in step_results],
                decision_signals=["all_planned_steps_succeeded"],
            ),
            execution_quality=ExecutionQuality(
                tool_hit=any(item["type"] == "tool" for item in step_results) or None,
                sql_valid=_collect_sql_valid(step_results),
                sql_executed=_collect_sql_executed(step_results),
            ),
            trace=ExecutionTrace(
                user_input=plan.user_input,
                semantic_router_result=plan.semantic_router_result,
                semantic_router_version=plan.semantic_router_version,
                routing_source=plan.routing_source,
                legacy_used=plan.routing_source == "legacy_fallback",
                capability_source=_collect_trace_field(step_results, "capability_source"),
                capability_name=_collect_trace_field(step_results, "capability_name"),
                catalog_version=_collect_trace_field(step_results, "catalog_version"),
                execution_type=_collect_trace_field(step_results, "execution_type"),
                tool_name=_collect_trace_field(step_results, "tool_name"),
                sql=_collect_sql(step_results),
                used_tables=_collect_used_tables(step_results),
                sql_executed=_collect_sql_executed(step_results),
                error_type=_collect_error_type(step_results),
                success=True,
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
        routed_step = self._route_tool_step(step)
        if routed_step.status != "matched":
            log_event(
                capability_logger,
                logging.WARNING,
                "capability.not_found",
                capability_name=routed_step.capability,
                routing_source=(
                    "semantic_router"
                    if step.semantic_domain and step.semantic_intent
                    else "legacy_fallback"
                ),
                route_status=routed_step.status,
                reason=routed_step.reason,
            )
            missing_fact = (
                f"{step.semantic_domain}.{step.semantic_intent}"
                if step.semantic_domain and step.semantic_intent
                else step.name or "capability"
            )
            return ExecutionObservation(
                status="fail",
                data={
                    "error": routed_step.reason,
                    "route_status": routed_step.status,
                    "capability": routed_step.capability,
                },
                observation=ObservationFacts(
                    missing_facts=[missing_fact],
                    decision_signals=[routed_step.status],
                    failure_type="tool_miss",
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    tool_name=routed_step.executor,
                    error_type=routed_step.status,
                ),
            )
        log_event(
            capability_logger,
            logging.INFO,
            "capability.matched",
            capability_name=routed_step.capability,
            routing_source=(
                "semantic_router"
                if step.semantic_domain and step.semantic_intent
                else "legacy_fallback"
            ),
            execution_type=routed_step.execution_type,
            executor=routed_step.executor,
        )
        log_event(
            execution_logger,
            logging.INFO,
            "execution.started",
            execution_type=routed_step.execution_type,
            capability_name=routed_step.capability,
        )
        step = step.model_copy(
            update={
                "name": routed_step.executor,
                "args": routed_step.arguments,
            }
        )
        if not step.name:
            return ExecutionObservation(
                status="fail",
                observation=ObservationFacts(
                    missing_facts=["tool_name"],
                    failure_type="missing_param",
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    error_type="missing_param",
                ),
            )
        capability = self._registry.get_capability(step.name)
        if capability is None:
            return ExecutionObservation(
                status="fail",
                data={"error": f"Unknown capability: {step.name}."},
                observation=ObservationFacts(
                    missing_facts=[step.name],
                    decision_signals=["tool_failed"],
                    failure_type="tool_miss",
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    tool_name=step.name,
                ),
            )
        if capability.status != "enabled":
            reason = capability.blocked_reason or f"Capability is not executable: {step.name}."
            return ExecutionObservation(
                status="fail",
                data={"error": reason, "capability_status": capability.status},
                observation=ObservationFacts(
                    missing_facts=[step.name],
                    decision_signals=["capability_not_executable"],
                    failure_type="tool_miss",
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    tool_name=step.name,
                ),
            )
        missing_fields = _missing_required_fields(
            capability.required_argument_groups,
            step.args,
        )
        if missing_fields:
            return ExecutionObservation(
                status="partial",
                data={
                    "error": "缺少热处理记录标识，请提供 record_no、record_id 或 object_id。",
                    "missing_fields": missing_fields,
                },
                observation=ObservationFacts(
                    missing_facts=missing_fields,
                    decision_signals=["tool_missing_required_arguments"],
                    failure_type="missing_param",
                ),
                execution_quality=ExecutionQuality(tool_hit=False),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    tool_name=step.name,
                ),
            )
        try:
            started_at = time.perf_counter()
            log_event(
                execution_logger,
                logging.INFO,
                "tool.execute.start",
                tool_name=step.name,
                capability_name=routed_step.capability,
            )
            data = self._registry.execute(step.name, step.args)
            duration_ms = elapsed_ms(started_at)
            log_event(
                execution_logger,
                logging.INFO,
                "tool.execute.completed",
                tool_name=step.name,
                capability_name=routed_step.capability,
                success=True,
                duration_ms=duration_ms,
            )
            tool_trace = _registry_last_trace(self._registry)
            return ExecutionObservation(
                status="success",
                data={"tool_result": data},
                observation=ObservationFacts(
                    facts_found=[step.name],
                    decision_signals=["tool_executed"],
                ),
                execution_quality=ExecutionQuality(
                    tool_hit=True,
                    sql_valid=_trace_bool(tool_trace, "sql_valid"),
                    sql_executed=_trace_bool(tool_trace, "sql_executed"),
                ),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    tool_name=step.name,
                    sql=_trace_str(tool_trace, "sql"),
                    used_tables=_trace_str_list(tool_trace, "used_tables"),
                    sql_executed=_trace_bool(tool_trace, "sql_executed"),
                    error_type=_trace_str(tool_trace, "error_type"),
                ),
            )
        except Exception as exc:
            log_event(
                execution_logger,
                logging.ERROR,
                "tool.execute.failed",
                tool_name=step.name,
                capability_name=routed_step.capability,
                success=False,
                error=type(exc).__name__,
            )
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
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    tool_name=step.name,
                ),
            )

    def _route_tool_step(self, step: PlanStep) -> CapabilityExecutionPlan:
        if step.semantic_domain and step.semantic_intent:
            return self._capability_router.route(
                SemanticIntent(
                    domain=step.semantic_domain,
                    intent=step.semantic_intent,
                    arguments=step.args,
                )
            )
        return _legacy_tool_route(step)

    def _execute_sql_step(self, plan: PlannerPlan, step: PlanStep) -> ExecutionObservation:
        routed_step = self._route_sql_step(step)
        if routed_step.status != "matched":
            log_event(
                capability_logger,
                logging.WARNING,
                "capability.not_found",
                capability_name=routed_step.capability,
                routing_source=(
                    "semantic_router"
                    if step.semantic_domain and step.semantic_intent
                    else "legacy_fallback"
                ),
                route_status=routed_step.status,
                reason=routed_step.reason,
            )
            missing_fact = (
                f"{step.semantic_domain}.{step.semantic_intent}"
                if step.semantic_domain and step.semantic_intent
                else "readonly_sql_capability"
            )
            return ExecutionObservation(
                status="fail",
                data={
                    "error": routed_step.reason,
                    "route_status": routed_step.status,
                    "capability": routed_step.capability,
                },
                observation=ObservationFacts(
                    missing_facts=[missing_fact],
                    decision_signals=[routed_step.status],
                    failure_type="schema_gap",
                ),
                execution_quality=ExecutionQuality(sql_valid=False, sql_executed=False),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    error_type=routed_step.status,
                    success=False,
                    error_reason=routed_step.reason,
                ),
            )
        log_event(
            capability_logger,
            logging.INFO,
            "capability.matched",
            capability_name=routed_step.capability,
            routing_source=(
                "semantic_router"
                if step.semantic_domain and step.semantic_intent
                else "legacy_fallback"
            ),
            execution_type=routed_step.execution_type,
            executor=routed_step.executor,
        )
        log_event(
            execution_logger,
            logging.INFO,
            "execution.started",
            execution_type=routed_step.execution_type,
            capability_name=routed_step.capability,
        )
        question = step.args.get("question")
        state: AgentState = {
            "user_query": question if isinstance(question, str) else plan.goal,
            "conversation_key": None,
            "agent_version": "orchestrator-v1",
            "prompt_version": "orchestrator-v1",
            "tool_version": "orchestrator-v1",
        }
        started_at = time.perf_counter()
        result_state = self._text_to_sql_node(state)
        result = result_state.get("tool_result") or {}
        normalized = NormalizedTextToSqlResult.model_validate(result)
        duration_ms = normalized.duration_ms or elapsed_ms(started_at)
        if sql_logger.isEnabledFor(logging.DEBUG):
            log_event(
                sql_logger,
                logging.DEBUG,
                "sql.execute",
                sql=normalized.validated_sql or normalized.generated_sql,
                parameters={key: value for key, value in step.args.items() if key != "question"},
                duration_ms=duration_ms,
                success=normalized.status == "success",
            )
        if normalized.status == "success":
            return ExecutionObservation(
                status="success",
                data=_model_json_object(normalized),
                observation=ObservationFacts(
                    facts_found=["sql_result"],
                    decision_signals=["sql_validated", "sql_executed"],
                ),
                execution_quality=ExecutionQuality(
                    sql_valid=True,
                    sql_executed=True,
                ),
                trace=ExecutionTrace(
                    capability_source=routed_step.capability_source,
                    capability_name=routed_step.capability,
                    catalog_version=routed_step.catalog_version,
                    execution_type=routed_step.execution_type,
                    sql=normalized.validated_sql or normalized.generated_sql,
                    used_tables=normalized.used_tables,
                    sql_executed=True,
                    success=True,
                ),
            )

        error_code = normalized.error.get("code") if normalized.error else None
        failure_type = _sql_failure_type(error_code)
        status = "partial" if failure_type == "missing_param" else "fail"
        return ExecutionObservation(
            status=status,
            data=_model_json_object(normalized),
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
                capability_source=routed_step.capability_source,
                capability_name=routed_step.capability,
                catalog_version=routed_step.catalog_version,
                execution_type=routed_step.execution_type,
                sql=normalized.validated_sql or normalized.generated_sql,
                used_tables=normalized.used_tables,
                sql_executed=False,
                error_type=failure_type,
                success=False,
                error_reason=error_code,
            ),
        )

    def _route_sql_step(self, step: PlanStep) -> CapabilityExecutionPlan:
        if step.semantic_domain and step.semantic_intent:
            return self._capability_router.route(
                SemanticIntent(
                    domain=step.semantic_domain,
                    intent=step.semantic_intent,
                    arguments=step.args,
                )
            )
        return CapabilityExecutionPlan(
            status="matched",
            capability=None,
            execution_type="readonly_sql",
            executor="text_to_sql",
            arguments=step.args,
            capability_source="catalog",
            catalog_version="legacy",
            reason="Legacy planner supplied a direct SQL route.",
        )


def _normalize_loop_result(trace_id: str, loop_result: ExecutionLoopResult) -> AgentRunResult:
    final_observation = loop_result.observations[-1]
    failure_report = loop_result.failure_report or classify_failure(final_observation)
    error = _normalized_error(failure_report)
    return AgentRunResult(
        trace_id=trace_id,
        plan_trace={
            "initial_plan": _model_json_object(loop_result.initial_plan),
            "replan": (
                _model_json_object(loop_result.final_plan)
                if loop_result.attempts > 1
                else None
            ),
        },
        execution_trace=[
            {
                "step": index + 1,
                "semantic_router_result": _semantic_trace_for_index(loop_result, index),
                "semantic_router_version": _semantic_version_for_index(loop_result, index),
                "routing_source": _routing_source_for_index(loop_result, index),
                "result": _model_json_object(observation),
            }
            for index, observation in enumerate(loop_result.observations)
        ],
        final_result=AgentFinalResult(
            status=_final_status(final_observation.status),
            data=final_observation.data,
            error=error,
        ),
        debug={
            "route": loop_result.final_plan.intent,
            "failure_analysis": _model_json_object(failure_report) if failure_report else None,
            "execution_summary": {
                "planner_calls": loop_result.attempts,
                "execution_loops": loop_result.attempts,
                "replanned": loop_result.attempts > 1,
                "max_execution_loop": 2,
                "max_planner_call": 2,
            },
            "observation_trace": [
                _model_json_object(observation.observation)
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
            "failure_analysis": _model_json_object(error),
            "execution_summary": {
                "planner_calls": 0,
                "execution_loops": 0,
                "replanned": False,
                "max_execution_loop": 2,
                "max_planner_call": 2,
            },
        },
    )


def _semantic_trace_for_index(
    loop_result: ExecutionLoopResult,
    index: int,
) -> JsonObject | None:
    plan = loop_result.initial_plan if index == 0 else loop_result.final_plan
    return plan.semantic_router_result


def _semantic_version_for_index(
    loop_result: ExecutionLoopResult,
    index: int,
) -> str | None:
    plan = loop_result.initial_plan if index == 0 else loop_result.final_plan
    return plan.semantic_router_version


def _routing_source_for_index(
    loop_result: ExecutionLoopResult,
    index: int,
) -> str:
    plan = loop_result.initial_plan if index == 0 else loop_result.final_plan
    return plan.routing_source


def _with_plan_trace_metadata(
    observation: ExecutionObservation,
    plan: PlannerPlan,
) -> ExecutionObservation:
    return observation.model_copy(
        update={
            "trace": observation.trace.model_copy(
                update={
                    "semantic_router_result": plan.semantic_router_result,
                    "semantic_router_version": plan.semantic_router_version,
                    "routing_source": plan.routing_source,
                    "user_input": plan.user_input,
                    "legacy_used": plan.routing_source == "legacy_fallback",
                    "success": observation.status == "success",
                    "error_reason": (
                        observation.observation.failure_type
                        or observation.trace.error_type
                        or observation.trace.error_reason
                    ),
                }
            )
        }
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
    if (
        failure_report.failure_type == "missing_param"
        and any(_is_record_identifier_missing(fact) for fact in failure_report.missing_facts)
    ):
        message = "缺少热处理记录标识，请提供 record_no、record_id 或 object_id。"
    else:
        message = failure_report.reason
    return NormalizedError(
        error_type=mapping.get(failure_report.source_layer, "execution_error"),
        message=message,
        recoverable=failure_report.failure_type
        in {"tool_miss", "missing_param", "schema_gap"},
    )


def _final_status(status: str) -> str:
    if status == "fail":
        return "failed"
    return status


def _sql_failure_type(error_code: str | None) -> FailureType:
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


def _missing_required_fields(
    required_argument_groups: list[list[str]],
    arguments: JsonObject,
) -> list[str]:
    for group in required_argument_groups:
        if all(arguments.get(field) for field in group):
            return []
    if len(required_argument_groups) > 1 and all(len(group) == 1 for group in required_argument_groups):
        return ["record identifier: record_id or record_no or object_id"]
    return [field for field in required_argument_groups[0] if not arguments.get(field)]


def _is_record_identifier_missing(fact: str) -> bool:
    return (
        "record identifier" in fact
        or fact.endswith(".args")
        or fact in {"record_id", "record_no", "object_id"}
    )


def _legacy_tool_route(step: PlanStep) -> CapabilityExecutionPlan:
    if not step.name:
        return CapabilityExecutionPlan(
            status="capability_not_found",
            arguments=step.args,
            reason="Legacy tool step did not include a capability name.",
        )
    return CapabilityExecutionPlan(
        status="matched",
        capability=step.name,
        execution_type="tool",
        executor=step.name,
        arguments=step.args,
        capability_source="catalog",
        catalog_version="legacy",
        reason="Legacy planner supplied a direct tool name.",
    )


def _collect_used_tables(step_results: list[JsonObject]) -> list[str]:
    tables: set[str] = set()
    for item in step_results:
        observation = item.get("observation")
        if not isinstance(observation, dict):
            continue
        trace = observation.get("trace")
        if not isinstance(trace, dict):
            continue
        used_tables = trace.get("used_tables")
        if not isinstance(used_tables, list):
            continue
        for table in used_tables:
            if isinstance(table, str):
                tables.add(table)
    return sorted(tables)


def _collect_trace_field(step_results: list[JsonObject], key: str) -> str | None:
    for item in step_results:
        trace = _step_trace(item)
        if trace is None:
            continue
        value = trace.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _collect_sql(step_results: list[JsonObject]) -> str | None:
    for item in step_results:
        trace = _step_trace(item)
        if trace is None:
            continue
        sql = trace.get("sql")
        if isinstance(sql, str) and sql.strip():
            return sql
    return None


def _collect_sql_executed(step_results: list[JsonObject]) -> bool | None:
    found = None
    for item in step_results:
        trace = _step_trace(item)
        if trace is not None and isinstance(trace.get("sql_executed"), bool):
            found = trace["sql_executed"]
        observation = item.get("observation")
        if isinstance(observation, dict):
            quality = observation.get("execution_quality")
            if isinstance(quality, dict) and isinstance(quality.get("sql_executed"), bool):
                found = quality["sql_executed"]
    return found


def _collect_sql_valid(step_results: list[JsonObject]) -> bool | None:
    found = None
    for item in step_results:
        observation = item.get("observation")
        if not isinstance(observation, dict):
            continue
        quality = observation.get("execution_quality")
        if isinstance(quality, dict) and isinstance(quality.get("sql_valid"), bool):
            found = quality["sql_valid"]
    return found


def _collect_error_type(step_results: list[JsonObject]) -> str | None:
    for item in step_results:
        trace = _step_trace(item)
        if trace is None:
            continue
        error_type = trace.get("error_type")
        if isinstance(error_type, str) and error_type:
            return error_type
    return None


def _step_trace(step_result: JsonObject) -> JsonObject | None:
    observation = step_result.get("observation")
    if not isinstance(observation, dict):
        return None
    trace = observation.get("trace")
    return trace if isinstance(trace, dict) else None


def _registry_last_trace(registry: ToolRegistry) -> JsonObject | None:
    trace_reader = getattr(registry, "last_trace", None)
    if not callable(trace_reader):
        return None
    trace = trace_reader()
    return trace if isinstance(trace, dict) else None


def _trace_bool(trace: JsonObject | None, key: str) -> bool | None:
    if trace is None:
        return None
    value = trace.get(key)
    return value if isinstance(value, bool) else None


def _trace_str(trace: JsonObject | None, key: str) -> str | None:
    if trace is None:
        return None
    value = trace.get(key)
    return value if isinstance(value, str) and value else None


def _trace_str_list(trace: JsonObject | None, key: str) -> list[str]:
    if trace is None:
        return []
    value = trace.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def elapsed_ms(started_at: float) -> int:
    return max(int((time.perf_counter() - started_at) * 1000), 0)


def _record_loop_events(
    collector: AgentEventCollector,
    trace_id: str,
    loop_result: ExecutionLoopResult,
    duration_ms: int,
) -> None:
    collector.record_event(
        event_type="LOOP_START",
        trace_id=trace_id,
        component="execution_loop",
        input_json={"attempts": loop_result.attempts},
    )
    collector.record_event(
        event_type="PLANNER_START",
        trace_id=trace_id,
        component="planner",
        step_id=1,
        input_json={"replan": False},
    )
    collector.record_event(
        event_type="PLANNER_END",
        trace_id=trace_id,
        component="planner",
        step_id=1,
        output_json=_model_json_object(loop_result.initial_plan),
    )
    if loop_result.attempts > 1:
        collector.record_event(
            event_type="REPLAN_TRIGGER",
            trace_id=trace_id,
            component="execution_loop",
            input_json=_model_json_object(loop_result.observations[0].observation),
        )
        collector.record_event(
            event_type="PLANNER_START",
            trace_id=trace_id,
            component="planner",
            step_id=2,
            input_json={"replan": True},
        )
        collector.record_event(
            event_type="PLANNER_END",
            trace_id=trace_id,
            component="planner",
            step_id=2,
            output_json=_model_json_object(loop_result.final_plan),
        )
    for observation_index, observation in enumerate(loop_result.observations):
        _record_observation_events(
            collector,
            trace_id,
            loop_result.final_plan if observation_index else loop_result.initial_plan,
            observation,
        )
    collector.record_event(
        event_type="LOOP_END",
        trace_id=trace_id,
        component="execution_loop",
        output_json={"status": loop_result.status, "attempts": loop_result.attempts},
        latency_ms=duration_ms,
    )


def _record_observation_events(
    collector: AgentEventCollector,
    trace_id: str,
    plan: PlannerPlan,
    observation: ExecutionObservation,
) -> None:
    raw_step_results = observation.data.get("step_results")
    step_results = (
        [cast(JsonObject, item) for item in raw_step_results if isinstance(item, dict)]
        if isinstance(raw_step_results, list)
        else []
    )
    if step_results:
        for item in step_results:
            step_observation = _json_object_or_empty(item.get("observation"))
            step_type = item.get("type")
            trace = _json_object_or_empty(step_observation.get("trace"))
            component_value = item.get("name") or trace.get("tool_name") or trace.get("capability_name")
            component = component_value if isinstance(component_value, str) else "text_to_sql"
            step_id_value = item.get("step_id")
            step_id = step_id_value if isinstance(step_id_value, int) else None
            if step_type == "tool":
                collector.record_event(
                    event_type="TOOL_MATCH",
                    trace_id=trace_id,
                    component=component,
                    step_id=step_id,
                    input_json={"step": item},
                )
                collector.record_event(
                    event_type=(
                        "TOOL_EXECUTE_SUCCESS"
                        if step_observation.get("status") == "success"
                        else "TOOL_EXECUTE_FAIL"
                    ),
                    trace_id=trace_id,
                    component=component,
                    step_id=step_id,
                    output_json=step_observation,
                )
            else:
                _record_sql_events(collector, trace_id, component, step_id, step_observation)
        return

    if plan.steps:
        first_step = plan.steps[0]
        trace = _model_json_object(observation.trace)
        component = first_step.name or trace.get("tool_name") or trace.get("capability_name") or "text_to_sql"
        if first_step.type == "tool":
            collector.record_event(
                event_type="TOOL_MATCH",
                trace_id=trace_id,
                component=component,
                step_id=first_step.step_id,
                input_json=_model_json_object(first_step),
            )
            collector.record_event(
                event_type="TOOL_EXECUTE_FAIL",
                trace_id=trace_id,
                component=component,
                step_id=first_step.step_id,
                output_json=_model_json_object(observation),
            )
        else:
            _record_sql_events(
                collector,
                trace_id,
                component,
                first_step.step_id,
                _model_json_object(observation),
            )


def _record_sql_events(
    collector: AgentEventCollector,
    trace_id: str,
    component: str,
    step_id: int | None,
    observation: JsonObject,
) -> None:
    data = _json_object_or_empty(observation.get("data")) or observation
    duration_value = data.get("duration_ms")
    latency_ms = duration_value if isinstance(duration_value, int) else None
    collector.record_event(
        event_type="SQL_GENERATE",
        trace_id=trace_id,
        component=component,
        step_id=step_id,
        output_json={"generated_sql": data.get("generated_sql")},
    )
    collector.record_event(
        event_type="SQL_VALIDATE",
        trace_id=trace_id,
        component=component,
        step_id=step_id,
        output_json={"validated_sql": data.get("validated_sql")},
    )
    collector.record_event(
        event_type=(
            "SQL_EXECUTE_SUCCESS"
            if observation.get("status") == "success" or data.get("status") == "success"
            else "SQL_EXECUTE_FAIL"
        ),
        trace_id=trace_id,
        component=component,
        step_id=step_id,
        output_json=observation,
        latency_ms=latency_ms,
    )


def _model_json_object(model: BaseModel) -> JsonObject:
    return cast(JsonObject, model.model_dump(mode="json"))


def _optional_json_object(value: JsonValue) -> JsonObject | None:
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return None


def _json_object_or_empty(value: JsonValue | None) -> JsonObject:
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return {}


def _last_step_data(step_results: list[JsonObject]) -> JsonValue:
    if not step_results:
        return {}
    observation = _json_object_or_empty(step_results[-1].get("observation"))
    return observation.get("data") or {}
