import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.agent.capability.loader import CapabilityLoader
from app.agent.capability_reasoning.audit import CapabilityReasoningAuditRepository
from app.agent.capability_reasoning.generator import build_prompt
from app.agent.capability_reasoning.models import CapabilityReasoningResult
from app.agent.capability_reasoning.reasoner import (
    CapabilityReasoner,
    default_heat_treatment_business_facts,
)
from app.agent.capability_reasoning.validator import CapabilityReasoningValidator


def test_capability_reasoning_result_rejects_execution_fields():
    with pytest.raises(ValidationError):
        CapabilityReasoningResult.model_validate(
            {
                "goal": "查询状态",
                "context_level": "catalog_only",
                "candidate_capabilities": [],
                "selected_capability": None,
                "entities": {},
                "confidence": 0.1,
                "need_clarification": True,
                "sql": "SELECT 1",
            }
        )


def test_capability_reasoner_selects_status_from_catalog():
    registry = CapabilityLoader().load()
    result = CapabilityReasoner(registry).reason("TRACE-HTR-B-H-001什么状态")

    assert result.selected_capability == "heat_current_stage"
    assert result.entities == {"record_no": "TRACE-HTR-B-H-001"}
    assert result.context_level == "catalog_only"


def test_business_facts_improve_device_reasoning():
    registry = CapabilityLoader().load()
    reasoner = CapabilityReasoner(registry)

    catalog_only = reasoner.reason_catalog_only("TRACE-HTR-B-H-001在哪个炉子完成")
    with_facts = reasoner.reason_with_business_facts(
        "TRACE-HTR-B-H-001在哪个炉子完成",
        default_heat_treatment_business_facts(),
    )

    assert catalog_only.selected_capability is None
    assert with_facts.selected_capability == "heat_device_trace"
    assert with_facts.context_level == "catalog_with_business_facts"


def test_validator_rejects_planned_capability_without_execution():
    registry = CapabilityLoader().load()
    reasoning = CapabilityReasoner(registry).reason_with_business_facts(
        "TRACE-HTR-B-H-001在哪个炉子完成"
    )

    validation = CapabilityReasoningValidator(registry).validate(reasoning)

    assert validation.status == "capability_not_executable"
    assert validation.selected_capability == "heat_device_trace"
    assert validation.need_clarification is True


def test_validator_requires_missing_entities():
    registry = CapabilityLoader().load()
    reasoning = CapabilityReasoner(registry).reason("查热处理状态")

    validation = CapabilityReasoningValidator(registry).validate(reasoning)

    assert validation.status == "missing_required_entities"
    assert validation.missing_entities == ["record_no"]


def test_capability_reasoning_audit_records_result():
    registry = CapabilityLoader().load()
    reasoning = CapabilityReasoner(registry).reason("TRACE-HTR-B-H-001什么状态")
    validation = CapabilityReasoningValidator(registry).validate(reasoning)
    engine = create_engine("sqlite://", future=True)
    audit = CapabilityReasoningAuditRepository(engine)

    audit.record(
        request_id="req-1",
        user_input="TRACE-HTR-B-H-001什么状态",
        reasoning_result=reasoning,
        validation_result=validation,
        execution_result={"would_execute": True},
    )

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM capability_reasoning_audit")
        ).scalar_one()
    assert count == 1


def test_capability_reasoning_prompt_contains_catalog_and_forbidden_actions():
    registry = CapabilityLoader().load()

    prompt = build_prompt(
        "TRACE-HTR-B-H-001什么状态",
        registry,
        "catalog_only",
    )

    assert "heat_current_stage" in prompt
    assert "heat_device_trace" in prompt
    assert "禁止" in prompt
    assert "输出 SQL" in prompt
    assert "CapabilityReasoningResult" in prompt
