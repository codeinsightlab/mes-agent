from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class AgentIssue(Base):
    __tablename__ = "agent_issue"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    issue_key: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("agent_feedback.id", ondelete="RESTRICT", onupdate="RESTRICT"),
        nullable=False,
    )
    process_status: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=1)
    priority: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False, default=2)
    root_cause_type: Mapped[int | None] = mapped_column(TINYINT(unsigned=True), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
