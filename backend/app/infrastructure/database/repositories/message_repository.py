from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database.models.message import AgentMessage


ROLE_USER = 2
ROLE_ASSISTANT = 3
CONTENT_TYPE_TEXT = 1
MESSAGE_STATUS_NORMAL = 1


class MessageRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_message_key(self, message_key: str) -> AgentMessage | None:
        statement = select(AgentMessage).where(AgentMessage.message_key == message_key)
        return self._session.execute(statement).scalar_one_or_none()

    def create_user_message(
        self,
        message_key: str,
        conversation_id: int,
        content: str,
        now: datetime,
    ) -> AgentMessage:
        return self._create_message(
            message_key=message_key,
            conversation_id=conversation_id,
            parent_message_id=None,
            role=ROLE_USER,
            content=content,
            content_type=CONTENT_TYPE_TEXT,
            sequence_no=1,
            message_status=MESSAGE_STATUS_NORMAL,
            now=now,
        )

    def create_assistant_message(
        self,
        message_key: str,
        conversation_id: int,
        parent_message_id: int,
        content: str,
        now: datetime,
    ) -> AgentMessage:
        return self._create_message(
            message_key=message_key,
            conversation_id=conversation_id,
            parent_message_id=parent_message_id,
            role=ROLE_ASSISTANT,
            content=content,
            content_type=CONTENT_TYPE_TEXT,
            sequence_no=2,
            message_status=MESSAGE_STATUS_NORMAL,
            now=now,
        )

    def _create_message(
        self,
        message_key: str,
        conversation_id: int,
        parent_message_id: int | None,
        role: int,
        content: str,
        content_type: int,
        sequence_no: int,
        message_status: int,
        now: datetime,
    ) -> AgentMessage:
        message = AgentMessage(
            message_key=message_key,
            conversation_id=conversation_id,
            parent_message_id=parent_message_id,
            role=role,
            content=content,
            content_type=content_type,
            sequence_no=sequence_no,
            message_status=message_status,
            created_at=now,
            updated_at=now,
        )
        self._session.add(message)
        self._session.flush()
        return message
