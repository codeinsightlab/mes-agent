import hashlib
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.feedback.enums import feedback_reason_type_label
from app.domain.issue.enums import issue_status_label
from app.domain.issue.exceptions import FeedbackNotFoundError, IssuePersistenceError
from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository
from app.infrastructure.database.session import session_scope


logger = logging.getLogger(__name__)

SUMMARY_LIMIT = 120
SENSITIVE_MARKERS = ("api key", "apikey", "authorization", "bearer", "db_password", "password")


class FeedbackReviewService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def list_disliked_feedbacks(
        self,
        page: int,
        page_size: int,
        reason_type: int | None = None,
        has_issue: bool | None = None,
        issue_status: int | None = None,
        feedback_key: str | None = None,
        response_message_key: str | None = None,
    ):
        logger.info(
            "Disliked feedback list queried page=%s page_size=%s reason_type=%s has_issue=%s issue_status=%s",
            page,
            page_size,
            reason_type,
            has_issue,
            issue_status,
        )
        try:
            with session_scope(self._session_factory) as session:
                rows, total = FeedbackRepository(session).list_disliked_feedbacks(
                    page=page,
                    page_size=page_size,
                    reason_type=reason_type,
                    has_issue=has_issue,
                    issue_status=issue_status,
                    feedback_key=feedback_key,
                    response_message_key=response_message_key,
                )
                return {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "items": [self._summary_from_row(row) for row in rows],
                }
        except SQLAlchemyError as exc:
            logger.error(
                "Disliked feedback list failed exception_type=%s",
                type(exc).__name__,
            )
            raise IssuePersistenceError("Failed to query disliked feedbacks.") from exc

    def get_disliked_feedback_detail(self, feedback_key: str):
        logger.info("Feedback detail queried feedback_key=%s", feedback_key)
        try:
            with session_scope(self._session_factory) as session:
                row = FeedbackRepository(session).get_disliked_feedback_detail(feedback_key)
                if row is None:
                    raise FeedbackNotFoundError("Disliked feedback not found.")
                return self._detail_from_row(row)
        except FeedbackNotFoundError:
            raise
        except SQLAlchemyError as exc:
            logger.error(
                "Feedback detail failed feedback_key=%s exception_type=%s",
                feedback_key,
                type(exc).__name__,
            )
            raise IssuePersistenceError("Failed to query disliked feedback detail.") from exc

    def _summary_from_row(self, row):
        feedback, conversation, assistant, user_message, model_call, issue = row
        return {
            "feedback_key": feedback.feedback_key,
            "response_message_key": assistant.message_key,
            "reason_type": feedback.reason_type,
            "reason_type_label": feedback_reason_type_label(feedback.reason_type),
            "comment": self._summary(feedback.comment),
            "visitor_digest": self._visitor_digest(feedback.visitor_id),
            "assistant_content_summary": self._summary(assistant.content),
            "user_message_content_summary": self._summary(user_message.content if user_message else None),
            "conversation_key": conversation.conversation_key,
            "model": model_call.model if model_call else None,
            "provider": model_call.provider if model_call else None,
            "agent_version": model_call.agent_version if model_call else None,
            "prompt_version": model_call.prompt_version if model_call else None,
            "tool_version": model_call.tool_version if model_call else None,
            "created_at": feedback.created_at,
            "has_issue": issue is not None,
            "issue_key": issue.issue_key if issue else None,
            "issue_status": issue.process_status if issue else None,
            "issue_status_label": issue_status_label(issue.process_status) if issue else None,
        }

    def _detail_from_row(self, row):
        feedback, conversation, assistant, user_message, model_call, issue = row
        return {
            "feedback_key": feedback.feedback_key,
            "feedback_type": feedback.feedback_type,
            "reason_type": feedback.reason_type,
            "reason_type_label": feedback_reason_type_label(feedback.reason_type),
            "comment": feedback.comment,
            "visitor_digest": self._visitor_digest(feedback.visitor_id),
            "created_at": feedback.created_at,
            "updated_at": feedback.updated_at,
            "conversation_key": conversation.conversation_key,
            "user_message": self._message(user_message) if user_message else None,
            "assistant_message": self._message(assistant),
            "model_call": self._model_call(model_call) if model_call else None,
            "has_issue": issue is not None,
            "issue": self._issue(issue, feedback.feedback_key) if issue else None,
        }

    def _message(self, message):
        return {
            "message_key": message.message_key,
            "role": message.role,
            "content": message.content,
            "sequence_no": message.sequence_no,
            "created_at": message.created_at,
        }

    def _model_call(self, model_call):
        return {
            "call_key": model_call.call_key,
            "provider": model_call.provider,
            "model": model_call.model,
            "agent_version": model_call.agent_version,
            "prompt_version": model_call.prompt_version,
            "tool_version": model_call.tool_version,
            "system_prompt_snapshot": self._safe_snapshot(model_call.system_prompt_snapshot),
            "request_snapshot": self._safe_snapshot(model_call.request_snapshot),
            "response_snapshot": self._safe_snapshot(model_call.response_snapshot),
            "prompt_tokens": model_call.prompt_tokens,
            "completion_tokens": model_call.completion_tokens,
            "total_tokens": model_call.total_tokens,
            "duration_ms": model_call.duration_ms,
            "finish_reason": model_call.finish_reason,
            "call_status": model_call.call_status,
            "error_code": model_call.error_code,
            "error_message": model_call.error_message,
            "created_at": model_call.created_at,
        }

    def _issue(self, issue, feedback_key: str):
        from app.domain.issue.enums import (
            issue_priority_label,
            issue_root_cause_type_label,
            issue_status_label,
        )

        return {
            "issue_key": issue.issue_key,
            "feedback_key": feedback_key,
            "process_status": issue.process_status,
            "process_status_label": issue_status_label(issue.process_status),
            "priority": issue.priority,
            "priority_label": issue_priority_label(issue.priority),
            "root_cause_type": issue.root_cause_type,
            "root_cause_type_label": issue_root_cause_type_label(issue.root_cause_type),
            "root_cause": issue.root_cause,
            "solution": issue.solution,
            "processed_by": issue.processed_by,
            "processed_at": issue.processed_at,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
        }

    def _visitor_digest(self, visitor_id: str | None) -> str | None:
        if not visitor_id:
            return None
        return hashlib.sha256(visitor_id.encode("utf-8")).hexdigest()[:12]

    def _summary(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if len(normalized) <= SUMMARY_LIMIT:
            return normalized
        return normalized[:SUMMARY_LIMIT] + "..."

    def _safe_snapshot(self, value: str | None) -> str | None:
        if value is None:
            return None
        lower = value.lower()
        if any(marker in lower for marker in SENSITIVE_MARKERS):
            return None
        return value
