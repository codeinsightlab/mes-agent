from typing import Literal

from pydantic import BaseModel, Field

from app.core.type_defs import JsonObject


ExecutionStatus = Literal["success", "fail", "partial"]
FailureType = Literal[
    "tool_miss",
    "sql_error",
    "missing_param",
    "schema_gap",
    "execution_error",
]


class ObservationFacts(BaseModel):
    facts_found: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    decision_signals: list[str] = Field(default_factory=list)
    failure_type: FailureType | None = None


class ExecutionQuality(BaseModel):
    tool_hit: bool | None = None
    sql_valid: bool | None = None
    sql_executed: bool | None = None


class ExecutionTrace(BaseModel):
    tool_name: str | None = None
    sql: str | None = None
    used_tables: list[str] = Field(default_factory=list)
    sql_executed: bool | None = None
    error_type: str | None = None


class ExecutionObservation(BaseModel):
    status: ExecutionStatus
    data: JsonObject = Field(default_factory=dict)
    observation: ObservationFacts = Field(default_factory=ObservationFacts)
    execution_quality: ExecutionQuality = Field(default_factory=ExecutionQuality)
    trace: ExecutionTrace = Field(default_factory=ExecutionTrace)


class FailureClassificationReport(BaseModel):
    failure_type: FailureType | None = None
    source_layer: Literal["planner", "tool", "sql", "execution", "schema", "unknown"]
    reason: str
    missing_facts: list[str] = Field(default_factory=list)
