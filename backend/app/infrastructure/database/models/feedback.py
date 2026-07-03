from datetime import datetime

from sqlalchemy import Computed, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class AgentFeedback(Base):
    __tablename__ = "agent_feedback"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    feedback_key: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_conversation.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    message_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_message.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visitor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deleted: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=0)
    feedback_owner_key: Mapped[str | None] = mapped_column(
        String(140),
        Computed(
            "CASE "
            "WHEN `user_id` IS NOT NULL THEN CONCAT('user:', `user_id`) "
            "WHEN `visitor_id` IS NOT NULL THEN CONCAT('visitor:', `visitor_id`) "
            "ELSE 'anonymous' END",
            persisted=True,
        ),
        nullable=True,
    )
    active_feedback_owner_key: Mapped[str | None] = mapped_column(
        String(140),
        Computed(
            "CASE WHEN `deleted` = 0 THEN `feedback_owner_key` ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )
    feedback_type: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    reason_type: Mapped[int | None] = mapped_column(TINYINT(unsigned=True), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
