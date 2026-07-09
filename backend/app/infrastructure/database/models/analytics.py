from datetime import datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.mysql import BIGINT, DATETIME, INTEGER, LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import Base


class AgentTrace(Base):
    __tablename__ = "agent_trace"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    final_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    loop_depth: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)


class AgentEvent(Base):
    __tablename__ = "agent_event"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    step_id: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(INTEGER(unsigned=True), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)


class AgentFailure(Base):
    __tablename__ = "agent_failure"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_layer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    detail_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)


class AgentMetricsSnapshot(Base):
    __tablename__ = "agent_metrics_snapshot"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    total_requests: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False, default=0)
    success_rate: Mapped[float] = mapped_column(nullable=False, default=0)
    tool_hit_rate: Mapped[float] = mapped_column(nullable=False)
    sql_success_rate: Mapped[float] = mapped_column(nullable=False)
    replan_rate: Mapped[float] = mapped_column(nullable=False)
    avg_loop_depth: Mapped[float] = mapped_column(nullable=False)
    execution_error_rate: Mapped[float] = mapped_column(nullable=False, default=0)
    window_start: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=3), nullable=False)
