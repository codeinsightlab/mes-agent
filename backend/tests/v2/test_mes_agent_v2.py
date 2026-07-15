from app.agent.agents.heat_treatment import HeatTreatmentAgent
from app.agent.capability.catalog.loader import CapabilityLoader
from app.agent.core import AgentRequest, AgentRouter, MesAgent
from app.agent.execution import ExecutionEngine
from app.agent.reasoning import CapabilityReasoner
from app.agent.runtime import CapabilityRuntime, LlmRuntime, TraceRuntime


class RecordingAuditRuntime:
    def __init__(self):
        self.records = []

    def record(self, request, response):
        self.records.append((request, response))


class RecordingReasoningAudit:
    def __init__(self):
        self.records = []

    def record(self, audit):
        self.records.append(audit)


class FakeBusinessReasoningModel:
    def with_structured_output(self, output_type):
        return self

    def invoke(self, prompt):
        user_input = prompt.split("用户问题：", 1)[1].split("MES Capability Catalog：", 1)[0].strip()
        if "什么状态" in user_input:
            return {
                "goal": "查询热处理当前状态",
                "domain": "heat_treatment",
                "selected_capability": {
                    "name": "heat_current_stage",
                    "reason": "用户询问当前状态",
                },
                "entities": {"record_no": "TRACE-HTR-B-H-001"},
                "confidence": 0.95,
                "need_clarification": False,
                "clarification_reason": None,
            }
        if "炉子" in user_input:
            return {
                "goal": "查询热处理执行设备",
                "domain": "heat_treatment",
                "selected_capability": {
                    "name": "heat_device_trace",
                    "reason": "用户询问指定记录使用的炉子",
                },
                "entities": {"record_no": "TRACE-HTR-B-H-001"},
                "confidence": 0.94,
                "need_clarification": False,
                "clarification_reason": None,
            }
        if "完成多少批" in user_input:
            return {
                "goal": "统计本月热处理完成批次",
                "domain": "heat_treatment",
                "selected_capability": {
                    "name": "heat_completion_count_monthly",
                    "reason": "用户明确询问本月完成批次",
                },
                "entities": {"time_range": "current_month"},
                "confidence": 0.96,
                "need_clarification": False,
                "clarification_reason": None,
            }
        return {
            "goal": "无法确定",
            "domain": "heat_treatment",
            "selected_capability": None,
            "entities": {},
            "confidence": 0.2,
            "need_clarification": True,
            "clarification_reason": "用户未说明需要查询的业务信息",
        }


def build_mes_agent():
    registry = CapabilityLoader().load()
    trace_runtime = TraceRuntime()
    executions = []

    def current_stage(arguments):
        executions.append(("heat_current_stage", arguments))
        return {"found": True, "record_no": arguments["record_no"], "status": "RUNNING"}

    def monthly_count(arguments):
        executions.append(("heat_completion_count_monthly", arguments))
        return {"rows": [{"completed_count": 7}], "row_count": 1, "validated_sql": "SELECT COUNT(*)"}

    runtime = CapabilityRuntime(
        registry,
        ExecutionEngine({"heat_current_stage": current_stage, "text_to_sql": monthly_count}),
    )
    reasoning_audit = RecordingReasoningAudit()
    domain_agent = HeatTreatmentAgent(
        CapabilityReasoner(
            registry,
            LlmRuntime(FakeBusinessReasoningModel()),
            reasoning_audit,
        ),
        runtime,
        trace_runtime,
    )
    audit = RecordingAuditRuntime()
    return (
        MesAgent(AgentRouter(domain_agent), trace_runtime, audit),
        executions,
        audit,
        reasoning_audit,
    )


def test_heat_status_runs_full_v2_chain():
    agent, executions, audit, reasoning_audit = build_mes_agent()

    result = agent.run(AgentRequest(message="TRACE-HTR-B-H-001什么状态"))

    assert result.status == "success"
    assert result.agent == "heat_treatment_agent"
    assert result.capability == "heat_current_stage"
    assert executions == [("heat_current_stage", {"record_no": "TRACE-HTR-B-H-001"})]
    assert [event["stage"] for event in result.trace] == [
        "request", "agent_router", "reasoning", "capability", "execution", "result"
    ]
    assert len(audit.records) == 1
    assert reasoning_audit.records[0].prompt_version == "capability-reasoning-v2"
    assert reasoning_audit.records[0].selected_capability == "heat_current_stage"
    assert reasoning_audit.records[0].business_fact_version == "heat-treatment-business-facts-v1"


def test_heat_device_contract_is_routed_but_not_executed_while_planned():
    agent, executions, audit, _ = build_mes_agent()

    result = agent.run(AgentRequest(message="TRACE-HTR-B-H-001在哪个炉子完成"))

    assert result.status == "clarification_required"
    assert result.capability == "heat_device_trace"
    assert "planned" in (result.clarification or "")
    assert executions == []
    assert len(audit.records) == 1


def test_heat_monthly_statistics_runs_shared_execution_runtime():
    agent, executions, _, _ = build_mes_agent()

    result = agent.run(AgentRequest(message="本月热处理完成多少批"))

    assert result.status == "success"
    assert result.capability == "heat_completion_count_monthly"
    assert result.data["rows"] == [{"completed_count": 7}]
    assert executions[0][0] == "heat_completion_count_monthly"
    assert executions[0][1]["time_range"] == "current_month"


def test_ambiguous_heat_question_requires_clarification_without_execution():
    agent, executions, audit, _ = build_mes_agent()

    result = agent.run(AgentRequest(message="这个热处理怎么样"))

    assert result.status == "clarification_required"
    assert result.capability is None
    assert result.clarification
    assert executions == []
    assert len(audit.records) == 1


def test_agent_router_is_fixed_but_accepts_request_for_future_extension():
    agent, _, _, _ = build_mes_agent()
    domain_agent = agent._router.route(AgentRequest(message="任意输入"))

    assert domain_agent.name == "heat_treatment_agent"
