from typing import Protocol

from app.agent.context.models import AgentRequest, AgentResponse


class DomainAgent(Protocol):
    name: str

    def run(self, request: AgentRequest, request_id: str) -> AgentResponse: ...


class AgentRouter:
    """V2 domain router. The selection seam is stable; routing is intentionally fixed."""

    def __init__(self, heat_treatment_agent: DomainAgent):
        self._heat_treatment_agent = heat_treatment_agent

    def route(self, request: AgentRequest) -> DomainAgent:
        del request
        return self._heat_treatment_agent
