from app.agent.execution_loop import ExecutionFeedbackLoop, classify_failure
from app.agent.execution_observation import (
    ExecutionObservation,
    ExecutionQuality,
    ExecutionTrace,
    ObservationFacts,
)
from app.agent.planner.models import PlannerRequest
from app.agent.planner.planner import DebuggablePlanner


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
        data=data or {},
        observation=ObservationFacts(
            facts_found=[] if missing_facts else ["result"],
            missing_facts=missing_facts or [],
            decision_signals=[],
            failure_type=failure_type,
        ),
        execution_quality=ExecutionQuality(
            tool_hit=True,
            sql_valid=True,
            sql_executed=status == "success",
        ),
        trace=ExecutionTrace(tool_name="heat_current_stage", used_tables=[]),
    )


def test_loop_does_not_replan_when_tool_execution_is_complete():
    execution_layer = SequenceExecutionLayer([observation(data={"status": "FINISHED"})])
    loop = ExecutionFeedbackLoop(DebuggablePlanner(), execution_layer)

    result = loop.run(PlannerRequest(user_query="TRACE-HTR-K2-T-FG-001到哪了"))

    assert result.status == "success"
    assert result.attempts == 1
    assert len(execution_layer.calls) == 1
    assert result.initial_plan.intent == "tool"
    assert result.final_plan == result.initial_plan


def test_loop_replans_once_when_sql_observation_is_partial():
    execution_layer = SequenceExecutionLayer(
        [
            observation(status="partial", missing_facts=["factory"], failure_type="missing_param"),
            observation(status="success", data={"rows": [{"factory": "A", "qty": 10}]}),
        ]
    )
    loop = ExecutionFeedbackLoop(DebuggablePlanner(), execution_layer)

    result = loop.run(PlannerRequest(user_query="统计本月设备产量，但未指定工厂"))

    assert result.status == "success"
    assert result.attempts == 2
    assert len(execution_layer.calls) == 2
    assert result.initial_plan.intent == "sql"
    assert result.final_plan.intent == "sql"
    assert result.final_plan.steps[0].args["focus"] == "factory_filter"


def test_loop_replans_mixed_diagnostic_to_qc_focus():
    execution_layer = SequenceExecutionLayer(
        [
            observation(status="partial", missing_facts=["QC"], failure_type="tool_miss"),
            observation(status="fail", missing_facts=["QC"], failure_type="tool_miss"),
        ]
    )
    loop = ExecutionFeedbackLoop(DebuggablePlanner(), execution_layer)

    result = loop.run(PlannerRequest(user_query="为什么这批产品不能入库？"))

    assert result.attempts == 2
    assert result.initial_plan.intent == "mixed"
    assert result.final_plan.intent == "tool"
    assert result.final_plan.steps[0].name == "quality_status"
    assert result.failure_report is not None
    assert result.failure_report.failure_type == "tool_miss"
    assert result.failure_report.source_layer == "tool"


def test_failure_classification_report_maps_execution_error():
    report = classify_failure(
        observation(status="fail", missing_facts=[], failure_type="execution_error")
    )

    assert report is not None
    assert report.source_layer == "execution"
    assert report.failure_type == "execution_error"
