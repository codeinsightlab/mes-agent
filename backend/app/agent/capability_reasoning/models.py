from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.type_defs import JsonObject


ContextLevel = Literal["catalog_only", "catalog_with_business_facts"]


class CapabilityCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    confidence: float
    reason: str

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class CapabilityReasoningResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    context_level: ContextLevel
    candidate_capabilities: list[CapabilityCandidate] = Field(default_factory=list)
    selected_capability: str | None = None
    entities: JsonObject = Field(default_factory=dict)
    confidence: float = 0
    need_clarification: bool = True
    clarification_reason: str | None = None

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @model_validator(mode="before")
    @classmethod
    def forbid_execution_fields(cls, values):
        if not isinstance(values, dict):
            return values
        forbidden = {"sql", "repository", "database", "api_call", "tool_call"}
        present = sorted(forbidden.intersection(values))
        if present:
            raise ValueError(f"Capability reasoning must not output execution fields: {present}")
        return values


class BusinessFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[str] = Field(default_factory=list)


class CapabilityValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "matched",
        "capability_not_found",
        "capability_not_executable",
        "missing_required_entities",
        "need_clarification",
    ]
    selected_capability: str | None = None
    execution_type: str | None = None
    executor: str | None = None
    entities: JsonObject = Field(default_factory=dict)
    missing_entities: list[str] = Field(default_factory=list)
    need_clarification: bool = False
    clarification_reason: str | None = None
