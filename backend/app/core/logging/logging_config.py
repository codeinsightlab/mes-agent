import json
import logging
import logging.config
import os
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any


DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SQL_LOG_LEVEL = "INFO"
_TRACE_ID: ContextVar[str] = ContextVar("agent_trace_id", default="-")


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        if not hasattr(record, "event"):
            record.event = record.getMessage()
        if not hasattr(record, "fields"):
            record.fields = {}
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", "-"),
            "event": getattr(record, "event", record.getMessage()),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    *,
    level: str | None = None,
    sql_level: str | None = None,
    json_format: bool | None = None,
) -> None:
    app_level = _normalize_level(level or os.getenv("AGENT_LOG_LEVEL") or DEFAULT_LOG_LEVEL)
    agent_sql_level = _normalize_level(
        sql_level or os.getenv("AGENT_SQL_LOG_LEVEL") or DEFAULT_SQL_LOG_LEVEL
    )
    use_json = json_format
    if use_json is None:
        use_json = (os.getenv("AGENT_LOG_FORMAT") or "json").strip().lower() == "json"

    formatter = (
        {
            "()": "app.core.logging.logging_config.JsonLogFormatter",
        }
        if use_json
        else {
            "format": (
                "%(asctime)s %(levelname)s %(name)s "
                "[trace_id=%(trace_id)s] event=%(event)s %(message)s"
            )
        }
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "trace_id": {
                    "()": "app.core.logging.logging_config.TraceIdFilter",
                }
            },
            "formatters": {"agent": formatter},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "agent",
                    "filters": ["trace_id"],
                }
            },
            "loggers": {
                "agent": {
                    "handlers": ["console"],
                    "level": app_level,
                    "propagate": False,
                },
                "agent.sql": {
                    "handlers": ["console"],
                    "level": agent_sql_level,
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": app_level,
            },
        }
    )


def set_trace_id(trace_id: str) -> Token[str]:
    return _TRACE_ID.set(trace_id)


def reset_trace_id(token: Token[str]) -> None:
    _TRACE_ID.reset(token)


def get_trace_id() -> str:
    return _TRACE_ID.get()


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    logger.log(
        level,
        event,
        extra={"event": event, "fields": fields, "trace_id": get_trace_id()},
    )


def _normalize_level(level: str) -> str:
    normalized = level.strip().upper()
    if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return DEFAULT_LOG_LEVEL
    return normalized
