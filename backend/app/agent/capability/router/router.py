from app.agent.capability.registry import CapabilityRuntimeRegistry
from app.agent.capability.router.matcher import CapabilityMatcher
from app.agent.capability.router.models import (
    CapabilityExecutionPlan,
    SemanticIntent,
)


class CapabilityRouter:
    def __init__(self, registry: CapabilityRuntimeRegistry):
        self._matcher = CapabilityMatcher(registry)

    def route(self, semantic_intent: SemanticIntent) -> CapabilityExecutionPlan:
        capability = self._matcher.match(semantic_intent)
        if capability is None:
            return CapabilityExecutionPlan(
                status="capability_not_found",
                arguments=semantic_intent.arguments,
                reason=(
                    "No catalog capability matched "
                    f"domain={semantic_intent.domain} intent={semantic_intent.intent}."
                ),
            )
        if not capability.executable:
            return CapabilityExecutionPlan(
                status="capability_not_executable",
                capability=capability.name,
                execution_type=capability.execution_type,
                executor=capability.executor,
                arguments=semantic_intent.arguments,
                reason=(
                    f"Capability '{capability.name}' is not executable because "
                    f"status is '{capability.status}'."
                ),
            )
        return CapabilityExecutionPlan(
            status="matched",
            capability=capability.name,
            execution_type=capability.execution_type,
            executor=capability.executor,
            arguments=semantic_intent.arguments,
            reason=f"Catalog matched capability '{capability.name}'.",
        )
