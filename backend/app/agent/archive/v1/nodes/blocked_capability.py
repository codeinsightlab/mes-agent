from app.agent.capability.catalog.heat_treatment import CAPABILITY_BY_NAME
from app.agent.context.state import AgentState


def blocked_capability_node(state: AgentState) -> AgentState:
    capability_name = state.get("capability_name")
    capability = CAPABILITY_BY_NAME.get(capability_name or "")
    reason = capability.blocked_reason if capability else "Capability is blocked."
    return {
        **state,
        "tool_result": {
            "status": "blocked",
            "capability_name": capability_name,
            "reason": reason,
        },
        "matcher_reason": state.get("matcher_reason") or reason,
    }
