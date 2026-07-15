import json
from pathlib import Path

from app.agent.capability.catalog.registry import CapabilityRuntimeRegistry
from app.agent.reasoning.capability_reasoning.audit import (
    CapabilityReasoningAuditRecord,
    CapabilityReasoningAuditSink,
    LoggingCapabilityReasoningAuditSink,
)
from app.agent.reasoning.capability_reasoning.models import (
    BusinessFacts,
    CapabilityReasoningResult,
)
from app.agent.runtime.llm import LlmRuntime, LlmStructuredOutputError


PROMPT_VERSION = "capability-reasoning-v2"
DEFAULT_BUSINESS_FACT_VERSION = "heat-treatment-business-facts-v1"
PROMPT_PATH = Path(__file__).with_name("prompt") / "capability_reasoning_v2.md"


class LlmCapabilityReasoningAdapter:
    """LLM-native capability selection. It never executes a capability."""

    def __init__(
        self,
        llm_runtime: LlmRuntime,
        audit_sink: CapabilityReasoningAuditSink | None = None,
        business_fact_version: str = DEFAULT_BUSINESS_FACT_VERSION,
    ):
        self._llm_runtime = llm_runtime
        self._audit_sink = audit_sink or LoggingCapabilityReasoningAuditSink()
        self._business_fact_version = business_fact_version
        self._prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    def reason(
        self,
        user_input: str,
        registry: CapabilityRuntimeRegistry,
        business_facts: BusinessFacts,
    ) -> CapabilityReasoningResult:
        prompt = self.build_prompt(user_input, registry, business_facts)
        available = [
            capability.name
            for capability in registry.all()
            if capability.domain == "heat_treatment"
        ]
        try:
            result = self._llm_runtime.structured(prompt, CapabilityReasoningResult)
        except LlmStructuredOutputError as exc:
            self._audit_sink.record(
                CapabilityReasoningAuditRecord(
                    user_input=user_input,
                    prompt_version=PROMPT_VERSION,
                    available_capabilities=available,
                    business_fact_version=self._business_fact_version,
                    llm_output=exc.raw_output,
                    selected_capability=None,
                    confidence=0,
                    need_clarification=True,
                    parse_error=str(exc),
                )
            )
            raise
        raw_result = result
        selected = result.selected_capability_name
        if selected is not None and selected not in available:
            result = result.model_copy(
                update={
                    "selected_capability": None,
                    "need_clarification": True,
                    "clarification_reason": (
                        f"模型选择了 Catalog 中不存在的 Capability: {selected}。"
                    ),
                }
            )
            selected = None
        self._audit_sink.record(
            CapabilityReasoningAuditRecord(
                user_input=user_input,
                prompt_version=PROMPT_VERSION,
                available_capabilities=available,
                business_fact_version=self._business_fact_version,
                llm_output=raw_result,
                selected_capability=selected,
                confidence=result.confidence,
                need_clarification=result.need_clarification,
            )
        )
        return result

    def build_prompt(
        self,
        user_input: str,
        registry: CapabilityRuntimeRegistry,
        business_facts: BusinessFacts,
    ) -> str:
        return (
            self._prompt_template.replace("{{user_input}}", user_input)
            .replace("{{capability_catalog}}", _catalog_json(registry))
            .replace("{{business_facts}}", business_facts.model_dump_json(indent=2))
        )


def _catalog_json(registry: CapabilityRuntimeRegistry) -> str:
    payload = [
        {
            "name": capability.name,
            "description": capability.description,
            "business_goal": capability.business_goal,
            "when_to_use": capability.when_to_use,
            "examples": capability.examples or capability.example_queries,
            "input_entities": capability.input_entities or capability.required_entities,
            "execution_type": capability.execution_type,
            "api_contract": capability.api_contract,
            "status": capability.status,
        }
        for capability in registry.all()
        if capability.domain == "heat_treatment"
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)
