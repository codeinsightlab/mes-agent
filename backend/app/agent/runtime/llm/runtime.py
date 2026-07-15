import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class LlmStructuredOutputError(ValueError):
    def __init__(self, message: str, raw_output: str | dict[str, Any]):
        super().__init__(message)
        self.raw_output = raw_output


class LlmRuntime:
    """Shared model boundary for prompt invocation and structured validation."""

    def __init__(self, model: Any | None = None):
        self._model = model

    def structured(self, prompt: str, output_type: type[T]) -> T:
        if self._model is None:
            raise RuntimeError("LLM Runtime is not configured.")
        if hasattr(self._model, "with_structured_output"):
            try:
                structured_model = self._model.with_structured_output(output_type)
                result = structured_model.invoke(prompt)
            except Exception:
                result = self._model.invoke(
                    prompt + "\n\n只返回 JSON 对象，不要使用 Markdown 代码块。"
                )
        else:
            result = self._model.invoke(prompt)
        if isinstance(result, output_type):
            return result
        if isinstance(result, dict):
            return _validate(output_type, result, result)
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return _validate_json_content(output_type, content)
        if isinstance(result, BaseModel):
            payload = result.model_dump(mode="json")
            return _validate(output_type, payload, payload)
        if isinstance(result, str):
            return _validate_json_content(output_type, result)
        raise ValueError("LLM structured response must be an object or JSON string.")


def _validate_json_content(output_type: type[T], content: str) -> T:
    try:
        payload = _extract_json_object(content)
    except Exception as exc:
        raise LlmStructuredOutputError(str(exc), content) from exc
    return _validate(output_type, payload, payload)


def _validate(
    output_type: type[T],
    payload: object,
    raw_output: str | dict[str, Any],
) -> T:
    try:
        return output_type.model_validate(payload)
    except Exception as exc:
        raise LlmStructuredOutputError(str(exc), raw_output) from exc


def _extract_json_object(content: str) -> dict[str, Any]:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM response did not contain a JSON object.")
    decoded = json.loads(cleaned[start : end + 1])
    if not isinstance(decoded, dict):
        raise ValueError("LLM response JSON must be an object.")
    return decoded
