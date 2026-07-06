from datetime import date, datetime, time, timedelta
from pathlib import Path

from app.analytics.report.models import (
    AnalyticsRepository,
    AnalyticsWindow,
    CountGroup,
    MetricValue,
    ReportArtifact,
    ReportArtifactMetrics,
    ReportType,
)


BACKEND_DIR = Path(__file__).resolve().parents[3]
REPORT_DIR = BACKEND_DIR / "reports"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


class MdReportGenerator:
    def __init__(
        self,
        repository: AnalyticsRepository,
        report_dir: Path = REPORT_DIR,
        template_dir: Path = TEMPLATE_DIR,
    ):
        self._repository = repository
        self._report_dir = report_dir
        self._template_dir = template_dir

    @property
    def repository(self) -> AnalyticsRepository:
        return self._repository

    def generate(self, report_type: ReportType, report_date: date | None = None) -> ReportArtifact:
        target_date = report_date or date.today()
        window = _daily_window(target_date)
        report_data = self._repository.fetch_report_data(window)
        metrics: ReportArtifactMetrics = {
            **report_data.metrics,
            "top_failure_types": report_data.top_failure_types,
            "top_sql_errors": report_data.top_sql_errors,
            "tool_usage": report_data.tool_usage,
            "tool_miss_analysis": report_data.tool_miss_analysis,
            "schema_gaps": report_data.schema_gaps,
            "execution_failures": report_data.execution_failures,
            "degradation_signals": report_data.degradation_signals,
            "root_cause_summary": report_data.root_cause_summary,
        }
        template_name = {
            "daily": "daily_report.md.tpl",
            "failure": "failure_report.md.tpl",
            "health": "system_health_report.md.tpl",
        }[report_type]
        output_path = self._output_path(report_type, target_date)
        content = _render_template(
            self._template_dir / template_name,
            {
                "report_date": target_date.isoformat(),
                **_format_metrics(metrics),
            },
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return ReportArtifact(
            report_type=report_type,
            report_date=target_date,
            path=output_path,
            content=content,
            metrics=metrics,
        )

    def generate_daily_reports(self, report_date: date | None = None) -> list[ReportArtifact]:
        return [
            self.generate("daily", report_date),
            self.generate("failure", report_date),
            self.generate("health", report_date),
        ]

    def _output_path(self, report_type: ReportType, report_date: date) -> Path:
        if report_type == "daily":
            return self._report_dir / "daily" / f"{report_date.isoformat()}.md"
        if report_type == "failure":
            return self._report_dir / "failure" / f"{report_date.isoformat()}.md"
        return self._report_dir / "health" / "latest.md"


def _daily_window(report_date: date) -> AnalyticsWindow:
    start_at = datetime.combine(report_date, time.min)
    return AnalyticsWindow(start_at=start_at, end_at=start_at + timedelta(days=1))


TemplateValue = str | MetricValue | list[CountGroup] | list[str]


def _render_template(path: Path, values: dict[str, str]) -> str:
    content = path.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{ " + key + " }}", str(value))
    return content


def _format_metrics(metrics: ReportArtifactMetrics) -> dict[str, str]:
    formatted: dict[str, str] = {}
    for key, value in metrics.items():
        if isinstance(value, list):
            formatted[key] = _format_list(value)
        elif isinstance(value, float):
            formatted[key] = str(value)
        else:
            formatted[key] = str(value)
    return formatted


def _format_list(values: list[CountGroup] | list[str]) -> str:
    if not values:
        return "- N/A"
    lines: list[str] = []
    for item in values:
        if isinstance(item, dict):
            name = item.get("name", "N/A")
            count = item.get("count", 0)
            lines.append(f"- {name}: {count}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)
