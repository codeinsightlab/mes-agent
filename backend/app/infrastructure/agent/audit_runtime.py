import logging

from app.agent.context.models import AgentRequest, AgentResponse
from app.analytics.event.collector import AgentEventCollector
from app.domain.persistence.exceptions import PersistenceError


class AnalyticsAuditRuntime:
    """Persists V2 audit records through the existing analytics collector."""

    def __init__(self, collector: AgentEventCollector):
        self._collector = collector
        self._logger = logging.getLogger(__name__)

    def record(self, request: AgentRequest, response: AgentResponse) -> None:
        try:
            self._collector.record_trace(
                trace_id=response.request_id,
                user_query=request.message,
                plan_json={"agent": response.agent, "capability": response.capability},
                final_result=response.model_dump(mode="json"),
                status=response.status,
                loop_depth=1,
            )
        except PersistenceError:
            self._logger.exception("V2 agent audit persistence failed")
