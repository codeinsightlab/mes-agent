from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class AgentConversation(Base):
    __tablename__ = "agent_conversation"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    conversation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visitor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=1)
    message_count: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(
        DATETIME(fsp=3), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    deleted: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=0)
