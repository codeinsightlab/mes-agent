from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CapabilityStatus = Literal["enabled", "planned", "experimental", "blocked", "disabled"]
ExecutionType = Literal["tool", "readonly_sql", "action", "reference"]
LegacySource = Literal["old python constant", "none"]


class CapabilitySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("required", "optional")
    @classmethod
    def normalize_fields(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            stripped = value.strip()
            if stripped and stripped not in normalized:
                normalized.append(stripped)
        return normalized


class CapabilityDataSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    name: str
    fields: list[str] = Field(default_factory=list)
    description: str | None = None


class CapabilityDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    domain: str
    description: str
    intent: list[str] = Field(default_factory=list)
    status: CapabilityStatus
    execution_type: ExecutionType
    executor: str
    input_schema: CapabilitySchema
    output_schema: CapabilitySchema
    data_sources: list[CapabilityDataSource] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    legacy_source: LegacySource = "none"

    @field_validator("name", "domain", "description", "executor")
    @classmethod
    def required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must not be empty")
        return stripped

    @model_validator(mode="after")
    def validate_executable_shape(self):
        if self.execution_type == "tool" and not self.executor:
            raise ValueError("tool capability requires executor")
        return self

    @property
    def executable(self) -> bool:
        return self.status == "enabled"
