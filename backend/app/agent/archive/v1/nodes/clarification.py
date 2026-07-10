from app.agent.context.state import AgentState


def clarification_node(state: AgentState) -> AgentState:
    missing_fields = state.get("missing_fields") or []
    question = "请提供热处理记录编号、record_id 或 object_id 后再查询。"
    if missing_fields and missing_fields != ["record identifier: record_id or record_no or object_id"]:
        question = f"请补充以下信息：{', '.join(missing_fields)}。"
    return {
        **state,
        "clarification_question": question,
        "tool_result": {
            "status": "clarification_required",
            "question": question,
        },
    }
