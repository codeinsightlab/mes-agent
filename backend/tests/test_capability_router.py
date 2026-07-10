import textwrap

from app.agent.capability.loader import CapabilityLoader
from app.agent.capability.router import CapabilityRouter, SemanticIntent
from app.agent.orchestrator.agent_orchestrator import (
    AgentOrchestrator,
    AgentRunInput,
    PlanExecutionAdapter,
)
from app.agent.planner.planner import DebuggablePlanner
from tests.heat_tool_test_utils import build_heat_treatment_test_registry
from tests.test_agent_orchestrator import FakeTextToSqlNode


def write_catalog(tmp_path, body: str):
    definitions_dir = tmp_path / "definitions"
    definitions_dir.mkdir()
    catalog_path = definitions_dir / "test.yaml"
    catalog_path.write_text(textwrap.dedent(body), encoding="utf-8")
    return definitions_dir


def test_router_matches_heat_status_intent_to_catalog_capability():
    router = CapabilityRouter(CapabilityLoader().load())

    plan = router.route(
        SemanticIntent(
            domain="heat_treatment",
            intent="query_status",
            entity_type="heat_record",
            arguments={"record_no": "HT20260603-007"},
        )
    )

    assert plan.status == "matched"
    assert plan.capability == "heat_current_stage"
    assert plan.execution_type == "tool"
    assert plan.executor == "heat_current_stage"
    assert plan.arguments == {"record_no": "HT20260603-007"}
    assert plan.capability_source == "catalog"
    assert plan.catalog_version == "v2"


def test_router_returns_not_found_for_uncataloged_intent_without_guessing():
    router = CapabilityRouter(CapabilityLoader().load())

    plan = router.route(
        SemanticIntent(
            domain="heat_treatment",
            intent="query_equipment",
            entity_type="heat_record",
            arguments={"record_no": "HT20260603-007"},
        )
    )

    assert plan.status == "capability_not_found"
    assert plan.capability is None
    assert plan.executor is None
    assert plan.arguments == {"record_no": "HT20260603-007"}
    assert plan.catalog_version == "v2"


def test_router_matches_heat_analysis_sql_capability():
    router = CapabilityRouter(CapabilityLoader().load())

    plan = router.route(
        SemanticIntent(
            domain="heat_treatment",
            intent="analyze_completion_count",
            arguments={"question": "本月热处理完成多少批", "time_range": "current_month"},
        )
    )

    assert plan.status == "matched"
    assert plan.capability == "heat_completion_count_monthly"
    assert plan.execution_type == "readonly_sql"
    assert plan.executor == "text_to_sql"
    assert plan.catalog_version == "v2"


def test_router_blocks_planned_catalog_capability_before_execution(tmp_path):
    definitions_dir = write_catalog(
        tmp_path,
        """
        capabilities:
          - name: planned_heat_status
            domain: heat_treatment
            description: planned heat status capability
            intent:
              - query_status
            status: planned
            execution_type: tool
            executor: heat_current_stage
            input_schema:
              required:
                - record_no
            output_schema:
              required:
                - found
        """,
    )
    registry = CapabilityLoader(
        definitions_dir,
        executor_names={"heat_current_stage"},
    ).load()
    router = CapabilityRouter(registry)

    plan = router.route(
        SemanticIntent(
            domain="heat_treatment",
            intent="query_status",
            arguments={"record_no": "HT20260603-007"},
        )
    )

    assert plan.status == "capability_not_executable"
    assert plan.capability == "planned_heat_status"
    assert plan.executor == "heat_current_stage"


def test_planner_router_tool_registry_repository_sql_chain_succeeds():
    registry = build_heat_treatment_test_registry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(
            text_to_sql_node=FakeTextToSqlNode(),
            registry=registry,
        ),
    )

    result = orchestrator.run(AgentRunInput(message="HT20260603-007热处理的状态"))

    step = result.plan_trace["initial_plan"]["steps"][0]
    trace = result.execution_trace[-1]["result"]["trace"]
    tool_result = result.final_result.data["last_result"]["tool_result"]
    assert result.final_result.status == "success"
    assert step["name"] is None
    assert step["semantic_domain"] == "heat_treatment"
    assert step["semantic_intent"] == "query_status"
    assert trace["capability_source"] == "catalog"
    assert trace["capability_name"] == "heat_current_stage"
    assert trace["catalog_version"] == "v2"
    assert trace["tool_name"] == "heat_current_stage"
    assert trace["sql"].startswith("SELECT record_no, status")
    assert trace["used_tables"] == ["mes_heat_treatment_record"]
    assert tool_result["record_no"] == "HT20260603-007"
    assert tool_result["status"] == "RUNNING"
