from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.infrastructure.database.models.conversation import AgentConversation
from app.infrastructure.database.models.feedback import AgentFeedback
from app.infrastructure.database.models.issue import AgentIssue
from app.infrastructure.database.models.message import AgentMessage
from app.infrastructure.database.models.model_call import AgentModelCall


ACTIVE_RECORD = 0
FEEDBACK_TYPE_DISLIKE = 2


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

    def list_disliked_feedbacks(
        self,
        page: int,
        page_size: int,
        reason_type: int | None = None,
        has_issue: bool | None = None,
        issue_status: int | None = None,
        feedback_key: str | None = None,
        response_message_key: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ):
        user_message = aliased(AgentMessage)
        assistant_message = aliased(AgentMessage)
        statement = (
            select(
                AgentFeedback,
                AgentConversation,
                assistant_message,
                user_message,
                AgentModelCall,
                AgentIssue,
            )
            .join(AgentConversation, AgentConversation.id == AgentFeedback.conversation_id)
            .join(assistant_message, assistant_message.id == AgentFeedback.message_id)
            .outerjoin(
                user_message,
                user_message.id == assistant_message.parent_message_id,
            )
            .outerjoin(
                AgentModelCall,
                AgentModelCall.response_message_id == assistant_message.id,
            )
            .outerjoin(AgentIssue, AgentIssue.feedback_id == AgentFeedback.id)
        )
        statement = self._apply_disliked_filters(
            statement,
            assistant_message=assistant_message,
            reason_type=reason_type,
            has_issue=has_issue,
            issue_status=issue_status,
            feedback_key=feedback_key,
            response_message_key=response_message_key,
            created_from=created_from,
            created_to=created_to,
        )
        total = self._session.execute(
            select(func.count()).select_from(statement.subquery())
        ).scalar_one()
        rows = self._session.execute(
            statement.order_by(AgentFeedback.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return rows, total

    def get_disliked_feedback_detail(self, feedback_key: str):
        user_message = aliased(AgentMessage)
        assistant_message = aliased(AgentMessage)
        statement = (
            select(
                AgentFeedback,
                AgentConversation,
                assistant_message,
                user_message,
                AgentModelCall,
                AgentIssue,
            )
            .join(AgentConversation, AgentConversation.id == AgentFeedback.conversation_id)
            .join(assistant_message, assistant_message.id == AgentFeedback.message_id)
            .outerjoin(user_message, user_message.id == assistant_message.parent_message_id)
            .outerjoin(AgentModelCall, AgentModelCall.response_message_id == assistant_message.id)
            .outerjoin(AgentIssue, AgentIssue.feedback_id == AgentFeedback.id)
            .where(
                AgentFeedback.feedback_key == feedback_key,
                AgentFeedback.feedback_type == FEEDBACK_TYPE_DISLIKE,
                AgentFeedback.deleted == ACTIVE_RECORD,
            )
        )
        return self._session.execute(statement).one_or_none()

    def _apply_disliked_filters(self, statement, assistant_message, **filters):
        statement = statement.where(
            AgentFeedback.feedback_type == FEEDBACK_TYPE_DISLIKE,
            AgentFeedback.deleted == ACTIVE_RECORD,
        )
        if filters["reason_type"] is not None:
            statement = statement.where(AgentFeedback.reason_type == filters["reason_type"])
        if filters["has_issue"] is True:
            statement = statement.where(AgentIssue.id.is_not(None))
        if filters["has_issue"] is False:
            statement = statement.where(AgentIssue.id.is_(None))
        if filters["issue_status"] is not None:
            statement = statement.where(AgentIssue.process_status == filters["issue_status"])
        if filters["feedback_key"]:
            statement = statement.where(AgentFeedback.feedback_key == filters["feedback_key"])
        if filters["response_message_key"]:
            statement = statement.where(assistant_message.message_key == filters["response_message_key"])
        if filters["created_from"] is not None:
            statement = statement.where(AgentFeedback.created_at >= filters["created_from"])
        if filters["created_to"] is not None:
            statement = statement.where(AgentFeedback.created_at <= filters["created_to"])
        return statement
