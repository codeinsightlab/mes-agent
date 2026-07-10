import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.agent.orchestrator.agent_orchestrator import (
    AgentOrchestrator,
    AgentRunInput,
    PlanExecutionAdapter,
)
from app.agent.planner.models import PlannerRequest
from app.agent.planner.planner import DebuggablePlanner
from app.agent.semantic_router import SemanticRouter, SemanticRouterResult
from tests.heat_tool_test_utils import build_heat_treatment_test_registry
from tests.test_agent_orchestrator import FakeTextToSqlNode


GOLDEN_CASES_PATH = Path(__file__).parent / "golden" / "semantic_router" / "cases.json"


def load_golden_cases():
    return json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))


def test_semantic_router_extracts_explicit_heat_status_query():
    result = SemanticRouter().route("HT20260603-007热处理状态")

    assert result.semantic_router_version == "v1"
    assert result.domain == "heat_treatment"
    assert result.intent == "query_status"
    assert result.entities == {"record_no": "HT20260603-007"}
    assert result.confidence == 0.95
    assert result.need_clarification is False
    assert result.clarification_reason is None


def test_semantic_router_result_protocol_rejects_forbidden_fields():
    payload = {
        "semantic_router_version": "v1",
        "domain": "heat_treatment",
        "intent": "query_status",
        "entities": {},
        "confidence": 0.9,
        "need_clarification": False,
        "tool": "heat_current_stage",
    }

    with pytest.raises(ValidationError):
        SemanticRouterResult.model_validate(payload)


def test_semantic_router_normalizes_synonym_expression():
    result = SemanticRouter().route("这个热处理做到哪一步了")

    assert result.domain == "heat_treatment"
    assert result.intent == "query_status"


def test_semantic_router_marks_ambiguous_heat_question_for_clarification():
    result = SemanticRouter().route("这个热处理怎么样")

    assert result.domain == "heat_treatment"
    assert result.intent == "unknown"
    assert result.need_clarification is True
    assert result.clarification_reason is not None


def test_semantic_router_normalizes_chinese_status_expressions():
    router = SemanticRouter()

    for message in ["到哪一步了", "做完了吗", "当前什么情况", "状态如何"]:
        result = router.route(message)
        assert result.domain == "heat_treatment"
        assert result.intent == "query_status"
        assert result.need_clarification is False


def test_planner_consumes_semantic_router_result_without_tool_name_selection():
    semantic_result = SemanticRouter().route("HT20260603-007热处理状态")

    plan = DebuggablePlanner().plan(
        PlannerRequest(
            user_query="HT20260603-007热处理状态",
            semantic_router_result=semantic_result,
        )
    )

    step = plan.steps[0]
    assert step.type == "tool"
    assert step.name is None
    assert step.semantic_domain == "heat_treatment"
    assert step.semantic_intent == "query_status"
    assert step.args == {"record_no": "HT20260603-007"}
    assert plan.semantic_router_result == semantic_result.model_dump(mode="json")


def test_ambiguous_semantic_result_does_not_execute_status_query():
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(
            text_to_sql_node=FakeTextToSqlNode(),
            registry=build_heat_treatment_test_registry(),
        ),
    )

    result = orchestrator.run(AgentRunInput(message="这个热处理怎么样"))

    trace = result.execution_trace[-1]
    assert result.final_result.status == "failed"
    assert result.debug["route"] == "unknown"
    assert result.plan_trace["initial_plan"]["steps"] == []
    assert trace["semantic_router_result"]["need_clarification"] is True
    assert trace["semantic_router_version"] == "v1"
    assert trace["routing_source"] == "semantic_router"
    assert trace["semantic_router_result"]["intent"] == "unknown"
    assert trace["result"]["trace"]["semantic_router_result"]["need_clarification"] is True
    assert trace["result"]["trace"]["semantic_router_version"] == "v1"
    assert trace["result"]["trace"]["routing_source"] == "semantic_router"


@pytest.mark.parametrize("case", load_golden_cases(), ids=lambda case: case["id"])
def test_semantic_router_golden_cases(case):
    result = SemanticRouter().route(case["input"])
    expected = case["expected"]

    if "semantic_router_version" in expected:
        assert result.semantic_router_version == expected["semantic_router_version"]
    if "domain" in expected:
        assert result.domain == expected["domain"]
    if "intent" in expected:
        assert result.intent == expected["intent"]
    if "record_no" in expected:
        assert result.entities.get("record_no") == expected["record_no"]
    if "need_clarification" in expected:
        assert result.need_clarification is expected["need_clarification"]
    if "clarification_reason_contains" in expected:
        assert result.clarification_reason is not None
        assert expected["clarification_reason_contains"] in result.clarification_reason
