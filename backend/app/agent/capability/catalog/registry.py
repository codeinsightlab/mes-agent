from app.agent.capability.models.definitions import CapabilityDefinition
from app.agent.capability.catalog.validator import CapabilityNotExecutableError


class CapabilityRuntimeRegistry:
    def __init__(self, capabilities: list[CapabilityDefinition]):
        self._capabilities = {capability.name: capability for capability in capabilities}

    def get(self, name: str) -> CapabilityDefinition | None:
        return self._capabilities.get(name)

    def require(self, name: str) -> CapabilityDefinition:
        capability = self.get(name)
        if capability is None:
            raise KeyError(f"Unknown capability: {name}")
        return capability

    def require_executable(self, name: str) -> CapabilityDefinition:
        capability = self.require(name)
        if not capability.executable:
            raise CapabilityNotExecutableError(
                f"Capability '{name}' is not executable because status is '{capability.status}'."
            )
        return capability

    def all(self) -> list[CapabilityDefinition]:
        return list(self._capabilities.values())

    def names(self) -> list[str]:
        return sorted(self._capabilities)

    def __len__(self) -> int:
        return len(self._capabilities)
