from app.agent.state import AgentState


def result_builder_node(state: AgentState) -> AgentState:
    final_message = _final_message(state)
    final_result = {
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
    tool_result = state.get("tool_result") or {}
    if route == "tool":
        return f"已执行 {capability_name}。"
    if route == "blocked":
        return tool_result.get("reason") or "该能力当前被阻断，无法执行。"
    if route == "clarification":
        return tool_result.get("question") or "需要补充参数后才能执行。"
    if route == "text_to_sql":
        return tool_result.get("message") or "当前进入 Text-to-SQL 占位路径。"
    return state.get("error_message") or "Agent 执行失败。"
