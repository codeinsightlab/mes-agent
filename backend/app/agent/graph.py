from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.agent.nodes.blocked_capability import blocked_capability_node
from app.agent.nodes.clarification import clarification_node
from app.agent.nodes.result_builder import result_builder_node
from app.agent.nodes.text_to_sql_placeholder import text_to_sql_placeholder_node
from app.agent.nodes.tool_executor import make_tool_executor_node
from app.agent.nodes.tool_matcher import MatcherFn, make_tool_matcher_node
from app.agent.state import AgentState
from app.agent.tools.registry import DEFAULT_TOOL_REGISTRY, ToolRegistry


def build_agent_graph(
    matcher: MatcherFn,
    match_threshold: float,
    registry: ToolRegistry = DEFAULT_TOOL_REGISTRY,
):
    graph = StateGraph(AgentState)
    graph.add_node("tool_matcher", make_tool_matcher_node(matcher, match_threshold))
    graph.add_node("tool_executor", make_tool_executor_node(registry))
    graph.add_node("blocked_capability", blocked_capability_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("text_to_sql_placeholder", text_to_sql_placeholder_node)
    graph.add_node("result_builder", result_builder_node)

    graph.add_edge(START, "tool_matcher")
    graph.add_conditional_edges(
        "tool_matcher",
        _route_decision,
        {
            "tool": "tool_executor",
            "blocked": "blocked_capability",
            "clarification": "clarification",
            "text_to_sql": "text_to_sql_placeholder",
            "error": "result_builder",
        },
    )
    graph.add_edge("tool_executor", "result_builder")
    graph.add_edge("blocked_capability", "result_builder")
    graph.add_edge("clarification", "result_builder")
    graph.add_edge("text_to_sql_placeholder", "result_builder")
    graph.add_edge("result_builder", END)
    return graph.compile()


def _route_decision(state: AgentState) -> str:
    return state.get("route") or "error"
