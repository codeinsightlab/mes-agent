from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRunContext(BaseModel):
    conversation_key: str | None = None
    visitor_id: str | None = None


class AgentRequest(BaseModel):
    message: str
    context: AgentRunContext | None = None


class AgentResponse(BaseModel):
    request_id: str
    agent: str
    status: Literal["success", "clarification_required", "error"]
    capability: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    clarification: str | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
