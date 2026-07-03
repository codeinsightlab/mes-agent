from typing import Any, Literal, TypedDict


RouteName = Literal["tool", "text_to_sql", "blocked", "clarification", "error"]


class AgentState(TypedDict, total=False):
    user_query: str
    conversation_key: str | None
    route: RouteName
    matched: bool
    capability_name: str | None
    capability_status: str | None
    confidence: float | None
    extracted_arguments: dict[str, Any]
    missing_fields: list[str]
    matcher_reason: str | None
    candidate_capabilities: list[str]
    tool_result: dict[str, Any] | None
    text_to_sql_status: str | None
    final_result: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    clarification_question: str | None
    agent_version: str
    prompt_version: str
    tool_version: str
