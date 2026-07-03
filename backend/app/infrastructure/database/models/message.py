from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class AgentMessage(Base):
    __tablename__ = "agent_message"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    message_key: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_conversation.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    parent_message_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_message.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=True,
    )
    role: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    content: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    content_type: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=1)
    sequence_no: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)
    message_status: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
