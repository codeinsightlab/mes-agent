from collections.abc import Callable
from typing import Any


Executor = Callable[[dict[str, Any]], dict[str, Any]]


class ExecutionEngine:
    """Shared executor dispatch. It knows implementations, not domain agents."""

    def __init__(self, executors: dict[str, Executor]):
        self._executors = executors

    def execute(self, executor_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        executor = self._executors.get(executor_name)
        if executor is None:
            raise RuntimeError(f"Capability executor is not configured: {executor_name}.")
        return executor(arguments)
