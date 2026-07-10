import logging

from app.agent.orchestrator.agent_orchestrator import (
    AgentOrchestrator,
    AgentRunInput,
    PlanExecutionAdapter,
)
from app.agent.planner.planner import DebuggablePlanner
from tests.heat_tool_test_utils import build_heat_treatment_test_registry
from tests.test_agent_orchestrator import FakeTextToSqlNode


def test_agent_lifecycle_logs_include_trace_id(caplog):
    _enable_caplog_for_agent_loggers()
    caplog.set_level(logging.DEBUG, logger="agent")
    orchestrator = _build_orchestrator()

    result = orchestrator.run(AgentRunInput(message="HT20260603-007热处理状态"))

    records = _agent_records(caplog.records)
    events = [record.event for record in records]
    assert "agent.request.start" in events
    assert "semantic_router.completed" in events
    assert "planner.completed" in events
    assert "capability.matched" in events
    assert "tool.execute.start" in events
    assert "tool.execute.completed" in events
    assert "agent.request.finished" in events

    trace_ids = {record.trace_id for record in records if record.event in events}
    assert trace_ids == {result.trace_id}


def test_sql_debug_logger_outputs_sql(caplog):
    _enable_caplog_for_agent_loggers()
    caplog.set_level(logging.INFO, logger="agent")
    caplog.set_level(logging.DEBUG, logger="agent.sql")
    orchestrator = _build_orchestrator()

    result = orchestrator.run(AgentRunInput(message="本月热处理完成多少批"))

    sql_records = [
        record
        for record in caplog.records
        if record.name == "agent.sql" and getattr(record, "event", None) == "sql.execute"
    ]
    assert result.final_result.status == "success"
    assert len(sql_records) == 1
    assert sql_records[0].trace_id == result.trace_id
    assert "mes_heat_treatment_record" in sql_records[0].fields["sql"]
    assert sql_records[0].fields["duration_ms"] == 1


def test_sql_info_logger_does_not_output_sql(caplog):
    _enable_caplog_for_agent_loggers()
    caplog.set_level(logging.INFO, logger="agent")
    caplog.set_level(logging.INFO, logger="agent.sql")
    orchestrator = _build_orchestrator()

    orchestrator.run(AgentRunInput(message="本月热处理完成多少批"))

    sql_records = [
        record
        for record in caplog.records
        if record.name == "agent.sql" and getattr(record, "event", None) == "sql.execute"
    ]
    assert sql_records == []


def _build_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator(
        DebuggablePlanner(),
        PlanExecutionAdapter(
            text_to_sql_node=FakeTextToSqlNode(),
            registry=build_heat_treatment_test_registry(),
        ),
    )


def _agent_records(records):
    return [
        record
        for record in records
        if record.name.startswith("agent") and hasattr(record, "event")
    ]


def _enable_caplog_for_agent_loggers() -> None:
    for name in [
        "agent",
        "agent.semantic_router",
        "agent.planner",
        "agent.capability_router",
        "agent.execution",
        "agent.sql",
    ]:
        logging.getLogger(name).propagate = True
