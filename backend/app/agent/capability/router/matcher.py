from app.agent.capability.models import CapabilityDefinition
from app.agent.capability.registry import CapabilityRuntimeRegistry
from app.agent.capability.router.models import SemanticIntent


class CapabilityMatcher:
    def __init__(self, registry: CapabilityRuntimeRegistry):
        self._registry = registry

    def match(self, semantic_intent: SemanticIntent) -> CapabilityDefinition | None:
        for capability in self._registry.all():
            if capability.domain != semantic_intent.domain:
                continue
            if semantic_intent.intent in capability.intent:
                return capability
        return None
