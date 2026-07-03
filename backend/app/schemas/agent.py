from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message cannot be empty.")
        return stripped


class AgentQueryResponse(BaseModel):
    route: str
    matched: bool
    capability_name: str | None = None
    capability_status: str | None = None
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
