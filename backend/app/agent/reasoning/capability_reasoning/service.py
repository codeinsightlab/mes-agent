from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.reasoning.capability_reasoning.models import BusinessFacts, CapabilityReasoningResult
from app.agent.reasoning.capability_reasoning.reasoner import CapabilityReasoner as LegacyReasoningAlgorithm
from app.agent.runtime.llm.runtime import LlmRuntime


class CapabilityReasoner:
    """Shared reasoning boundary. It selects a capability but never executes one."""

    def __init__(self, registry: CapabilityRuntimeRegistry, llm_runtime: LlmRuntime):
        self._algorithm = LegacyReasoningAlgorithm(registry)
        self._llm_runtime = llm_runtime

    def reason(self, user_input: str, business_facts: BusinessFacts) -> CapabilityReasoningResult:
        # The V2 seam accepts the shared LLM runtime. Current deterministic behavior is
        # retained until a model-backed reasoner is explicitly requested.
        _ = self._llm_runtime
        return self._algorithm.reason_with_business_facts(user_input, business_facts)
