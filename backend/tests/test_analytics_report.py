from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.agent.execution_observation import (
    ExecutionObservation,
    ExecutionQuality,
    ExecutionTrace,
    ObservationFacts,
)
from app.agent.orchestrator.agent_orchestrator import AgentOrchestrator, AgentRunInput
from app.agent.planner.planner import DebuggablePlanner
from app.analytics.event.collector import AgentEventCollector
from app.analytics.metrics.snapshot import MetricsSnapshotService
from app.analytics.report.report_generator import MdReportGenerator
from app.analytics.report.repository import SqlAlchemyAnalyticsRepository
from app.analytics.report.scheduler import seconds_until_next_daily_run
from app.api.analytics_report import get_report_generator
from app.main import app


class OneShotExecutionLayer:
    def execute(self, plan):
        return ExecutionObservation(
            status="success",
            data={
                "tool_result": {"status": "FINISHED"},
                "step_results": [
                    {
                        "step_id": 1,
                        "type": "tool",
                        "name": "heat_current_stage",
                        "observation": {
                            "status": "success",
                            "data": {"tool_result": {"status": "FINISHED"}},
                            "observation": {
                                "facts_found": ["heat_current_stage"],
                                "missing_facts": [],
                                "decision_signals": ["tool_executed"],
                                "failure_type": None,
                            },
                            "execution_quality": {
                                "tool_hit": True,
                                "sql_valid": None,
                                "sql_executed": None,
                            },
                            "trace": {
                                "tool_name": "heat_current_stage",
                                "sql": None,
                                "used_tables": [],
                            },
                        },
                    }
                ],
            },
            observation=ObservationFacts(facts_found=["heat_current_stage"]),
            execution_quality=ExecutionQuality(tool_hit=True),
            trace=ExecutionTrace(tool_name="heat_current_stage"),
        )


def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_analytics_tables(engine)
    seed_analytics_data(engine)
    return engine


