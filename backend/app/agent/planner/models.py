from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.execution_observation import ExecutionObservation
from app.agent.semantic_router.models import SemanticRouterResult
from app.core.type_defs import JsonObject, JsonValue


PlanIntent = Literal["tool", "sql", "mixed", "unknown"]
PlanStepType = Literal["tool", "sql"]
ExecutionMode = Literal["sequential"]
RoutingSource = Literal["semantic_router", "legacy_fallback"]


class ExecutionHistoryItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    step: int
    route: str
    input: JsonValue
    output: JsonValue = None
    status: Literal["success", "failed"]


class PlannerRequest(BaseModel):
    user_query: str = Field(..., min_length=1, max_length=4000)
    tool_catalog: list[JsonObject] = Field(default_factory=list)
    schema_context: str = ""
    execution_history: list[ExecutionHistoryItem] = Field(default_factory=list)
    previous_plan: JsonObject | None = None
    execution_observation: ExecutionObservation | None = None
    semantic_router_result: SemanticRouterResult | None = None

    @field_validator("user_query")
    @classmethod
    def strip_user_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("user_query cannot be empty.")
        return stripped


class PlanStep(BaseModel):
    step_id: int
    type: PlanStepType
    name: str | None = None
    semantic_domain: str | None = None
    semantic_intent: str | None = None
    query_goal: str
    args: JsonObject = Field(default_factory=dict)
    reason: str
    dependency: list[int] = Field(default_factory=list)
    expected_output: str
    reuse_from_history: int | None = None
    skip_reason: str | None = None
    legacy: bool = False


class ExecutionPlanPolicy(BaseModel):
    mode: ExecutionMode = "sequential"
    stop_condition: str


class DebugTrace(BaseModel):
    classification_reason: str
    tool_selection_reason: str
    sql_intent_reason: str
    risk_assessment: str


class FailureAnalysis(BaseModel):
    source: Literal["planner", "tool", "sql", "execution", "schema", "unknown"]
    reason: str
    related_step: int | None = None


class PlannerPlan(BaseModel):
    user_input: str | None = None
    intent: PlanIntent
    goal: str
    steps: list[PlanStep] = Field(default_factory=list, max_length=5)
    execution_plan: ExecutionPlanPolicy
    confidence: float = Field(..., ge=0, le=1)
    debug_trace: DebugTrace
    failure_analysis: list[FailureAnalysis] = Field(default_factory=list)
    semantic_router_result: JsonObject | None = None
    semantic_router_version: str | None = None
    routing_source: RoutingSource = "legacy_fallback"
