from collections.abc import Iterable

from app.agent.capability.models import CapabilityDefinition


class CapabilityCatalogError(Exception):
    """Base error for capability catalog runtime failures."""


class CapabilityCatalogLoadError(CapabilityCatalogError):
    """Raised when catalog files cannot be loaded or parsed."""


class CapabilityCatalogValidationError(CapabilityCatalogError):
    """Raised when a capability definition fails runtime validation."""


class CapabilityNotExecutableError(CapabilityCatalogError):
    """Raised when a loaded capability exists but cannot be executed."""


class CapabilityValidator:
    def __init__(self, executor_names: Iterable[str]):
        self._executor_names = set(executor_names)

    def validate(self, capabilities: list[CapabilityDefinition]) -> None:
        names: set[str] = set()
        for capability in capabilities:
            if capability.name in names:
                raise CapabilityCatalogValidationError(
                    f"Duplicate capability name: {capability.name}"
                )
            names.add(capability.name)
            self.validate_capability(capability)

    def validate_capability(self, capability: CapabilityDefinition) -> None:
        if (
            capability.status == "enabled"
            and capability.execution_type == "tool"
            and capability.executor not in self._executor_names
        ):
            raise CapabilityCatalogValidationError(
                f"Capability '{capability.name}' references unknown executor: {capability.executor}"
            )
        if capability.status == "enabled" and capability.execution_type == "tool":
            if capability.executor not in self._executor_names:
                raise CapabilityCatalogValidationError(
                    f"Enabled capability '{capability.name}' has no registered executor: {capability.executor}"
                )
