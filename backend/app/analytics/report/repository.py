from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.report.models import AnalyticsRawData, AnalyticsWindow
from app.domain.persistence.exceptions import PersistenceError


ANALYTICS_TABLES = (
    "agent_trace",
    "agent_event",
    "agent_metrics_snapshot",
    "agent_failure",
)


class SqlAlchemyAnalyticsRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def fetch_window(self, window: AnalyticsWindow) -> AnalyticsRawData:
        try:
            with self._engine.connect() as connection:
                return AnalyticsRawData(
                    traces=_fetch_table(connection, "agent_trace", window.start_at, window.end_at),
                    events=_fetch_table(connection, "agent_event", window.start_at, window.end_at),
                    metrics_snapshots=_fetch_table(
                        connection,
                        "agent_metrics_snapshot",
                        window.start_at,
                        window.end_at,
                    ),
                    failures=_fetch_table(connection, "agent_failure", window.start_at, window.end_at),
                )
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to read analytics tables.") from exc


def _fetch_table(connection, table_name: str, start_at: datetime, end_at: datetime) -> list[dict[str, Any]]:
    if table_name not in ANALYTICS_TABLES:
        raise PersistenceError("Unsupported analytics table.")
    result = connection.execute(
        text(
            f"""
            SELECT *
            FROM {table_name}
            WHERE created_at >= :start_at
              AND created_at < :end_at
            ORDER BY created_at ASC
            """
        ),
        {"start_at": start_at, "end_at": end_at},
    )
    return [dict(row._mapping) for row in result]
