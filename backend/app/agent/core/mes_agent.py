import uuid

from app.agent.context.models import AgentRequest, AgentResponse
from app.agent.core.agent_router import AgentRouter
from app.agent.runtime.audit.runtime import AuditRuntime
from app.agent.runtime.trace.runtime import TraceRuntime


class MesAgent:
    """V2 unified entrypoint; it contains no MES business decisions."""

    def __init__(self, router: AgentRouter, trace_runtime: TraceRuntime, audit_runtime: AuditRuntime):
        self._router = router
        self._trace_runtime = trace_runtime
        self._audit_runtime = audit_runtime

    def run(self, request: AgentRequest) -> AgentResponse:
        request_id = uuid.uuid4().hex
        self._trace_runtime.start(request_id, request.message)
        agent = self._router.route(request)
        self._trace_runtime.record(request_id, "agent_router", {"agent": agent.name})
        try:
            response = agent.run(request, request_id)
        except Exception as exc:
            self._trace_runtime.record(request_id, "result", {"status": "error", "error_type": type(exc).__name__})
            response = AgentResponse(request_id=request_id, agent=agent.name, status="error")
        response.trace = self._trace_runtime.finish(request_id, response.status)
        self._audit_runtime.record(request, response)
        return response
