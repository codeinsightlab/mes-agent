from typing import Any

from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.execution import ExecutionEngine


class CapabilityRuntime:
    """Shared catalog validation and execution boundary used by every domain agent."""

    def __init__(self, registry: CapabilityRuntimeRegistry, execution_engine: ExecutionEngine):
        self._registry = registry
        self._execution_engine = execution_engine

    @property
    def registry(self) -> CapabilityRuntimeRegistry:
        return self._registry

    def execute(self, capability_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        capability = self._registry.require_executable(capability_name)
        return self._execution_engine.execute(capability.executor, arguments)
