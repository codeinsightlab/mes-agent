import time
import logging

from app.application.chat_persistence_service import ChatPersistenceService
from app.application.chat_result import ChatUseCaseResult
from app.domain.llm.client import LlmClient
from app.domain.llm.exceptions import (
    LlmAuthenticationError,
    LlmCallError,
    LlmConfigurationError,
    LlmResponseFormatError,
    LlmTimeoutError,
    LlmUnavailableError,
)
from app.domain.llm.models import ChatRequest, LlmMessage


logger = logging.getLogger(__name__)


class ChatApplicationService:
    def __init__(
        self,
        llm_client: LlmClient,
        persistence_service: ChatPersistenceService,
        provider: str,
        model: str,
        agent_version: str,
        prompt_version: str,
        tool_version: str | None,
    ):
        self._llm_client = llm_client
        self._persistence_service = persistence_service
        self._provider = provider
        self._model = model
        self._agent_version = agent_version
        self._prompt_version = prompt_version
        self._tool_version = tool_version

    def close(self):
        close = getattr(self._llm_client, "close", None)
        if callable(close):
            close()

    def chat(self, message: str) -> ChatUseCaseResult:
        if not message or not message.strip():
            raise ValueError("Message cannot be empty.")

        message = message.strip()
        request = ChatRequest(
            messages=[
                LlmMessage(
                    role="system",
                    content="You are a concise assistant for a MES Agent research project.",
                ),
                LlmMessage(role="user", content=message),
            ]
        )
        start = self._persistence_service.initialize_chat(
            user_message=message,
            chat_request=request,
            provider=self._provider,
            model=request.model or self._model,
            agent_version=self._agent_version,
            prompt_version=self._prompt_version,
            tool_version=self._tool_version,
        )

        started_at = time.perf_counter()
        try:
            response = self._llm_client.chat(request)
        except (
            LlmAuthenticationError,
            LlmCallError,
            LlmConfigurationError,
            LlmResponseFormatError,
            LlmTimeoutError,
            LlmUnavailableError,
        ) as exc:
            duration_ms = self._duration_ms(started_at)
            logger.info(
                "Chat model call result=failed call_key=%s duration_ms=%s error_code=%s",
                start.call_key,
                duration_ms,
                self._error_code(exc),
            )
            self._persistence_service.save_failure(
                start=start,
                duration_ms=duration_ms,
                error_code=self._error_code(exc),
                error_message=str(exc),
                timed_out=isinstance(exc, LlmTimeoutError),
            )
            raise

        duration_ms = self._duration_ms(started_at)
        logger.info(
            "Chat model call result=success call_key=%s duration_ms=%s",
            start.call_key,
            duration_ms,
        )
        saved = self._persistence_service.save_success(
            start=start,
            response=response,
            duration_ms=duration_ms,
        )
        return ChatUseCaseResult(
            response=response,
            conversation_key=saved.conversation_key,
            response_message_key=saved.response_message_key,
            call_key=saved.call_key,
        )

    def _duration_ms(self, started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))

    def _error_code(self, exc: Exception) -> str:
        if isinstance(exc, LlmConfigurationError):
            return "llm_configuration_error"
        if isinstance(exc, LlmAuthenticationError):
            return "llm_authentication_error"
        if isinstance(exc, LlmTimeoutError):
            return "llm_timeout"
        if isinstance(exc, LlmUnavailableError):
            return "llm_unavailable"
        if isinstance(exc, LlmResponseFormatError):
            return "llm_response_format_error"
        return "llm_call_error"
