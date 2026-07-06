from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from app.analytics.report.metrics_engine import build_report_metrics
from app.analytics.report.models import (
    AnalyticsRepository,
    AnalyticsWindow,
    ReportArtifact,
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

    def generate(self, report_type: ReportType, report_date: date | None = None) -> ReportArtifact:
        target_date = report_date or date.today()
        window = _daily_window(target_date)
        raw_data = self._repository.fetch_window(window)
        metrics = build_report_metrics(raw_data)
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


def _render_template(path: Path, values: dict[str, Any]) -> str:
    content = path.read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace("{{ " + key + " }}", str(value))
    return content


def _format_metrics(metrics: dict[str, Any]) -> dict[str, str]:
    formatted: dict[str, str] = {}
    for key, value in metrics.items():
        if isinstance(value, list):
            formatted[key] = _format_list(value)
        elif isinstance(value, float):
            formatted[key] = str(value)
        else:
            formatted[key] = str(value)
    return formatted


def _format_list(values: list[Any]) -> str:
    if not values:
        return "- N/A"
    lines = []
    for item in values:
        if isinstance(item, dict):
            name = item.get("name", "N/A")
            count = item.get("count", 0)
            lines.append(f"- {name}: {count}")
        else:
            lines.append(f"- {item}")
    return "\n".join(lines)
