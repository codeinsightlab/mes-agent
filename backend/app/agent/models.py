from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RouteName = Literal["tool", "text_to_sql", "blocked", "clarification", "error"]
CapabilityStatus = Literal["enabled", "blocked", "disabled"]


class HeatToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    record_no: str | None = None
    object_id: str | None = None
    item_code: str | None = None
    lot_code: str | None = None

    @field_validator("record_id", "record_no", "object_id", "item_code", "lot_code")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped

    def has_record_identifier(self) -> bool:
        return any([self.record_id, self.record_no, self.object_id])


class ToolMatchDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched: bool
    capability_name: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    extracted_arguments: HeatToolArguments = Field(default_factory=HeatToolArguments)
    missing_fields: list[str] = Field(default_factory=list)
    reason: str
    candidate_capabilities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_match_consistency(self):
        if not self.matched and self.capability_name is not None:
            raise ValueError("capability_name must be empty when matched is false.")
        return self


class CapabilitySpec(BaseModel):
    name: str
    business_object: str
    description: str
    applicable_when: list[str]
    not_applicable_when: list[str]
    required_argument_groups: list[list[str]]
    optional_arguments: list[str]
    argument_schema: dict[str, Any]
    result_schema: dict[str, Any]
    examples: list[str]
    confusing_with: list[str]
    version: str
    status: CapabilityStatus
    blocked_reason: str | None = None


class AgentResult(BaseModel):
    route: RouteName
    matched: bool
    capability_name: str | None = None
    capability_status: CapabilityStatus | None = None
    confidence: float | None = None
    extracted_arguments: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    matcher_reason: str | None = None
    tool_result: dict[str, Any] | None = None
    final_message: str
    agent_version: str
    prompt_version: str
    tool_version: str
    error_code: str | None = None
    error_message: str | None = None
