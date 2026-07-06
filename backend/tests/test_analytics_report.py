from datetime import date, datetime

from fastapi.testclient import TestClient

from app.analytics.report.models import AnalyticsRawData
from app.analytics.report.report_generator import MdReportGenerator
from app.analytics.report.scheduler import seconds_until_next_daily_run
from app.api.analytics_report import get_report_generator
from app.main import app


class FakeAnalyticsRepository:
    def fetch_window(self, window):
        return AnalyticsRawData(
            traces=[
                {
                    "trace_id": "raw-trace-1",
                    "status": "success",
                    "route": "tool",
                    "tool_name": "heat_current_stage",
                    "latency_ms": 100,
                    "replanned": False,
                    "execution_loops": 1,
                },
                {
                    "trace_id": "raw-trace-2",
                    "status": "failed",
                    "route": "text_to_sql",
                    "latency_ms": 300,
                    "replanned": True,
                    "execution_loops": 2,
                },
            ],
            events=[
                {
                    "event_type": "text_to_sql",
                    "status": "failed",
                    "error_code": "unknown_column",
                    "duration_ms": 250,
                }
            ],
            metrics_snapshots=[],
            failures=[
                {
                    "failure_type": "sql_error",
                    "source_layer": "sql",
                    "message": "unknown column",
                },
                {
                    "failure_type": "tool_miss",
                    "source_layer": "tool",
                    "message": "missing tool mapping",
                },
            ],
        )


def test_report_generator_creates_three_markdown_reports(tmp_path):
    generator = MdReportGenerator(
        repository=FakeAnalyticsRepository(),
        report_dir=tmp_path,
    )

    artifacts = generator.generate_daily_reports(date(2026, 7, 6))

    paths = {artifact.path for artifact in artifacts}
    assert tmp_path / "daily" / "2026-07-06.md" in paths
    assert tmp_path / "failure" / "2026-07-06.md" in paths
    assert tmp_path / "health" / "latest.md" in paths
    assert (tmp_path / "daily" / "2026-07-06.md").exists()
    assert "# Agent System Daily Report" in (tmp_path / "daily" / "2026-07-06.md").read_text()
    assert "# Failure Analysis Report" in (tmp_path / "failure" / "2026-07-06.md").read_text()
    assert "# System Health Report" in (tmp_path / "health" / "latest.md").read_text()


def test_report_generation_is_idempotent_and_excludes_raw_trace_ids(tmp_path):
    generator = MdReportGenerator(
        repository=FakeAnalyticsRepository(),
        report_dir=tmp_path,
    )

    first = generator.generate("daily", date(2026, 7, 6))
    second = generator.generate("daily", date(2026, 7, 6))

    assert first.path == second.path
    assert first.content == second.content
    assert "raw-trace-1" not in second.content
    assert "total_requests: 2" in second.content
    assert "success_rate: 0.5" in second.content


def test_report_generate_api_uses_unified_generator(tmp_path):
    generator = MdReportGenerator(
        repository=FakeAnalyticsRepository(),
        report_dir=tmp_path,
    )
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


def test_report_generate_api_rejects_unknown_type():
    client = TestClient(app)

    response = client.post("/api/analytics/report/generate", json={"type": "weekly"})

    assert response.status_code == 422


def test_scheduler_calculates_next_0010_run():
    before_run = datetime(2026, 7, 6, 0, 0, 0)
    after_run = datetime(2026, 7, 6, 0, 11, 0)

    assert seconds_until_next_daily_run(before_run) == 600
    assert seconds_until_next_daily_run(after_run) == 86340
