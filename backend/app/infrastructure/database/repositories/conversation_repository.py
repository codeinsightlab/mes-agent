from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.database.models.conversation import AgentConversation


class ConversationRepository:
    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        conversation_key: str,
        now: datetime,
        title: str | None = None,
    ) -> AgentConversation:
        conversation = AgentConversation(
            conversation_key=conversation_key,
            user_id=None,
            visitor_id=None,
            title=title,
            status=1,
            message_count=0,
            last_message_at=None,
            created_at=now,
            updated_at=now,
            deleted=0,
        )
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def update_message_summary(
        self,
        conversation: AgentConversation,
        message_count: int,
        last_message_at: datetime,
        now: datetime,
        status: int | None = None,
    ):
        conversation.message_count = message_count
        conversation.last_message_at = last_message_at
        conversation.updated_at = now
        if status is not None:
            conversation.status = status
        self._session.flush()

    def get_by_id(self, conversation_id: int) -> AgentConversation:
        return self._session.get_one(AgentConversation, conversation_id)
