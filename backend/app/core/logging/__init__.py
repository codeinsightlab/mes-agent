import logging

from app.core.logging.logging_config import (
    configure_logging,
    get_trace_id,
    log_event,
    reset_trace_id,
    set_trace_id,
)

logging.getLogger("agent").addHandler(logging.NullHandler())

__all__ = [
    "configure_logging",
    "get_trace_id",
    "log_event",
    "reset_trace_id",
    "set_trace_id",
]
