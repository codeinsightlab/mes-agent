from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.type_defs import JsonObject


CapabilityRouteStatus = Literal[
    "matched",
    "capability_not_found",
    "capability_not_executable",
]


class SemanticIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    intent: str
    entity_type: str | None = None
    arguments: JsonObject = Field(default_factory=dict)

    @field_validator("domain", "intent")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must not be empty")
        return stripped


class CapabilityExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CapabilityRouteStatus
    capability: str | None = None
    execution_type: str | None = None
    executor: str | None = None
    arguments: JsonObject = Field(default_factory=dict)
    capability_source: Literal["catalog"] = "catalog"
    catalog_version: str = "v1"
    reason: str
