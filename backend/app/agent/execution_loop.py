import logging
from typing import Protocol

from pydantic import BaseModel, Field

from app.agent.execution_observation import (
    ExecutionObservation,
    FailureClassificationReport,
)
from app.agent.planner.models import PlannerPlan, PlannerRequest
from app.agent.planner.planner import DebuggablePlanner


MAX_LOOP_ATTEMPTS = 2
logger = logging.getLogger(__name__)


class PlanExecutionLayer(Protocol):
    def execute(self, plan: PlannerPlan) -> ExecutionObservation:
        ...


class ExecutionLoopResult(BaseModel):
    status: str
    attempts: int
    initial_plan: PlannerPlan
    final_plan: PlannerPlan
    observations: list[ExecutionObservation] = Field(default_factory=list)
    failure_report: FailureClassificationReport | None = None


class ExecutionFeedbackLoop:
    def __init__(
        self,
        planner: DebuggablePlanner,
        execution_layer: PlanExecutionLayer,
        max_attempts: int = MAX_LOOP_ATTEMPTS,
    ):
        if max_attempts != MAX_LOOP_ATTEMPTS:
            raise ValueError("ExecutionFeedbackLoop V1 only allows exactly 2 attempts.")
        self._planner = planner
        self._execution_layer = execution_layer
        self._max_attempts = max_attempts

    def run(self, request: PlannerRequest) -> ExecutionLoopResult:
        initial_plan = self._planner.plan(request)
        logger.info(
            "Execution loop initial plan intent=%s step_count=%s step_types=%s capability_names=%s",
            initial_plan.intent,
            len(initial_plan.steps),
            [step.type for step in initial_plan.steps],
            [step.name for step in initial_plan.steps],
        )
        first_observation = self._execution_layer.execute(initial_plan)
        observations = [first_observation]
        logger.info(
            "Execution loop first observation status=%s missing_fields=%s replan_required=%s",
            first_observation.status,
            first_observation.observation.missing_facts,
            _needs_replan(first_observation),
        )

        if not _needs_replan(first_observation):
            return ExecutionLoopResult(
                status=first_observation.status,
                attempts=1,
                initial_plan=initial_plan,
                final_plan=initial_plan,
                observations=observations,
                failure_report=classify_failure(first_observation),
            )

        refined_request = request.model_copy(
            update={
                "previous_plan": initial_plan.model_dump(),
                "execution_observation": first_observation,
            }
        )
        refined_plan = self._planner.plan(refined_request)
        logger.info(
            "Execution loop replan intent=%s step_count=%s step_types=%s capability_names=%s",
            refined_plan.intent,
            len(refined_plan.steps),
            [step.type for step in refined_plan.steps],
            [step.name for step in refined_plan.steps],
        )
        final_observation = self._execution_layer.execute(refined_plan)
        observations.append(final_observation)
        logger.info(
            "Execution loop final observation status=%s missing_fields=%s",
            final_observation.status,
            final_observation.observation.missing_facts,
        )
        return ExecutionLoopResult(
            status=final_observation.status,
            attempts=self._max_attempts,
            initial_plan=initial_plan,
            final_plan=refined_plan,
            observations=observations,
            failure_report=classify_failure(final_observation),
        )


def _needs_replan(observation: ExecutionObservation) -> bool:
    return (
        observation.status == "partial"
        or bool(observation.observation.missing_facts)
    )


def classify_failure(
    observation: ExecutionObservation,
) -> FailureClassificationReport | None:
    failure_type = observation.observation.failure_type
    if observation.status == "success" and not failure_type:
        return None
    missing_facts = observation.observation.missing_facts
    if failure_type == "tool_miss":
        source = "tool"
        reason = "Tool was missing, mismatched, or did not return the expected fact."
    elif failure_type == "sql_error":
        source = "sql"
        reason = "SQL generation or validation failed."
    elif failure_type == "missing_param":
        source = "planner"
        reason = "Plan lacks required parameters or facts to execute completely."
    elif failure_type == "schema_gap":
        source = "schema"
        reason = "The requested fact is not represented in the allowed schema context."
    elif failure_type == "execution_error":
        source = "execution"
        reason = "Execution layer failed after a plan was produced."
    elif missing_facts:
        source = "planner"
        reason = "Execution returned partial information and reported missing facts."
    else:
        source = "unknown"
        reason = "Execution did not succeed, but no specific failure type was reported."
    return FailureClassificationReport(
        failure_type=failure_type,
        source_layer=source,
        reason=reason,
        missing_facts=missing_facts,
    )
