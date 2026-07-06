from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.type_defs import JsonObject
from app.domain.persistence.exceptions import PersistenceError


class AgentEventCollector:
    def __init__(self, engine: Engine):
        self._engine = engine

    def record_event(
        self,
        *,
        event_type: str,
        trace_id: str,
        component: str,
        step_id: int | None = None,
        input_json: JsonObject | None = None,
        output_json: JsonObject | None = None,
        latency_ms: int | None = None,
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO agent_event (
                            event_type,
                            trace_id,
                            step_id,
                            component,
                            input_json,
                            output_json,
                            latency_ms,
                            timestamp,
                            created_at
                        )
                        VALUES (
                            :event_type,
                            :trace_id,
                            :step_id,
                            :component,
                            :input_json,
                            :output_json,
                            :latency_ms,
                            :timestamp,
                            :created_at
                        )
                        """
                    ),
                    {
                        "event_type": event_type,
                        "trace_id": trace_id,
                        "step_id": step_id,
                        "component": component,
                        "input_json": _json_value(input_json),
                        "output_json": _json_value(output_json),
                        "latency_ms": latency_ms,
                        "timestamp": now,
                        "created_at": now,
                    },
                )
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to write agent event.") from exc

    def record_trace(
        self,
        *,
        trace_id: str,
        user_query: str,
        plan_json: JsonObject,
        final_result: JsonObject,
        status: str,
        loop_depth: int,
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO agent_trace (
                            trace_id,
                            user_query,
                            plan_json,
                            final_result,
                            status,
                            loop_depth,
                            created_at
                        )
                        VALUES (
                            :trace_id,
                            :user_query,
                            :plan_json,
                            :final_result,
                            :status,
                            :loop_depth,
                            :created_at
                        )
                        """
                    ),
                    {
                        "trace_id": trace_id,
                        "user_query": user_query,
                        "plan_json": _json_value(plan_json),
                        "final_result": _json_value(final_result),
                        "status": status,
                        "loop_depth": loop_depth,
                        "created_at": now,
                    },
                )
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to write agent trace.") from exc

    def record_failure(
        self,
        *,
        trace_id: str,
        failure_type: str | None,
        source_layer: str | None,
        error_code: str | None,
        summary: str,
        detail_json: JsonObject | None = None,
    ) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO agent_failure (
                            trace_id,
                            failure_type,
                            source_layer,
                            error_code,
                            summary,
                            detail_json,
                            created_at
                        )
                        VALUES (
                            :trace_id,
                            :failure_type,
                            :source_layer,
                            :error_code,
                            :summary,
                            :detail_json,
                            :created_at
                        )
                        """
                    ),
                    {
                        "trace_id": trace_id,
                        "failure_type": failure_type,
                        "source_layer": source_layer,
                        "error_code": error_code,
                        "summary": summary,
                        "detail_json": _json_value(detail_json),
                        "created_at": now,
                    },
                )
        except SQLAlchemyError as exc:
            raise PersistenceError("Failed to write agent failure.") from exc


def _json_value(value: JsonObject | None) -> str | None:
    if value is None:
        return None
    # SQLAlchemy text() cannot portably infer JSON values across SQLite/MySQL;
    # store a compact JSON string and let the DB JSON column cast it when supported.
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
