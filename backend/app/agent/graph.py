"""DEPRECATED: eval-only LangGraph route path.

Production Agent execution uses /api/agent/run with AgentOrchestrator.
Capability Catalog V1 should replace this experimental matcher graph or keep it
only as a router evaluation harness.
"""

from collections.abc import Callable
from typing import cast

from langgraph.graph import END, START, StateGraph

from app.agent.nodes.blocked_capability import blocked_capability_node
from app.agent.nodes.clarification import clarification_node
from app.agent.nodes.result_builder import result_builder_node
from app.agent.nodes.tool_executor import make_tool_executor_node
from app.agent.nodes.tool_matcher import MatcherFn, make_tool_matcher_node
from app.agent.state import AgentState
from app.agent.tools.registry import DEFAULT_TOOL_REGISTRY, ToolRegistry

NodeAction = Callable[..., AgentState]


def build_agent_graph(
    matcher: MatcherFn,
    match_threshold: float,
    text_to_sql_node,
    registry: ToolRegistry = DEFAULT_TOOL_REGISTRY,
):
    graph = StateGraph(AgentState)
    graph.add_node("tool_matcher", cast(NodeAction, make_tool_matcher_node(matcher, match_threshold)))
    graph.add_node("tool_executor", cast(NodeAction, make_tool_executor_node(registry)))
    graph.add_node("blocked_capability", cast(NodeAction, blocked_capability_node))
    graph.add_node("clarification", cast(NodeAction, clarification_node))
    graph.add_node("text_to_sql", text_to_sql_node)
    graph.add_node("result_builder", result_builder_node)

    graph.add_edge(START, "tool_matcher")
    graph.add_conditional_edges(
        "tool_matcher",
        _route_decision,
        {
            "tool": "tool_executor",
            "blocked": "blocked_capability",
            "clarification": "clarification",
            "text_to_sql": "text_to_sql",
            "error": "result_builder",
        },
    )
    graph.add_edge("tool_executor", "result_builder")
    graph.add_edge("blocked_capability", "result_builder")
    graph.add_edge("clarification", "result_builder")
    graph.add_edge("text_to_sql", "result_builder")
    graph.add_edge("result_builder", END)
    return graph.compile()


def _route_decision(state: AgentState) -> str:
    return state.get("route") or "error"
