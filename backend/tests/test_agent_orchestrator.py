from app.agent.execution_observation import (
    ExecutionObservation,
    ExecutionQuality,
    ExecutionTrace,
    ObservationFacts,
)
from app.agent.orchestrator.agent_orchestrator import (
    AgentOrchestrator,
    AgentRunInput,
    PlanExecutionAdapter,
)
from app.agent.tools.registry import DEFAULT_TOOL_REGISTRY
from app.agent.planner.models import PlannerPlan, PlanStep, ExecutionPlanPolicy, DebugTrace
from app.agent.planner.planner import DebuggablePlanner
from tests.heat_tool_test_utils import build_heat_treatment_test_registry


class SequenceExecutionLayer:
    def __init__(self, observations):
        self.observations = list(observations)
        self.calls = []

    def execute(self, plan):
        self.calls.append(plan)
        return self.observations.pop(0)


def observation(status="success", missing_facts=None, failure_type=None, data=None):
    return ExecutionObservation(
        status=status,
        data=data or {"value": "ok"},
        observation=ObservationFacts(
            facts_found=["result"] if status == "success" else [],
            missing_facts=missing_facts or [],
            decision_signals=[],
            failure_type=failure_type,
        ),
        execution_quality=ExecutionQuality(tool_hit=True, sql_valid=True, sql_executed=True),
        trace=ExecutionTrace(tool_name="heat_current_stage"),
    )


def test_orchestrator_returns_unified_success_result_without_replan():
    execution_layer = SequenceExecutionLayer([observation(data={"status": "FINISHED"})])
    orchestrator = AgentOrchestrator(DebuggablePlanner(), execution_layer)

    result = orchestrator.run(AgentRunInput(message="TRACE-HTR-K2-T-FG-001到哪了"))

    assert result.trace_id
    assert result.plan_trace["initial_plan"]["intent"] == "tool"
    assert result.plan_trace["replan"] is None
    assert len(result.execution_trace) == 1
    assert result.final_result.status == "success"
    assert result.debug["route"] == "tool"
    assert result.debug["execution_summary"]["planner_calls"] == 1
    assert result.debug["execution_summary"]["execution_loops"] == 1


def test_orchestrator_replans_once_for_partial_missing_facts():
    execution_layer = SequenceExecutionLayer(
        [
            observation(status="partial", missing_facts=["factory"], failure_type="missing_param"),
            observation(status="success", data={"rows": [{"factory": "A", "qty": 10}]}),
        ]
    )
    orchestrator = AgentOrchestrator(DebuggablePlanner(), execution_layer)

    result = orchestrator.run(AgentRunInput(message="统计本月设备产量，但未指定工厂"))

    assert result.final_result.status == "success"
    assert result.plan_trace["replan"] is not None
    assert len(result.execution_trace) == 2
    assert result.debug["execution_summary"]["planner_calls"] == 2
    assert result.debug["execution_summary"]["execution_loops"] == 2
    assert execution_layer.calls[1].steps[0].args["focus"] == "factory_filter"


def test_orchestrator_normalizes_tool_error():
    execution_layer = SequenceExecutionLayer(
        [observation(status="fail", missing_facts=[], failure_type="tool_miss")]
    )
    orchestrator = AgentOrchestrator(DebuggablePlanner(), execution_layer)

    result = orchestrator.run(AgentRunInput(message="为什么这批产品不能入库？"))

    assert result.final_result.status == "failed"
    assert result.final_result.error is not None
    assert result.final_result.error.error_type == "tool_error"
    assert result.final_result.error.recoverable is True
    assert result.debug["failure_analysis"]["source_layer"] == "tool"


