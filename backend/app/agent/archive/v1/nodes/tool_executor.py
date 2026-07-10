from collections.abc import Callable

from app.agent.execution.tools.exceptions import ToolExecutionError
from app.agent.context.state import AgentState
from app.agent.execution.tools.registry import ToolRegistry


def make_tool_executor_node(registry: ToolRegistry) -> Callable[[AgentState], AgentState]:
    def node(state: AgentState) -> AgentState:
        capability_name = state.get("capability_name")
        if not capability_name:
            return {
                **state,
                "route": "error",
                "error_code": "missing_capability",
                "error_message": "No capability selected for execution.",
            }
        try:
            result = registry.execute(
                capability_name,
                state.get("extracted_arguments") or {},
            )
            return {**state, "tool_result": result}
        except ToolExecutionError as exc:
            return {
                **state,
                "route": "error",
                "error_code": "tool_execution_error",
                "error_message": str(exc),
            }

    return node