def create_analytics_tables(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE agent_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL UNIQUE,
                    user_query TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    final_result TEXT NOT NULL,
                    status TEXT NOT NULL,
                    loop_depth INTEGER NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE agent_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    step_id INTEGER,
                    component TEXT NOT NULL,
                    input_json TEXT,
                    output_json TEXT,
                    latency_ms INTEGER,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE agent_failure (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    failure_type TEXT,
                    source_layer TEXT,
                    error_code TEXT,
                    summary TEXT NOT NULL,
                    detail_json TEXT,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE agent_metrics_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_hit_rate REAL NOT NULL,
                    sql_success_rate REAL NOT NULL,
                    replan_rate REAL NOT NULL,
                    avg_loop_depth REAL NOT NULL,
                    window_start DATETIME NOT NULL,
                    window_end DATETIME NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )


def seed_analytics_data(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO agent_trace (
                    trace_id, user_query, plan_json, final_result, status, loop_depth, created_at
                )
                VALUES
                ('raw-trace-1', 'TRACE-HTR-K2-T-FG-001到哪了', '{"intent":"tool"}', '{"status":"success"}', 'success', 1, '2026-07-06 08:00:00'),
                ('raw-trace-2', '统计本月每台设备产量', '{"intent":"sql"}', '{"status":"failed"}', 'failed', 2, '2026-07-06 09:00:00')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO agent_event (
                    event_type, trace_id, step_id, component, input_json, output_json, latency_ms, timestamp, created_at
                )
                VALUES
                ('LOOP_START', 'raw-trace-1', NULL, 'execution_loop', '{}', '{}', 0, '2026-07-06 08:00:00', '2026-07-06 08:00:00'),
                ('TOOL_MATCH', 'raw-trace-1', 1, 'heat_current_stage', '{}', '{}', 1, '2026-07-06 08:00:01', '2026-07-06 08:00:01'),
                ('TOOL_EXECUTE_SUCCESS', 'raw-trace-1', 1, 'heat_current_stage', '{}', '{}', 100, '2026-07-06 08:00:02', '2026-07-06 08:00:02'),
                ('SQL_GENERATE', 'raw-trace-2', 1, 'text_to_sql', '{}', '{}', 20, '2026-07-06 09:00:00', '2026-07-06 09:00:00'),
                ('SQL_VALIDATE', 'raw-trace-2', 1, 'text_to_sql', '{}', '{}', 20, '2026-07-06 09:00:01', '2026-07-06 09:00:01'),
                ('SQL_EXECUTE_FAIL', 'raw-trace-2', 1, 'text_to_sql', '{}', '{}', 300, '2026-07-06 09:00:02', '2026-07-06 09:00:02'),
                ('REPLAN_TRIGGER', 'raw-trace-2', NULL, 'execution_loop', '{}', '{}', 1, '2026-07-06 09:00:03', '2026-07-06 09:00:03')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO agent_failure (
                    trace_id, failure_type, source_layer, error_code, summary, detail_json, created_at
                )
                VALUES
                ('raw-trace-2', 'sql_error', 'sql', 'unknown_column', 'SQL validation failed.', '{}', '2026-07-06 09:00:04'),
                ('raw-trace-2', 'tool_miss', 'tool', 'tool_miss', 'Tool miss.', '{}', '2026-07-06 09:00:05')
                """
            )
        )


def generator_for(engine, tmp_path):
    return MdReportGenerator(
        repository=SqlAlchemyAnalyticsRepository(engine),
        report_dir=tmp_path,
    )


def test_report_generator_creates_three_markdown_reports_from_sql(tmp_path):
    generator = generator_for(sqlite_engine(), tmp_path)

    artifacts = generator.generate_daily_reports(date(2026, 7, 6))

    paths = {artifact.path for artifact in artifacts}
    assert tmp_path / "daily" / "2026-07-06.md" in paths
    assert tmp_path / "failure" / "2026-07-06.md" in paths
    assert tmp_path / "health" / "latest.md" in paths
    assert "# Agent System Daily Report" in (tmp_path / "daily" / "2026-07-06.md").read_text()
    assert "# Failure Analysis Report" in (tmp_path / "failure" / "2026-07-06.md").read_text()
    assert "# System Health Report" in (tmp_path / "health" / "latest.md").read_text()


def test_report_generation_is_idempotent_and_excludes_raw_trace_ids(tmp_path):
    generator = generator_for(sqlite_engine(), tmp_path)

    first = generator.generate("daily", date(2026, 7, 6))
    second = generator.generate("daily", date(2026, 7, 6))

    assert first.path == second.path
    assert first.content == second.content
    assert "raw-trace-1" not in second.content
    assert "total_requests: 2" in second.content
    assert "success_rate: 0.5" in second.content
    assert "tool_hit_rate: 1.0" in second.content
    assert "sql_success_rate: 0.0" in second.content


def test_report_generate_api_uses_sql_repository(tmp_path):
    generator = generator_for(sqlite_engine(), tmp_path)
    app.dependency_overrides[get_report_generator] = lambda: generator
    client = TestClient(app)

    response = client.post("/api/analytics/report/generate", json={"type": "health"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "health"
    assert payload["status"] == "generated"
    assert payload["path"].endswith("health/latest.md")
    assert payload["metrics"]["total_requests"] == 2


def test_trace_replay_reads_agent_trace_by_trace_id(tmp_path):
    generator = generator_for(sqlite_engine(), tmp_path)
    app.dependency_overrides[get_report_generator] = lambda: generator
    client = TestClient(app)

    response = client.get("/api/analytics/report/traces/raw-trace-1")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"] == "raw-trace-1"
    assert payload["plan_json"] == {"intent": "tool"}


def test_metrics_snapshot_uses_sql_and_writes_snapshot():
    engine = sqlite_engine()
    service = MetricsSnapshotService(engine)

    snapshot = service.create_snapshot(
        window_start=datetime(2026, 7, 6, 0, 0, 0),
        window_end=datetime(2026, 7, 7, 0, 0, 0),
    )

    assert snapshot["tool_hit_rate"] == 1.0
    assert snapshot["sql_success_rate"] == 0.0
    assert snapshot["replan_rate"] == 0.5
    assert snapshot["avg_loop_depth"] == 1.5
    with engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM agent_metrics_snapshot")).scalar_one()
    assert count == 1


def test_event_collector_writes_event_trace_and_failure_to_sql():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_analytics_tables(engine)
    collector = AgentEventCollector(engine)

    collector.record_event(
        event_type="PLANNER_START",
        trace_id="trace-new",
        component="planner",
        input_json={"message": "hello"},
    )
    collector.record_trace(
        trace_id="trace-new",
        user_query="hello",
        plan_json={"intent": "unknown"},
        final_result={"status": "failed"},
        status="failed",
        loop_depth=1,
    )
    collector.record_failure(
        trace_id="trace-new",
        failure_type="missing_param",
        source_layer="planner",
        error_code="planner_error",
        summary="missing params",
    )

    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM agent_event")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM agent_trace")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM agent_failure")).scalar_one() == 1


def test_orchestrator_records_execution_events_and_trace_to_sql():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    create_analytics_tables(engine)
    orchestrator = AgentOrchestrator(
        planner=DebuggablePlanner(),
        execution_layer=OneShotExecutionLayer(),
        event_collector=AgentEventCollector(engine),
    )

    result = orchestrator.run(AgentRunInput(message="TRACE-HTR-K2-T-FG-001到哪了"))

    with engine.connect() as connection:
        event_types = [
            row[0]
            for row in connection.execute(
                text("SELECT event_type FROM agent_event ORDER BY id ASC")
            ).all()
        ]
        trace_count = connection.execute(text("SELECT COUNT(*) FROM agent_trace")).scalar_one()
    assert result.final_result.status == "success"
    assert "PLANNER_START" in event_types
    assert "PLANNER_END" in event_types
    assert "TOOL_MATCH" in event_types
    assert "TOOL_EXECUTE_SUCCESS" in event_types
    assert "LOOP_START" in event_types
    assert "LOOP_END" in event_types
    assert trace_count == 1


def test_report_generate_api_rejects_unknown_type():
    client = TestClient(app)

    response = client.post("/api/analytics/report/generate", json={"type": "weekly"})

    assert response.status_code == 422


def test_scheduler_calculates_next_0010_run():
    before_run = datetime(2026, 7, 6, 0, 0, 0)
    after_run = datetime(2026, 7, 6, 0, 11, 0)

    assert seconds_until_next_daily_run(before_run) == 600
    assert seconds_until_next_daily_run(after_run) == 86340
