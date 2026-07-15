from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.reasoning.capability_reasoning.models import BusinessFacts, CapabilityReasoningResult
from app.agent.reasoning.capability_reasoning.adapter import LlmCapabilityReasoningAdapter
from app.agent.reasoning.capability_reasoning.audit import CapabilityReasoningAuditSink
from app.agent.runtime.llm.runtime import LlmRuntime


class CapabilityReasoner:
    """Shared reasoning boundary. It selects a capability but never executes one."""

    def __init__(
        self,
        registry: CapabilityRuntimeRegistry,
        llm_runtime: LlmRuntime,
        audit_sink: CapabilityReasoningAuditSink | None = None,
    ):
        self._registry = registry
        self._adapter = LlmCapabilityReasoningAdapter(llm_runtime, audit_sink)

    def reason(self, user_input: str, business_facts: BusinessFacts) -> CapabilityReasoningResult:
        return self._adapter.reason(user_input, self._registry, business_facts)
