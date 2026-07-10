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
    domain_agent = HeatTreatmentAgent(
        CapabilityReasoner(registry, LlmRuntime()),
        runtime,
        trace_runtime,
    )
    audit = RecordingAuditRuntime()
    return MesAgent(AgentRouter(domain_agent), trace_runtime, audit), executions, audit


def test_heat_status_runs_full_v2_chain():
    agent, executions, audit = build_mes_agent()

    result = agent.run(AgentRequest(message="TRACE-HTR-B-H-001什么状态"))

    assert result.status == "success"
    assert result.agent == "heat_treatment_agent"
    assert result.capability == "heat_current_stage"
    assert executions == [("heat_current_stage", {"record_no": "TRACE-HTR-B-H-001"})]
    assert [event["stage"] for event in result.trace] == [
        "request", "agent_router", "reasoning", "capability", "execution", "result"
    ]
    assert len(audit.records) == 1


def test_heat_device_contract_is_routed_but_not_executed_while_planned():
    agent, executions, audit = build_mes_agent()

    result = agent.run(AgentRequest(message="TRACE-HTR-B-H-001在哪个炉子完成"))

    assert result.status == "clarification_required"
    assert result.capability == "heat_device_trace"
    assert "planned" in (result.clarification or "")
    assert executions == []
    assert len(audit.records) == 1


def test_heat_monthly_statistics_runs_shared_execution_runtime():
    agent, executions, _ = build_mes_agent()

    result = agent.run(AgentRequest(message="本月热处理完成多少批"))

    assert result.status == "success"
    assert result.capability == "heat_completion_count_monthly"
    assert result.data["rows"] == [{"completed_count": 7}]
    assert executions[0][0] == "heat_completion_count_monthly"
    assert executions[0][1]["time_range"] == "current_month"


def test_ambiguous_heat_question_requires_clarification_without_execution():
    agent, executions, audit = build_mes_agent()

    result = agent.run(AgentRequest(message="这个热处理怎么样"))

    assert result.status == "clarification_required"
    assert result.capability is None
    assert result.clarification
    assert executions == []
    assert len(audit.records) == 1


def test_agent_router_is_fixed_but_accepts_request_for_future_extension():
    agent, _, _ = build_mes_agent()
    domain_agent = agent._router.route(AgentRequest(message="任意输入"))

    assert domain_agent.name == "heat_treatment_agent"
