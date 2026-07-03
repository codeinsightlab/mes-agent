from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models.feedback import AgentFeedback


ACTIVE_RECORD = 0


class FeedbackRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_active_by_message_and_visitor(
        self,
        message_id: int,
        visitor_id: str,
    ) -> AgentFeedback | None:
        statement = select(AgentFeedback).where(
            AgentFeedback.message_id == message_id,
            AgentFeedback.visitor_id == visitor_id,
            AgentFeedback.deleted == ACTIVE_RECORD,
        )
        return self._session.execute(statement).scalar_one_or_none()

    def get_active_by_message_and_user(
        self,
        message_id: int,
        user_id: str,
    ) -> AgentFeedback | None:
        statement = select(AgentFeedback).where(
            AgentFeedback.message_id == message_id,
            AgentFeedback.user_id == user_id,
            AgentFeedback.deleted == ACTIVE_RECORD,
        )
        return self._session.execute(statement).scalar_one_or_none()

    def create(
        self,
        feedback_key: str,
        conversation_id: int,
        message_id: int,
        user_id: str | None,
        visitor_id: str | None,
        feedback_type: int,
        reason_type: int | None,
        comment: str | None,
        now: datetime,
    ) -> AgentFeedback:
        feedback = AgentFeedback(
            feedback_key=feedback_key,
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            visitor_id=visitor_id,
            deleted=ACTIVE_RECORD,
            feedback_type=feedback_type,
            reason_type=reason_type,
            comment=comment,
            created_at=now,
            updated_at=now,
        )
        self._session.add(feedback)
        self._session.flush()
        return feedback

    def update(
        self,
        feedback: AgentFeedback,
        feedback_type: int,
        reason_type: int | None,
        comment: str | None,
        now: datetime,
    ) -> AgentFeedback:
        feedback.feedback_type = feedback_type
        feedback.reason_type = reason_type
        feedback.comment = comment
        feedback.updated_at = now
        self._session.flush()
        return feedback

    def get_by_feedback_key(self, feedback_key: str) -> AgentFeedback | None:
        statement = select(AgentFeedback).where(AgentFeedback.feedback_key == feedback_key)
        return self._session.execute(statement).scalar_one_or_none()
