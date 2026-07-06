from typing import Literal, NotRequired, Required, TypedDict

from app.core.type_defs import JsonObject


RouteName = Literal["tool", "text_to_sql", "blocked", "clarification", "error"]


class AgentState(TypedDict, total=False):
    user_query: Required[str]
    conversation_key: Required[str | None]
    agent_version: Required[str]
    prompt_version: Required[str]
    tool_version: Required[str]
    route: NotRequired[RouteName]
    matched: NotRequired[bool]
    capability_name: NotRequired[str | None]
    capability_status: NotRequired[str | None]
    confidence: NotRequired[float | None]
    extracted_arguments: NotRequired[JsonObject]
    missing_fields: NotRequired[list[str]]
    matcher_reason: NotRequired[str | None]
    candidate_capabilities: NotRequired[list[str]]
    tool_result: NotRequired[JsonObject | None]
    text_to_sql_status: NotRequired[str | None]
    final_result: NotRequired[JsonObject | None]
    error_code: NotRequired[str | None]
    error_message: NotRequired[str | None]
    clarification_question: NotRequired[str | None]
