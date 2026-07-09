from typing import cast

from app.agent.catalog.heat_treatment import CAPABILITY_BY_NAME
from app.agent.exceptions import ToolExecutionError
from app.agent.models import CapabilitySpec
from app.agent.tools.heat_treatment import build_langchain_tools
from app.agent.tools.repository.heat_treatment_repository import HeatTreatmentRepository
from app.core.type_defs import JsonObject


class ToolRegistry:
    def __init__(self, heat_treatment_repository: HeatTreatmentRepository | None = None):
        self._tools = build_langchain_tools(heat_treatment_repository)
        self._last_trace: JsonObject | None = None

    def get_capability(self, name: str) -> CapabilitySpec | None:
        return CAPABILITY_BY_NAME.get(name)

    def execute(self, name: str, arguments: JsonObject) -> JsonObject:
        capability = self.get_capability(name)
        if capability is None:
            raise ToolExecutionError(f"Unknown capability: {name}.")
        if capability.status != "enabled":
            raise ToolExecutionError(f"Capability is not executable: {name}.")
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"Tool is not registered: {name}.")
        raw_result = cast(JsonObject, tool.invoke(arguments))
        self._last_trace = _extract_trace(raw_result)
        return _without_trace(raw_result)

    def last_trace(self) -> JsonObject | None:
        return self._last_trace

    def argument_schema(self, name: str):
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"Tool is not registered: {name}.")
        return tool.args_schema


DEFAULT_TOOL_REGISTRY = ToolRegistry()


def _extract_trace(result: JsonObject) -> JsonObject | None:
    trace = result.get("_trace")
    return cast(JsonObject, trace) if isinstance(trace, dict) else None


def _without_trace(result: JsonObject) -> JsonObject:
    if "_trace" not in result:
        return result
    return {key: value for key, value in result.items() if key != "_trace"}
