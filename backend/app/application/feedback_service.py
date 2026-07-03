import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.feedback.enums import (
    FeedbackReasonType,
    FeedbackType,
    feedback_reason_type_label,
    feedback_type_label,
)
from app.domain.feedback.exceptions import (
    FeedbackPersistenceError,
    FeedbackTargetNotAssistantError,
    FeedbackTargetNotFoundError,
    FeedbackValidationError,
)
from app.domain.identity.context import IdentityContext
from app.infrastructure.database.models.feedback import AgentFeedback
from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository
from app.infrastructure.database.repositories.message_repository import (
    MESSAGE_STATUS_NORMAL,
    ROLE_ASSISTANT,
    MessageRepository,
)
from app.infrastructure.database.session import session_scope


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedbackCommand:
    response_message_key: str
    feedback_type: int
    reason_type: int | None = None
    comment: str | None = None


@dataclass(frozen=True)
class FeedbackResult:
    feedback_key: str
    response_message_key: str
    feedback_type: int
    feedback_type_label: str
    reason_type: int | None
    reason_type_label: str | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class FeedbackApplicationService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def submit_feedback(
        self,
        identity: IdentityContext,
        command: FeedbackCommand,
    ) -> FeedbackResult:
        visitor_id = identity.require_anonymous_visitor()
        feedback_type = self._feedback_type(command.feedback_type)
        reason_type = self._reason_type(command.reason_type)
        comment = self._normalize_comment(command.comment)
        if feedback_type == FeedbackType.LIKE:
            reason_type = None
            comment = None

        logger.info(
            "Feedback submit started response_message_key=%s visitor_digest=%s feedback_type=%s",
            command.response_message_key,
            self._visitor_digest(visitor_id),
            int(feedback_type),
        )

        try:
            with session_scope(self._session_factory) as session:
                messages = MessageRepository(session)
                feedbacks = FeedbackRepository(session)

                message = messages.get_by_message_key(command.response_message_key)
                if message is None:
                    raise FeedbackTargetNotFoundError("Feedback target message not found.")
                if message.role != ROLE_ASSISTANT:
                    raise FeedbackTargetNotAssistantError(
                        "Feedback target must be an assistant message."
                    )
                if message.message_status != MESSAGE_STATUS_NORMAL:
                    raise FeedbackValidationError("Feedback target message is not available.")

                existing_feedback = feedbacks.get_active_by_message_and_visitor(
                    message_id=message.id,
                    visitor_id=visitor_id,
                )
                action = "update" if existing_feedback is not None else "create"
                now = self._utc_now()
                if existing_feedback is None:
                    feedback = feedbacks.create(
                        feedback_key=self._new_key(),
                        conversation_id=message.conversation_id,
                        message_id=message.id,
                        user_id=None,
                        visitor_id=visitor_id,
                        feedback_type=int(feedback_type),
                        reason_type=reason_type,
                        comment=comment,
                        now=now,
                    )
                else:
                    feedback = feedbacks.update(
                        feedback=existing_feedback,
                        feedback_type=int(feedback_type),
                        reason_type=reason_type,
                        comment=comment,
                        now=now,
                    )

                result = self._to_result(feedback, command.response_message_key)
            logger.info(
                "Feedback submit commit success action=%s response_message_key=%s feedback_key=%s visitor_digest=%s",
                action,
                command.response_message_key,
                result.feedback_key,
                self._visitor_digest(visitor_id),
            )
            return result
        except (
            FeedbackTargetNotFoundError,
            FeedbackTargetNotAssistantError,
            FeedbackValidationError,
        ):
            raise
        except SQLAlchemyError as exc:
            logger.error(
                "Feedback submit failed stage=persistence response_message_key=%s exception_type=%s",
                command.response_message_key,
                type(exc).__name__,
            )
            raise FeedbackPersistenceError("Failed to save feedback.") from exc

    def _feedback_type(self, value: int) -> FeedbackType:
        try:
            return FeedbackType(value)
        except ValueError as exc:
            raise FeedbackValidationError("Unsupported feedback_type.") from exc

    def _reason_type(self, value: int | None) -> int | None:
        if value is None:
            return None
        try:
            return int(FeedbackReasonType(value))
        except ValueError as exc:
            raise FeedbackValidationError("Unsupported reason_type.") from exc

    def _normalize_comment(self, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > 1000:
            raise FeedbackValidationError("comment is too long.")
        return stripped

    def _to_result(
        self,
        feedback: AgentFeedback,
        response_message_key: str,
    ) -> FeedbackResult:
        return FeedbackResult(
            feedback_key=feedback.feedback_key,
            response_message_key=response_message_key,
            feedback_type=feedback.feedback_type,
            feedback_type_label=feedback_type_label(feedback.feedback_type),
            reason_type=feedback.reason_type,
            reason_type_label=feedback_reason_type_label(feedback.reason_type),
            comment=feedback.comment,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )

    def _new_key(self) -> str:
        return uuid.uuid4().hex

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)

    def _visitor_digest(self, visitor_id: str) -> str:
        return hashlib.sha256(visitor_id.encode("utf-8")).hexdigest()[:12]
