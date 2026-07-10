from app.agent.agents.heat_treatment.business_facts import HEAT_TREATMENT_BUSINESS_FACTS
from app.agent.agents.heat_treatment.capabilities import HEAT_TREATMENT_CAPABILITIES
from app.agent.reasoning.capability_reasoning.validator import CapabilityReasoningValidator
from app.agent.context.models import AgentRequest, AgentResponse
from app.agent.reasoning import CapabilityReasoner
from app.agent.runtime.capability.runtime import CapabilityRuntime
from app.agent.runtime.trace.runtime import TraceRuntime


class HeatTreatmentAgent:
    name = "heat_treatment_agent"

    def __init__(self, reasoner: CapabilityReasoner, capability_runtime: CapabilityRuntime, trace_runtime: TraceRuntime):
        self._reasoner = reasoner
        self._capability_runtime = capability_runtime
        self._validator = CapabilityReasoningValidator(capability_runtime.registry)
        self._trace_runtime = trace_runtime

    def run(self, request: AgentRequest, request_id: str) -> AgentResponse:
        reasoning = self._reasoner.reason(request.message, HEAT_TREATMENT_BUSINESS_FACTS)
        self._trace_runtime.record(request_id, "reasoning", reasoning.model_dump(mode="json"))
        selected = reasoning.selected_capability
        if selected not in HEAT_TREATMENT_CAPABILITIES:
            selected = None
        validation = self._validator.validate(reasoning)
        if selected is None or validation.status != "matched":
            self._trace_runtime.record(request_id, "capability", {"name": selected, "status": validation.status})
            return AgentResponse(
                request_id=request_id,
                agent=self.name,
                status="clarification_required",
                capability=selected,
                clarification=validation.clarification_reason or reasoning.clarification_reason,
            )
        arguments = dict(reasoning.entities)
        if selected == "heat_completion_count_monthly":
            arguments["question"] = request.message
        self._trace_runtime.record(request_id, "capability", {"name": selected, "status": "validated"})
        data = self._capability_runtime.execute(selected, arguments)
        self._trace_runtime.record(request_id, "execution", {"capability": selected, "status": "success"})
        return AgentResponse(request_id=request_id, agent=self.name, status="success", capability=selected, data=data)
