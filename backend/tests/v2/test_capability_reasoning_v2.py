import pytest
from pydantic import ValidationError

from app.agent.agents.heat_treatment.business_facts import HEAT_TREATMENT_BUSINESS_FACTS
from app.agent.capability.catalog.loader import CapabilityLoader
from app.agent.reasoning.capability_reasoning.adapter import LlmCapabilityReasoningAdapter
from app.agent.reasoning.capability_reasoning.models import CapabilityReasoningResult
from app.agent.runtime.llm import LlmRuntime


class StaticModel:
    def __init__(self, payload):
        self.payload = payload

    def with_structured_output(self, output_type):
        return self

    def invoke(self, prompt):
        return self.payload


class RecordingSink:
    def __init__(self):
        self.records = []

    def record(self, audit):
        self.records.append(audit)


def test_prompt_contains_capability_knowledge_and_forbidden_boundaries():
    registry = CapabilityLoader().load()
    adapter = LlmCapabilityReasoningAdapter(LlmRuntime(StaticModel({})))

    prompt = adapter.build_prompt(
        "TRACE-HTR-B-H-001什么状态",
        registry,
        HEAT_TREATMENT_BUSINESS_FACTS,
    )

    assert "business_goal" in prompt
    assert "when_to_use" in prompt
    assert "heat_current_stage" in prompt
    assert "不得输出 SQL" in prompt
    assert "planned" in prompt


def test_unknown_capability_is_normalized_to_clarification_and_raw_output_is_audited():
    registry = CapabilityLoader().load()
    sink = RecordingSink()
    adapter = LlmCapabilityReasoningAdapter(
        LlmRuntime(
            StaticModel(
                {
                    "goal": "查询炉子异常排行",
                    "domain": "heat_treatment",
                    "selected_capability": {
                        "name": "heat_device_abnormal_ranking",
                        "reason": "用户询问异常排行",
                    },
                    "entities": {},
                    "confidence": 0.9,
                    "need_clarification": False,
                    "clarification_reason": None,
                }
            )
        ),
        sink,
    )

    result = adapter.reason(
        "最近哪个炉子异常最多",
        registry,
        HEAT_TREATMENT_BUSINESS_FACTS,
    )

    assert result.selected_capability is None
    assert result.need_clarification is True
    assert sink.records[0].llm_output.selected_capability_name == "heat_device_abnormal_ranking"
    assert sink.records[0].selected_capability is None


def test_output_protocol_recursively_rejects_execution_fields():
    with pytest.raises(ValidationError, match="sql"):
        CapabilityReasoningResult.model_validate(
            {
                "goal": "查询状态",
                "domain": "heat_treatment",
                "selected_capability": None,
                "entities": {"sql": "SELECT 1"},
                "confidence": 0.2,
                "need_clarification": True,
                "clarification_reason": "无法判断",
            }
        )
