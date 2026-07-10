import logging
from typing import Protocol

from app.agent.context.models import AgentRequest, AgentResponse


class AuditRuntime(Protocol):
    def record(self, request: AgentRequest, response: AgentResponse) -> None: ...


class NullAuditRuntime:
    def record(self, request: AgentRequest, response: AgentResponse) -> None:
        del request, response


class LoggingAuditRuntime:
    """Default V2 audit sink. Persistence can be injected without changing agents."""

    def __init__(self, logger: logging.Logger | None = None):
        self._logger = logger or logging.getLogger("agent.audit")

    def record(self, request: AgentRequest, response: AgentResponse) -> None:
        self._logger.info(
            "agent_audit request_id=%s agent=%s capability=%s status=%s input_length=%s",
            response.request_id,
            response.agent,
            response.capability,
            response.status,
            len(request.message),
        )
