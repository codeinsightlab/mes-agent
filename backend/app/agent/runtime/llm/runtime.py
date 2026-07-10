from typing import Any, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class LlmRuntime:
    """Shared model boundary for prompt invocation and structured validation."""

    def __init__(self, model: Any | None = None):
        self._model = model

    def structured(self, prompt: str, output_type: type[T]) -> T:
        if self._model is None:
            raise RuntimeError("LLM Runtime is not configured.")
        return output_type.model_validate(self._model.invoke(prompt))
