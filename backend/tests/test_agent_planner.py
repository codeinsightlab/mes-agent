from app.agent.execution_observation import ExecutionObservation, ObservationFacts
from app.agent.planner.models import ExecutionHistoryItem, PlannerRequest
from app.agent.planner.planner import DebuggablePlanner


def plan_for(message, history=None):
    return DebuggablePlanner().plan(
        PlannerRequest(
            user_query=message,
            execution_history=history or [],
        )
    )


def test_planner_single_tool_query_creates_executable_tool_step():
    plan = plan_for("TRACE-HTR-K2-T-FG-001现在在哪一步")

    assert plan.intent == "tool"
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.type == "tool"
    assert step.name == "heat_current_stage"
    assert step.args == {"record_no": "TRACE-HTR-K2-T-FG-001"}
    assert step.reason
    assert plan.debug_trace.tool_selection_reason


def test_planner_equipment_tool_query_creates_equipment_step():
    plan = plan_for("TRACE-HTR-K2-T-FG-001分配到了哪个炉子")

    assert plan.intent == "tool"
    step = plan.steps[0]
    assert step.name == "heat_equipment_assignment"
    assert step.args == {"record_no": "TRACE-HTR-K2-T-FG-001"}


def test_planner_completion_query_with_furnace_word_keeps_current_stage_tool():
    plan = plan_for("这个炉子处理完了吗 TRACE-HTR-K2-T-FG-001")

    assert plan.intent == "tool"
    step = plan.steps[0]
    assert step.name == "heat_current_stage"
    assert step.args == {"record_no": "TRACE-HTR-K2-T-FG-001"}


def test_planner_batch_tool_query_creates_batch_step():
    plan = plan_for("TRACE-HTR-K2-T-FG-001包含哪些批次")

    assert plan.intent == "tool"
    step = plan.steps[0]
    assert step.name == "heat_batch_products"
    assert step.args == {"record_no": "TRACE-HTR-K2-T-FG-001"}


def test_planner_sql_query_creates_single_sql_step():
    plan = plan_for("统计本月每台设备产量")

    assert plan.intent == "sql"
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.type == "sql"
    assert step.name is None
    assert step.args == {"question": "统计本月每台设备产量"}
    assert "Text-to-SQL" in step.reason
    assert plan.execution_plan.stop_condition


def test_planner_mixed_diagnostic_query_exposes_capability_gaps():
    plan = plan_for("为什么这批产品不能入库？")

    assert plan.intent == "mixed"
    assert [step.type for step in plan.steps] == ["tool", "tool", "sql"]
    assert [step.name for step in plan.steps] == ["production_status", "quality_status", None]
    assert len(plan.steps) <= 5
    assert "未注册" in plan.debug_trace.risk_assessment


def test_planner_uses_execution_history_for_reuse_hint():
    plan = plan_for(
        "TRACE-HTR-K2-T-FG-001到哪了",
        history=[
            ExecutionHistoryItem(
                step=1,
                route="tool",
                input="TRACE-HTR-K2-T-FG-001到哪了",
                output={"status": "FINISHED"},
                status="success",
            )
        ],
    )

    assert plan.steps[0].reuse_from_history == 1
    assert plan.steps[0].skip_reason


def test_planner_maps_failed_sql_history_to_execution_source():
    plan = plan_for(
        "统计本月每台设备产量",
        history=[
            ExecutionHistoryItem(
                step=1,
                route="text_to_sql",
                input="统计本月每台设备产量",
                output={"error": "database timeout"},
                status="failed",
            )
        ],
    )

    assert plan.failure_analysis
    assert plan.failure_analysis[0].source == "execution"


def test_replan_keeps_tool_missing_args_out_of_sql_fallback():
    plan = DebuggablePlanner().plan(
        PlannerRequest(
            user_query="状态？",
            execution_observation=ExecutionObservation(
                status="fail",
                observation=ObservationFacts(
                    missing_facts=["heat_current_stage.args"],
                    failure_type="missing_param",
                ),
            ),
        )
    )

    assert plan.intent == "tool"
    assert plan.steps[0].type == "tool"
    assert plan.steps[0].name == "heat_current_stage"
    assert plan.steps[0].args == {}
    assert "不能用 SQL 兜底" in plan.debug_trace.sql_intent_reason


def test_replan_keeps_unknown_missing_steps_out_of_sql_fallback():
    plan = DebuggablePlanner().plan(
        PlannerRequest(
            user_query="aaa???!!!",
            execution_observation=ExecutionObservation(
                status="fail",
                observation=ObservationFacts(
                    missing_facts=["plan.steps"],
                    failure_type="missing_param",
                ),
            ),
        )
    )

    assert plan.intent == "unknown"
    assert plan.steps == []
    assert "没有可执行 step" in plan.debug_trace.classification_reason
