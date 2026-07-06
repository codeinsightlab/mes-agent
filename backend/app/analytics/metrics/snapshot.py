from datetime import UTC, datetime, timedelta
import logging
import threading
from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.domain.persistence.exceptions import PersistenceError


logger = logging.getLogger(__name__)


class MetricsSnapshotPayload(TypedDict):
    tool_hit_rate: float
    sql_success_rate: float
    replan_rate: float
    avg_loop_depth: float
    window_start: datetime
    window_end: datetime
    created_at: datetime


class MetricsSnapshotService:
    def __init__(self, engine: Engine):
        self._engine = engine

    def create_snapshot(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> MetricsSnapshotPayload:
        try:
            with self._engine.begin() as connection:
                metrics = connection.execute(
                    text(
                        """
                        SELECT
                          COALESCE(1.0 * SUM(CASE WHEN event_type='TOOL_EXECUTE_SUCCESS' THEN 1 ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN event_type IN ('TOOL_EXECUTE_SUCCESS', 'TOOL_EXECUTE_FAIL') THEN 1 ELSE 0 END), 0), 0) AS tool_hit_rate,
                          COALESCE(1.0 * SUM(CASE WHEN event_type='SQL_EXECUTE_SUCCESS' THEN 1 ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN event_type IN ('SQL_EXECUTE_SUCCESS', 'SQL_EXECUTE_FAIL') THEN 1 ELSE 0 END), 0), 0) AS sql_success_rate,
                          COALESCE(1.0 * COUNT(DISTINCT CASE WHEN event_type='REPLAN_TRIGGER' THEN trace_id END)
                            / NULLIF(COUNT(DISTINCT trace_id), 0), 0) AS replan_rate
                        FROM agent_event
                        WHERE timestamp >= :window_start
                          AND timestamp < :window_end
                        """
                    ),
                    {"window_start": window_start, "window_end": window_end},
                ).mappings().one()
                avg_loop_depth = connection.execute(
                    text(
                        """
                        SELECT COALESCE(AVG(loop_depth), 0) AS avg_loop_depth
                        FROM agent_trace
                        WHERE created_at >= :window_start
                          AND created_at < :window_end
                        """
                    ),
                    {"window_start": window_start, "window_end": window_end},
                ).scalar_one()
                now = datetime.now(UTC).replace(tzinfo=None)
                payload: MetricsSnapshotPayload = {
                    "tool_hit_rate": round(float(metrics["tool_hit_rate"] or 0), 4),
                    "sql_success_rate": round(float(metrics["sql_success_rate"] or 0), 4),
                    "replan_rate": round(float(metrics["replan_rate"] or 0), 4),
                    "avg_loop_depth": round(float(avg_loop_depth or 0), 4),
                    "window_start": window_start,
                    "window_end": window_end,
                    "created_at": now,
                }
                connection.execute(
                    text(
                        """
                        INSERT INTO agent_metrics_snapshot (
                            tool_hit_rate,
                            sql_success_rate,
                            replan_rate,
                            avg_loop_depth,
                            window_start,
                            window_end,
                            created_at
                        )
                        VALUES (
                            :tool_hit_rate,
                            :sql_success_rate,
                            :replan_rate,
                            :avg_loop_depth,
                            :window_start,
                            :window_end,
                            :created_at
                        )
                        """
                    ),
                    payload,
                )
                return payload
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to create metrics snapshot.") from exc

    def create_recent_snapshot(self, minutes: int = 10) -> MetricsSnapshotPayload:
        if minutes not in {10, 30, 60}:
            raise ValueError("Metrics snapshot window must be 10, 30, or 60 minutes.")
        window_end = datetime.now(UTC).replace(tzinfo=None)
        return self.create_snapshot(
            window_start=window_end - timedelta(minutes=minutes),
            window_end=window_end,
        )


class MetricsSnapshotScheduler:
    def __init__(self, service: MetricsSnapshotService, interval_minutes: int = 30):
        if interval_minutes not in {10, 30, 60}:
            raise ValueError("Metrics snapshot interval must be 10, 30, or 60 minutes.")
        self._service = service
        self._interval_minutes = interval_minutes
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="analytics-metrics-snapshot-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval_minutes * 60):
            try:
                self._service.create_recent_snapshot(self._interval_minutes)
            except Exception as exc:
                logger.error(
                    "Analytics metrics snapshot scheduler failed exception_type=%s",
                    type(exc).__name__,
                )
