from app.agent.catalog.heat_treatment import CAPABILITY_BY_NAME
from app.agent.exceptions import ToolExecutionError
from app.agent.tools.heat_treatment import build_langchain_tools


class ToolRegistry:
    def __init__(self):
        self._tools = build_langchain_tools()

    def get_capability(self, name: str):
        return CAPABILITY_BY_NAME.get(name)

    def execute(self, name: str, arguments: dict) -> dict:
        capability = self.get_capability(name)
        if capability is None:
            raise ToolExecutionError(f"Unknown capability: {name}.")
        if capability.status != "enabled":
            raise ToolExecutionError(f"Capability is not executable: {name}.")
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"Tool is not registered: {name}.")
        return tool.invoke(arguments)

    def argument_schema(self, name: str):
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"Tool is not registered: {name}.")
        return tool.args_schema


DEFAULT_TOOL_REGISTRY = ToolRegistry()
