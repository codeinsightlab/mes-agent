from app.agent.capability.registry import CapabilityRuntimeRegistry
from app.agent.capability.router.matcher import CapabilityMatcher
from app.agent.capability.router.models import (
    CapabilityExecutionPlan,
    SemanticIntent,
)


class CapabilityRouter:
    def __init__(self, registry: CapabilityRuntimeRegistry):
        self._registry = registry
        self._matcher = CapabilityMatcher(registry)

    def route(self, semantic_intent: SemanticIntent) -> CapabilityExecutionPlan:
        capability = self._matcher.match(semantic_intent)
        if capability is None:
            return CapabilityExecutionPlan(
                status="capability_not_found",
                arguments=semantic_intent.arguments,
                catalog_version="v2",
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
                catalog_version=capability.catalog_version,
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
            catalog_version=capability.catalog_version,
            reason=f"Catalog matched capability '{capability.name}'.",
        )

    def route_selected(
        self,
        capability_name: str | None,
        arguments: dict,
    ) -> CapabilityExecutionPlan:
        if not capability_name:
            return CapabilityExecutionPlan(
                status="capability_not_found",
                arguments=arguments,
                catalog_version="v2",
                reason="Capability reasoning did not select a capability.",
            )
        capability = self._registry.get(capability_name)
        if capability is None:
            return CapabilityExecutionPlan(
                status="capability_not_found",
                capability=capability_name,
                arguments=arguments,
                catalog_version="v2",
                reason=f"Capability reasoning selected unknown capability '{capability_name}'.",
            )
        if not capability.executable:
            return CapabilityExecutionPlan(
                status="capability_not_executable",
                capability=capability.name,
                execution_type=capability.execution_type,
                executor=capability.executor,
                arguments=arguments,
                catalog_version=capability.catalog_version,
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
            arguments=arguments,
            catalog_version=capability.catalog_version,
            reason=f"Capability reasoning selected catalog capability '{capability.name}'.",
        )
