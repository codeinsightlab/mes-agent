from app.agent.state import AgentState


def text_to_sql_placeholder_node(state: AgentState) -> AgentState:
    return {
        **state,
        "text_to_sql_status": "not_implemented",
        "tool_result": {
            "status": "not_implemented",
            "user_query": state["user_query"],
            "message": "当前问题未匹配已注册 Tool，后续将进入受控 Text-to-SQL 流程。",
        },
    }
