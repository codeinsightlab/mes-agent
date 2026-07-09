from datetime import datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from app.analytics.report.models import (
    AnalyticsEventRecord,
    AnalyticsFailureRecord,
    AnalyticsReportData,
    AnalyticsTraceRecord,
    AnalyticsWindow,
    CountGroup,
    MetricValue,
    ReportMetrics,
)
from app.core.type_defs import JsonObject
from app.domain.persistence.exceptions import PersistenceError


class SqlAlchemyAnalyticsRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def fetch_report_data(self, window: AnalyticsWindow) -> AnalyticsReportData:
        try:
            with self._engine.connect() as connection:
                metrics = _query_metrics(connection, window.start_at, window.end_at)
                top_failure_types = _query_top_failure_types(
                    connection,
                    window.start_at,
                    window.end_at,
                )
                top_sql_errors = _query_top_sql_errors(connection, window.start_at, window.end_at)
                tool_usage = _query_tool_usage(connection, window.start_at, window.end_at)
                tool_miss_analysis = _query_failure_group(
                    connection,
                    window.start_at,
                    window.end_at,
                    "tool_miss",
                )
                schema_gaps = _query_failure_group(
                    connection,
                    window.start_at,
                    window.end_at,
                    "schema_gap",
                )
                execution_failures = _query_failure_group(
                    connection,
                    window.start_at,
                    window.end_at,
                    "execution_error",
                )
                return AnalyticsReportData(
                    metrics=metrics,
                    top_failure_types=top_failure_types,
                    top_sql_errors=top_sql_errors,
                    tool_usage=tool_usage,
                    tool_miss_analysis=tool_miss_analysis,
                    schema_gaps=schema_gaps,
                    execution_failures=execution_failures,
                    degradation_signals=_degradation_signals(metrics, top_failure_types),
                    root_cause_summary=_root_cause_summary(top_failure_types, top_sql_errors),
                )
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to read analytics tables.") from exc

    def get_trace(self, trace_id: str) -> AnalyticsTraceRecord | None:
        try:
            with self._engine.connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT trace_id, user_query, plan_json, final_result, status, loop_depth, created_at
                        FROM agent_trace
                        WHERE trace_id = :trace_id
                        LIMIT 1
                        """
                    ),
                    {"trace_id": trace_id},
                ).mappings().first()
                if row is None:
                    return None
                created_at = row["created_at"]
                return {
                    "trace_id": str(row["trace_id"]),
                    "user_query": str(row["user_query"]),
                    "plan_json": cast(JsonObject | str | None, row["plan_json"]),
                    "final_result": cast(JsonObject | str | None, row["final_result"]),
                    "status": str(row["status"]),
                    "loop_depth": int(row["loop_depth"]),
                    "created_at": (
                        created_at
                        if isinstance(created_at, datetime)
                        else datetime.fromisoformat(str(created_at))
                    ),
                }
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to replay analytics trace.") from exc

    def list_events(self, trace_id: str) -> list[AnalyticsEventRecord]:
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT event_type, trace_id, step_id, component, input_json, output_json, latency_ms, timestamp
                        FROM agent_event
                        WHERE trace_id = :trace_id
                        ORDER BY timestamp ASC, id ASC
                        """
                    ),
                    {"trace_id": trace_id},
                ).mappings().all()
                return [
                    {
                        "event_type": str(row["event_type"]),
                        "trace_id": str(row["trace_id"]),
                        "step_id": int(row["step_id"]) if row["step_id"] is not None else None,
                        "component": str(row["component"]),
                        "input_json": cast(JsonObject | str | None, row["input_json"]),
                        "output_json": cast(JsonObject | str | None, row["output_json"]),
                        "latency_ms": (
                            int(row["latency_ms"]) if row["latency_ms"] is not None else None
                        ),
                        "timestamp": _datetime_value(row["timestamp"]),
                    }
                    for row in rows
                ]
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to replay analytics events.") from exc

    def list_failures(self, trace_id: str) -> list[AnalyticsFailureRecord]:
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT trace_id, failure_type, source_layer, error_code, summary, detail_json, created_at
                        FROM agent_failure
                        WHERE trace_id = :trace_id
                        ORDER BY created_at ASC, id ASC
                        """
                    ),
                    {"trace_id": trace_id},
                ).mappings().all()
                return [
                    {
                        "trace_id": str(row["trace_id"]),
                        "failure_type": (
                            str(row["failure_type"]) if row["failure_type"] is not None else None
                        ),
                        "source_layer": (
                            str(row["source_layer"]) if row["source_layer"] is not None else None
                        ),
                        "error_code": (
                            str(row["error_code"]) if row["error_code"] is not None else None
                        ),
                        "summary": str(row["summary"]),
                        "detail_json": cast(JsonObject | str | None, row["detail_json"]),
                        "created_at": _datetime_value(row["created_at"]),
                    }
                    for row in rows
                ]
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to replay analytics failures.") from exc


def _query_metrics(connection: Connection, start_at: datetime, end_at: datetime) -> ReportMetrics:
    trace_metrics = connection.execute(
        text(
            """
            SELECT
              COUNT(*) AS total_requests,
              COALESCE(1.0 * SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 0) AS success_rate,
              COALESCE(AVG(loop_depth), 0) AS avg_loop_depth
            FROM agent_trace
            WHERE created_at >= :start_at
              AND created_at < :end_at
            """
        ),
        {"start_at": start_at, "end_at": end_at},
    ).mappings().one()
    event_metrics = connection.execute(
        text(
            """
            SELECT
              COALESCE(AVG(latency_ms), 0) AS avg_latency,
              COALESCE(1.0 * SUM(CASE WHEN event_type='TOOL_EXECUTE_SUCCESS' THEN 1 ELSE 0 END)
                / NULLIF(SUM(CASE WHEN event_type IN ('TOOL_EXECUTE_SUCCESS', 'TOOL_EXECUTE_FAIL') THEN 1 ELSE 0 END), 0), 0) AS tool_hit_rate,
              COALESCE(1.0 * SUM(CASE WHEN event_type='SQL_EXECUTE_SUCCESS' THEN 1 ELSE 0 END)
                / NULLIF(SUM(CASE WHEN event_type IN ('SQL_EXECUTE_SUCCESS', 'SQL_EXECUTE_FAIL') THEN 1 ELSE 0 END), 0), 0) AS sql_success_rate,
              COALESCE(1.0 * COUNT(DISTINCT CASE WHEN event_type='REPLAN_TRIGGER' THEN trace_id END)
                / NULLIF(COUNT(DISTINCT trace_id), 0), 0) AS replan_rate
            FROM agent_event
            WHERE timestamp >= :start_at
              AND timestamp < :end_at
            """
        ),
        {"start_at": start_at, "end_at": end_at},
    ).mappings().one()
    failure_count = connection.execute(
        text(
            """
            SELECT COUNT(*) AS failure_count
            FROM agent_failure
            WHERE created_at >= :start_at
              AND created_at < :end_at
            """
        ),
        {"start_at": start_at, "end_at": end_at},
    ).scalar_one()
    total_requests = int(trace_metrics["total_requests"] or 0)
    metrics: ReportMetrics = {
        "total_requests": total_requests,
        "success_rate": _float_metric(trace_metrics["success_rate"]),
        "avg_loop_depth": _float_metric(trace_metrics["avg_loop_depth"]),
        "avg_latency": _float_metric(event_metrics["avg_latency"]),
        "tool_hit_rate": _float_metric(event_metrics["tool_hit_rate"]),
        "sql_success_rate": _float_metric(event_metrics["sql_success_rate"]),
        "replan_rate": _float_metric(event_metrics["replan_rate"]),
        "failure_count": int(failure_count or 0),
    }
    metrics["planner_success_rate"] = _query_planner_success_rate(
        connection,
        start_at,
        end_at,
        total_requests,
    )
    metrics["system_risk_level"] = _risk_level(metrics)
    metrics["most_used_tool"] = _query_most_used_tool(connection, start_at, end_at)
    return metrics


def _query_planner_success_rate(
    connection: Connection,
    start_at: datetime,
    end_at: datetime,
    total_requests: int,
) -> float:
    if total_requests <= 0:
        return 0.0
    planner_failures = connection.execute(
        text(
            """
            SELECT COUNT(*) AS planner_failures
            FROM agent_failure
            WHERE created_at >= :start_at
              AND created_at < :end_at
              AND (source_layer='planner' OR failure_type='missing_param')
            """
        ),
        {"start_at": start_at, "end_at": end_at},
    ).scalar_one()
    return round(max(total_requests - int(planner_failures or 0), 0) / total_requests, 4)


def _query_most_used_tool(connection: Connection, start_at: datetime, end_at: datetime) -> str:
    row = connection.execute(
        text(
            """
            SELECT component, COUNT(*) AS usage_count
            FROM agent_event
            WHERE timestamp >= :start_at
              AND timestamp < :end_at
              AND event_type IN ('TOOL_EXECUTE_SUCCESS', 'TOOL_EXECUTE_FAIL')
            GROUP BY component
            ORDER BY usage_count DESC, component ASC
            LIMIT 1
            """
        ),
        {"start_at": start_at, "end_at": end_at},
    ).mappings().first()
    return str(row["component"]) if row else "N/A"


def _query_top_failure_types(
    connection: Connection,
    start_at: datetime,
    end_at: datetime,
) -> list[CountGroup]:
    return _query_grouped(
        connection,
        """
        SELECT COALESCE(failure_type, 'unknown') AS name, COUNT(*) AS count
        FROM agent_failure
        WHERE created_at >= :start_at
          AND created_at < :end_at
        GROUP BY COALESCE(failure_type, 'unknown')
        ORDER BY count DESC, name ASC
        LIMIT 5
        """,
        start_at,
        end_at,
    )


def _query_top_sql_errors(
    connection: Connection,
    start_at: datetime,
    end_at: datetime,
) -> list[CountGroup]:
    return _query_grouped(
        connection,
        """
        SELECT COALESCE(error_code, failure_type, 'unknown_sql_error') AS name, COUNT(*) AS count
        FROM agent_failure
        WHERE created_at >= :start_at
          AND created_at < :end_at
          AND (source_layer='sql' OR failure_type IN ('sql_error', 'schema_gap'))
        GROUP BY COALESCE(error_code, failure_type, 'unknown_sql_error')
        ORDER BY count DESC, name ASC
        LIMIT 5
        """,
        start_at,
        end_at,
    )


def _query_tool_usage(
    connection: Connection,
    start_at: datetime,
    end_at: datetime,
) -> list[CountGroup]:
    return _query_grouped(
        connection,
        """
        SELECT component AS name, COUNT(*) AS count
        FROM agent_event
        WHERE timestamp >= :start_at
          AND timestamp < :end_at
          AND event_type IN ('TOOL_EXECUTE_SUCCESS', 'TOOL_EXECUTE_FAIL')
        GROUP BY component
        ORDER BY count DESC, name ASC
        LIMIT 5
        """,
        start_at,
        end_at,
    )


def _query_failure_group(
    connection: Connection,
    start_at: datetime,
    end_at: datetime,
    failure_type: str,
) -> list[CountGroup]:
    return _query_grouped(
        connection,
        """
        SELECT COALESCE(error_code, failure_type, 'unknown') AS name, COUNT(*) AS count
        FROM agent_failure
        WHERE created_at >= :start_at
          AND created_at < :end_at
          AND failure_type = :failure_type
        GROUP BY COALESCE(error_code, failure_type, 'unknown')
        ORDER BY count DESC, name ASC
        LIMIT 5
        """,
        start_at,
        end_at,
        {"failure_type": failure_type},
    )


def _query_grouped(
    connection: Connection,
    sql: str,
    start_at: datetime,
    end_at: datetime,
    extra_params: dict[str, object] | None = None,
) -> list[CountGroup]:
    rows = connection.execute(
        text(sql),
        {"start_at": start_at, "end_at": end_at, **(extra_params or {})},
    ).mappings().all()
    return [{"name": str(row["name"]), "count": int(row["count"])} for row in rows]


def _degradation_signals(metrics: ReportMetrics, top_failure_types: list[CountGroup]) -> list[str]:
    signals: list[str] = []
    if float(metrics.get("replan_rate") or 0) > 0.2:
        signals.append("loop instability: replan_rate above 20%")
    if top_failure_types:
        signals.append(
            "rising failure patterns: "
            + ", ".join(str(item["name"]) for item in top_failure_types[:3])
        )
    if float(metrics.get("sql_success_rate") or 0) < 0.95:
        signals.append("sql instability: sql_success_rate below 95%")
    return signals


def _root_cause_summary(
    top_failure_types: list[CountGroup],
    top_sql_errors: list[CountGroup],
) -> str:
    if not top_failure_types and not top_sql_errors:
        return "No dominant failure pattern in the selected window."
    parts: list[str] = []
    if top_failure_types:
        parts.append(
            "Top failures: " + ", ".join(str(item["name"]) for item in top_failure_types[:3])
        )
    if top_sql_errors:
        parts.append(
            "Top SQL errors: " + ", ".join(str(item["name"]) for item in top_sql_errors[:3])
        )
    return " ".join(parts)


def _risk_level(metrics: ReportMetrics) -> str:
    success_rate = float(metrics.get("success_rate") or 0)
    sql_success_rate = float(metrics.get("sql_success_rate") or 0)
    failure_count = int(metrics.get("failure_count") or 0)
    replan_rate = float(metrics.get("replan_rate") or 0)
    if success_rate < 0.8 or sql_success_rate < 0.8 or failure_count >= 10:
        return "HIGH"
    if success_rate < 0.95 or replan_rate > 0.2 or failure_count > 0:
        return "MEDIUM"
    return "LOW"


def _float_metric(value: object) -> float:
    normalized = _normalize_number(value)
    if isinstance(normalized, (int, float)):
        return float(normalized)
    return 0.0


def _normalize_number(value: object) -> MetricValue:
    if isinstance(value, Decimal):
        return round(float(value), 4)
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, int) or isinstance(value, str) or value is None:
        return value
    return str(value)


def _datetime_value(value: object) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
