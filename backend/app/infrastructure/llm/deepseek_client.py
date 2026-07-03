import logging
import time
from typing import Any

import httpx

from app.domain.llm.exceptions import (
    LlmAuthenticationError,
    LlmCallError,
    LlmResponseFormatError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from app.domain.llm.models import ChatRequest, ChatResponse, TokenUsage


logger = logging.getLogger(__name__)


class DeepSeekLlmClient:
    provider = "deepseek"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout_seconds: float,
        http_client: httpx.Client | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._http_client = http_client or httpx.Client(timeout=timeout_seconds)
        self._owns_http_client = http_client is None

    def close(self):
        if self._owns_http_client:
            self._http_client.close()

    def chat(self, request: ChatRequest) -> ChatResponse:
        started_at = time.perf_counter()
        payload = self._build_payload(request)

        try:
            response = self._http_client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            self._raise_for_status(response)
            data = response.json()
            chat_response = self._parse_response(data)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "LLM chat completed provider=%s model=%s elapsed_ms=%s total_tokens=%s",
                self.provider,
                chat_response.model,
                elapsed_ms,
                chat_response.usage.total_tokens if chat_response.usage else None,
            )
            return chat_response
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError("LLM provider request timed out.") from exc
        except httpx.HTTPError as exc:
            raise LlmCallError("LLM provider request failed.") from exc
        except ValueError as exc:
            raise LlmResponseFormatError("LLM provider returned invalid JSON.") from exc

    def _build_payload(self, request: ChatRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def _raise_for_status(self, response: httpx.Response):
        if response.status_code in (401, 403):
            raise LlmAuthenticationError("LLM provider authentication failed.")
        if response.status_code in (408, 504):
            raise LlmTimeoutError("LLM provider request timed out.")
        if response.status_code in (429, 500, 502, 503):
            raise LlmUnavailableError("LLM provider is temporarily unavailable.")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LlmCallError("LLM provider returned an error status.") from exc

    def _parse_response(self, data: Any) -> ChatResponse:
        if not isinstance(data, dict):
            raise LlmResponseFormatError("LLM provider response must be an object.")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmResponseFormatError("LLM provider response has no choices.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LlmResponseFormatError("LLM provider choice must be an object.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise LlmResponseFormatError("LLM provider choice has no message.")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmResponseFormatError("LLM provider response content is empty.")

        model = data.get("model")
        if not isinstance(model, str) or not model.strip():
            model = self._default_model

        return ChatResponse(
            content=content,
            model=model,
            provider=self.provider,
            finish_reason=first_choice.get("finish_reason"),
            usage=self._parse_usage(data.get("usage")),
        )

    def _parse_usage(self, usage: Any) -> TokenUsage | None:
        if usage is None:
            return None
        if not isinstance(usage, dict):
            raise LlmResponseFormatError("LLM provider usage must be an object.")

        return TokenUsage(
            prompt_tokens=self._optional_int(usage.get("prompt_tokens")),
            completion_tokens=self._optional_int(usage.get("completion_tokens")),
            total_tokens=self._optional_int(usage.get("total_tokens")),
        )

    def _optional_int(self, value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        raise LlmResponseFormatError("LLM provider usage token values must be integers.")
