import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.llm.models import ChatRequest, ChatResponse
from app.domain.persistence.exceptions import (
    ConversationInitializationError,
    ModelResultPersistenceError,
)
from app.infrastructure.database.repositories.conversation_repository import (
    ConversationRepository,
)
from app.infrastructure.database.repositories.message_repository import MessageRepository
from app.infrastructure.database.repositories.model_call_repository import (
    CALL_STATUS_FAILED,
    CALL_STATUS_TIMEOUT,
    ModelCallRepository,
)
from app.infrastructure.database.session import session_scope


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatRecordStart:
    conversation_id: int
    conversation_key: str
    user_message_id: int
    user_message_key: str
    call_id: int
    call_key: str


@dataclass(frozen=True)
class ChatRecordSuccess:
    conversation_key: str
    response_message_key: str
    call_key: str


class ChatPersistenceService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def initialize_chat(
        self,
        user_message: str,
        chat_request: ChatRequest,
        provider: str,
        model: str,
        agent_version: str,
        prompt_version: str,
        tool_version: str | None,
    ) -> ChatRecordStart:
        now = self._utc_now()
        conversation_key = self._new_key()
        user_message_key = self._new_key()
        call_key = self._new_key()

        try:
            logger.info(
                "Chat persistence stage=initializing conversation_key=%s call_key=%s",
                conversation_key,
                call_key,
            )
            with session_scope(self._session_factory) as session:
                conversations = ConversationRepository(session)
                messages = MessageRepository(session)
                model_calls = ModelCallRepository(session)

                conversation = conversations.create(
                    conversation_key=conversation_key,
                    now=now,
                    title=self._title_from_message(user_message),
                )
                user_record = messages.create_user_message(
                    message_key=user_message_key,
                    conversation_id=conversation.id,
                    content=user_message,
                    now=now,
                )
                model_call = model_calls.create_calling(
                    call_key=call_key,
                    conversation_id=conversation.id,
                    request_message_id=user_record.id,
                    provider=provider,
                    model=model,
                    agent_version=agent_version,
                    prompt_version=prompt_version,
                    tool_version=tool_version,
                    system_prompt_snapshot=self._system_prompt(chat_request),
                    request_snapshot=self._request_snapshot(chat_request),
                    now=now,
                )
                conversations.update_message_summary(
                    conversation=conversation,
                    message_count=1,
                    last_message_at=now,
                    now=now,
                )
                logger.info(
                    "Chat persistence stage=initialized conversation_key=%s user_message_key=%s call_key=%s committed=true",
                    conversation.conversation_key,
                    user_record.message_key,
                    model_call.call_key,
                )
                return ChatRecordStart(
                    conversation_id=conversation.id,
                    conversation_key=conversation.conversation_key,
                    user_message_id=user_record.id,
                    user_message_key=user_record.message_key,
                    call_id=model_call.id,
                    call_key=model_call.call_key,
                )
        except SQLAlchemyError as exc:
            logger.error(
                "Chat persistence stage=initialize_failed conversation_key=%s call_key=%s exception_type=%s",
                conversation_key,
                call_key,
                type(exc).__name__,
            )
            raise ConversationInitializationError(
                "Failed to initialize chat persistence records."
            ) from exc

    def save_success(
        self,
        start: ChatRecordStart,
        response: ChatResponse,
        duration_ms: int,
    ) -> ChatRecordSuccess:
        now = self._utc_now()
        response_message_key = self._new_key()

        try:
            logger.info(
                "Chat persistence stage=saving_success conversation_key=%s call_key=%s",
                start.conversation_key,
                start.call_key,
            )
            with session_scope(self._session_factory) as session:
                conversations = ConversationRepository(session)
                messages = MessageRepository(session)
                model_calls = ModelCallRepository(session)

                conversation = conversations.get_by_id(start.conversation_id)
                model_call = model_calls.get_by_id(start.call_id)
                assistant_message = messages.create_assistant_message(
                    message_key=response_message_key,
                    conversation_id=start.conversation_id,
                    parent_message_id=start.user_message_id,
                    content=response.content,
                    now=now,
                )
                usage = response.usage
                model_calls.update_success(
                    model_call=model_call,
                    response_message_id=assistant_message.id,
                    response_snapshot=self._response_snapshot(response),
                    prompt_tokens=usage.prompt_tokens if usage else None,
                    completion_tokens=usage.completion_tokens if usage else None,
                    total_tokens=usage.total_tokens if usage else None,
                    duration_ms=duration_ms,
                    finish_reason=response.finish_reason,
                    model=response.model,
                    provider=response.provider,
                    now=now,
                )
                conversations.update_message_summary(
                    conversation=conversation,
                    message_count=2,
                    last_message_at=now,
                    now=now,
                    status=2,
                )
                logger.info(
                    "Chat persistence stage=success_saved conversation_key=%s response_message_key=%s call_key=%s committed=true",
                    start.conversation_key,
                    assistant_message.message_key,
                    start.call_key,
                )
                return ChatRecordSuccess(
                    conversation_key=start.conversation_key,
                    response_message_key=assistant_message.message_key,
                    call_key=start.call_key,
                )
        except SQLAlchemyError as exc:
            logger.exception(
                "Chat persistence stage=save_success_failed conversation_key=%s call_key=%s exception_type=%s",
                start.conversation_key,
                start.call_key,
                type(exc).__name__,
            )
            raise ModelResultPersistenceError(
                "Failed to save model success result."
            ) from exc

    def save_failure(
        self,
        start: ChatRecordStart,
        duration_ms: int,
        error_code: str,
        error_message: str,
        timed_out: bool = False,
    ):
        now = self._utc_now()
        try:
            logger.info(
                "Chat persistence stage=saving_failure conversation_key=%s call_key=%s",
                start.conversation_key,
                start.call_key,
            )
            with session_scope(self._session_factory) as session:
                conversations = ConversationRepository(session)
                model_calls = ModelCallRepository(session)

                conversation = conversations.get_by_id(start.conversation_id)
                model_call = model_calls.get_by_id(start.call_id)
                model_calls.update_failure(
                    model_call=model_call,
                    call_status=CALL_STATUS_TIMEOUT if timed_out else CALL_STATUS_FAILED,
                    duration_ms=duration_ms,
                    error_code=error_code,
                    error_message=self._sanitize_error_message(error_message),
                    now=now,
                )
                conversations.update_message_summary(
                    conversation=conversation,
                    message_count=1,
                    last_message_at=conversation.last_message_at or now,
                    now=now,
                    status=2,
                )
                logger.info(
                    "Chat persistence stage=failure_saved conversation_key=%s call_key=%s committed=true",
                    start.conversation_key,
                    start.call_key,
                )
        except SQLAlchemyError as exc:
            logger.exception(
                "Chat persistence stage=save_failure_failed conversation_key=%s call_key=%s exception_type=%s",
                start.conversation_key,
                start.call_key,
                type(exc).__name__,
            )
            raise ModelResultPersistenceError(
                "Failed to save model failure result."
            ) from exc

    def _request_snapshot(self, request: ChatRequest) -> str:
        return self._to_json(
            {
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in request.messages
                ],
                "model": request.model,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
        )

    def _response_snapshot(self, response: ChatResponse) -> str:
        usage = response.usage
        return self._to_json(
            {
                "content": response.content,
                "provider": response.provider,
                "model": response.model,
                "finish_reason": response.finish_reason,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else None,
                    "completion_tokens": usage.completion_tokens if usage else None,
                    "total_tokens": usage.total_tokens if usage else None,
                }
                if usage
                else None,
            }
        )

    def _system_prompt(self, request: ChatRequest) -> str | None:
        for message in request.messages:
            if message.role == "system":
                return message.content
        return None

    def _to_json(self, value) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _sanitize_error_message(self, message: str) -> str:
        sanitized = message.replace("Authorization", "[redacted-header]")
        sanitized = sanitized.replace("Bearer", "[redacted-auth-scheme]")
        return sanitized[:1000]

    def _title_from_message(self, message: str) -> str:
        return message.strip().replace("\n", " ")[:80]

    def _new_key(self) -> str:
        return uuid.uuid4().hex

    def _utc_now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)