def test_plan_execution_adapter_runs_tool_step_with_registry():
    adapter = PlanExecutionAdapter(
        text_to_sql_node=FakeTextToSqlNode(),
        registry=build_heat_treatment_test_registry(),
    )
    plan = PlannerPlan(
        intent="tool",
        goal="查询热处理状态",
        steps=[
            PlanStep(
                step_id=1,
                type="tool",
                name="heat_current_stage",
                query_goal="查询状态",
                args={"record_no": "TRACE-HTR-K2-T-FG-001"},
                reason="测试 Tool 执行",
                dependency=[],
                expected_output="status",
            )
        ],
        execution_plan=ExecutionPlanPolicy(stop_condition="done"),
        confidence=0.9,
        debug_trace=DebugTrace(
            classification_reason="test",
            tool_selection_reason="test",
            sql_intent_reason="test",
            risk_assessment="test",
        ),
    )

    observation = adapter.execute(plan)

    assert observation.status == "success"
    tool_result = observation.data["last_result"]["tool_result"]
    assert tool_result["status"] == "FINISHED"
    assert observation.execution_quality.tool_hit is True
    assert observation.execution_quality.sql_valid is True
    assert observation.execution_quality.sql_executed is True
    assert observation.trace.sql is not None
    assert observation.trace.used_tables == ["mes_heat_treatment_record"]
    assert observation.trace.sql_executed is True


def test_plan_execution_adapter_runs_sql_step_with_text_to_sql_node():
    adapter = PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode())
    plan = PlannerPlan(
        intent="sql",
        goal="统计",
        steps=[
            PlanStep(
                step_id=1,
                type="sql",
                name=None,
                query_goal="统计设备产量",
                args={"question": "统计本月每台设备产量"},
                reason="测试 SQL 执行",
                dependency=[],
                expected_output="rows",
            )
        ],
        execution_plan=ExecutionPlanPolicy(stop_condition="done"),
        confidence=0.9,
        debug_trace=DebugTrace(
            classification_reason="test",
            tool_selection_reason="test",
            sql_intent_reason="test",
            risk_assessment="test",
        ),
    )

    observation = adapter.execute(plan)

    assert observation.status == "success"
    assert observation.data["last_result"]["rows"] == [{"equipment_name": "A", "qty": 10}]
    assert observation.trace.used_tables == ["mes_heat_treatment_record"]


def test_agent_run_executes_known_tool_with_record_no_once_without_replan():
    registry = SpyRegistry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode(), registry=registry),
    )

    result = orchestrator.run(AgentRunInput(message="TRACE-HTR-K2-T-FG-001现在在哪一步"))

    step = result.plan_trace["initial_plan"]["steps"][0]
    assert result.final_result.status == "success"
    assert result.debug["route"] == "tool"
    assert result.debug["execution_summary"]["replanned"] is False
    assert result.debug["execution_summary"]["planner_calls"] == 1
    assert step["name"] is None
    assert step["semantic_domain"] == "heat_treatment"
    assert step["semantic_intent"] == "query_status"
    assert step["args"]["record_no"] == "TRACE-HTR-K2-T-FG-001"
    assert registry.calls == [
        ("heat_current_stage", {"record_no": "TRACE-HTR-K2-T-FG-001"})
    ]
    assert result.final_result.error is None
    trace = result.execution_trace[-1]["result"]["trace"]
    assert trace["capability_source"] == "catalog"
    assert trace["capability_name"] == "heat_current_stage"
    assert trace["catalog_version"] == "v1"
    assert trace["tool_name"] == "heat_current_stage"
    assert trace["sql_executed"] is True
    assert trace["used_tables"] == ["mes_heat_treatment_record"]


def test_agent_run_executes_real_heat_current_stage_repository_trace():
    registry = SpyRegistry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode(), registry=registry),
    )

    result = orchestrator.run(AgentRunInput(message="HT20260603-007热处理的状态"))

    step = result.plan_trace["initial_plan"]["steps"][0]
    trace = result.execution_trace[-1]["result"]["trace"]
    tool_result = result.final_result.data["last_result"]["tool_result"]
    assert result.final_result.status == "success"
    assert result.debug["route"] == "tool"
    assert step["name"] is None
    assert step["semantic_domain"] == "heat_treatment"
    assert step["semantic_intent"] == "query_status"
    assert step["args"]["record_no"] == "HT20260603-007"
    assert tool_result == {
        "found": True,
        "record_no": "HT20260603-007",
        "status": "RUNNING",
        "status_name": "进行中",
    }
    assert trace["sql_executed"] is True
    assert trace["capability_name"] == "heat_current_stage"
    assert trace["catalog_version"] == "v1"
    assert trace["tool_name"] == "heat_current_stage"
    assert trace["used_tables"] == ["mes_heat_treatment_record"]
    assert trace["sql"].startswith("SELECT record_no, status")


