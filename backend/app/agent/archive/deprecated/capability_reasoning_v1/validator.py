from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.capability.catalog.router import CapabilityRouter

from .models import CapabilityReasoningResult, CapabilityValidationResult


class CapabilityReasoningValidator:
    def __init__(self, registry: CapabilityRuntimeRegistry):
        self._registry = registry
        self._router = CapabilityRouter(registry)

    def validate(self, result: CapabilityReasoningResult) -> CapabilityValidationResult:
        if result.need_clarification or not result.selected_capability:
            return CapabilityValidationResult(
                status="need_clarification",
                entities=result.entities,
                need_clarification=True,
                clarification_reason=result.clarification_reason,
            )
        capability = self._registry.get(result.selected_capability)
        if capability is None:
            return CapabilityValidationResult(
                status="capability_not_found",
                selected_capability=result.selected_capability,
                entities=result.entities,
                need_clarification=True,
                clarification_reason="模型选择了 Catalog 中不存在的能力。",
            )
        required_entities = capability.input_entities or capability.required_entities
        missing = [name for name in required_entities if not result.entities.get(name)]
        if missing:
            return CapabilityValidationResult(
                status="missing_required_entities",
                selected_capability=capability.name,
                execution_type=capability.execution_type,
                executor=capability.executor,
                entities=result.entities,
                missing_entities=missing,
                need_clarification=True,
                clarification_reason="缺少必要业务实体：" + ", ".join(missing),
            )
        routed = self._router.route_selected(capability.name, result.entities)
        if routed.status == "capability_not_executable":
            return CapabilityValidationResult(
                status="capability_not_executable",
                selected_capability=capability.name,
                execution_type=capability.execution_type,
                executor=capability.executor,
                entities=result.entities,
                need_clarification=True,
                clarification_reason=(
                    f"Capability '{capability.name}' 当前状态为 {capability.status}，不能执行。"
                ),
            )
        return CapabilityValidationResult(
            status="matched",
            selected_capability=capability.name,
            execution_type=capability.execution_type,
            executor=capability.executor,
            entities=result.entities,
        )
