from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER, LONGTEXT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class AgentModelCall(Base):
    __tablename__ = "agent_model_call"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    call_key: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_conversation.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    request_message_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_message.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    response_message_id: Mapped[int | None] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_message.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_prompt_snapshot: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    request_snapshot: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    response_snapshot: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    call_status: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    finish_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