def test_agent_run_returns_not_found_without_mock_fallback():
    registry = SpyRegistry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode(), registry=registry),
    )

    result = orchestrator.run(AgentRunInput(message="HT99999999热处理状态"))

    tool_result = result.final_result.data["last_result"]["tool_result"]
    trace = result.execution_trace[-1]["result"]["trace"]
    assert result.final_result.status == "success"
    assert tool_result == {
        "found": False,
        "record_no": "HT99999999",
        "status": None,
        "status_name": None,
    }
    assert trace["sql_executed"] is True
    assert trace["error_type"] == "not_found"


def test_agent_run_missing_tool_parameter_does_not_execute_tool_or_enter_sql():
    registry = SpyRegistry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode(), registry=registry),
    )

    result = orchestrator.run(AgentRunInput(message="这个热处理现在到哪一步"))

    assert registry.calls == []
    assert result.final_result.status == "partial"
    assert result.final_result.error is not None
    assert result.final_result.error.error_type == "planner_error"
    assert "缺少热处理记录标识" in result.final_result.error.message
    assert result.debug["route"] == "tool"
    assert result.debug["execution_summary"]["execution_loops"] == 2
    assert result.execution_trace[-1]["result"]["trace"]["tool_name"] == "heat_current_stage"
    assert result.execution_trace[-1]["result"]["trace"]["sql"] is None


def test_agent_run_rejects_planned_mock_tools_without_execution():
    registry = SpyRegistry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode(), registry=registry),
    )

    equipment = orchestrator.run(AgentRunInput(message="TRACE-HTR-K2-T-FG-001分配到了哪个炉子"))
    batch = orchestrator.run(AgentRunInput(message="TRACE-HTR-K2-T-FG-001包含哪些批次"))

    assert equipment.final_result.status == "failed"
    assert batch.final_result.status == "failed"
    assert equipment.debug["failure_analysis"]["failure_type"] == "tool_miss"
    assert batch.debug["failure_analysis"]["failure_type"] == "tool_miss"
    assert registry.calls == []


def test_agent_run_sql_path_remains_text_to_sql_and_cross_request_isolated():
    registry = SpyRegistry()
    orchestrator = AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(text_to_sql_node=FakeTextToSqlNode(), registry=registry),
    )

    tool = orchestrator.run(AgentRunInput(message="TRACE-HTR-K2-T-FG-001现在在哪一步"))
    missing = orchestrator.run(AgentRunInput(message="这个热处理现在到哪一步"))
    sql = orchestrator.run(AgentRunInput(message="统计本月每台热处理设备处理了多少批次"))

    assert len({tool.trace_id, missing.trace_id, sql.trace_id}) == 3
    assert tool.debug["route"] == "tool"
    assert missing.debug["route"] == "tool"
    assert sql.debug["route"] == "sql"
    assert sql.final_result.status == "success"
    assert registry.calls == [
        ("heat_current_stage", {"record_no": "TRACE-HTR-K2-T-FG-001"})
    ]


class FakeTextToSqlNode:
    def __call__(self, state):
        return {
            **state,
            "tool_result": {
                "route": "text_to_sql",
                "status": "success",
                "generated_sql": "SELECT equipment_name, 10 AS qty FROM mes_heat_treatment_record LIMIT 100",
                "validated_sql": "SELECT equipment_name, 10 AS qty FROM mes_heat_treatment_record LIMIT 100",
                "used_tables": ["mes_heat_treatment_record"],
                "columns": ["equipment_name", "qty"],
                "rows": [{"equipment_name": "A", "qty": 10}],
                "row_count": 1,
                "duration_ms": 1,
                "error": None,
                "schema_version": "heat-treatment-schema-v1",
                "query_intent": "test",
                "assumptions": [],
            },
        }


class SpyRegistry:
    def __init__(self):
        self.calls = []
        self._registry = build_heat_treatment_test_registry()

    def get_capability(self, name):
        return DEFAULT_TOOL_REGISTRY.get_capability(name)

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return self._registry.execute(name, arguments)

    def last_trace(self):
        return self._registry.last_trace()
