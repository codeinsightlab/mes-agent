from app.agent.context.state import AgentState
from app.core.type_defs import JsonObject


def result_builder_node(state: AgentState) -> AgentState:
    final_message = _final_message(state)
    final_result: JsonObject = {
        "route": state.get("route", "error"),
        "matched": bool(state.get("matched", False)),
        "capability_name": state.get("capability_name"),
        "capability_status": state.get("capability_status"),
        "confidence": state.get("confidence"),
        "extracted_arguments": state.get("extracted_arguments") or {},
        "missing_fields": state.get("missing_fields") or [],
        "matcher_reason": state.get("matcher_reason"),
        "tool_result": state.get("tool_result"),
        "final_message": final_message,
        "agent_version": state["agent_version"],
        "prompt_version": state["prompt_version"],
        "tool_version": state["tool_version"],
        "error_code": state.get("error_code"),
        "error_message": state.get("error_message"),
    }
    return {**state, "final_result": final_result}


def _final_message(state: AgentState) -> str:
    route = state.get("route")
    capability_name = state.get("capability_name")
    tool_result = _tool_result_object(state)
    if route == "tool":
        return f"已执行 {capability_name}。"
    if route == "blocked":
        reason = tool_result.get("reason")
        return reason if isinstance(reason, str) else "该能力当前被阻断，无法执行。"
    if route == "clarification":
        question = tool_result.get("question")
        return question if isinstance(question, str) else "需要补充参数后才能执行。"
    if route == "text_to_sql":
        if tool_result.get("status") == "success":
            return "已完成热处理 Text-to-SQL 只读查询。"
        message = tool_result.get("message")
        if isinstance(message, str):
            return message
        error = tool_result.get("error")
        if isinstance(error, dict):
            error_message = error.get("message")
            if isinstance(error_message, str):
                return error_message
        return "热处理 Text-to-SQL 查询未完成。"
    return state.get("error_message") or "Agent 执行失败。"


def _tool_result_object(state: AgentState) -> JsonObject:
    tool_result = state.get("tool_result")
    return tool_result if isinstance(tool_result, dict) else {}
