from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol


ReportType = Literal["daily", "failure", "health"]


@dataclass(frozen=True)
class AnalyticsWindow:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class AnalyticsRawData:
    traces: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    metrics_snapshots: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ReportArtifact:
    report_type: ReportType
    report_date: date
    path: Path
    content: str
    metrics: dict[str, Any]


class AnalyticsRepository(Protocol):
    def fetch_window(self, window: AnalyticsWindow) -> AnalyticsRawData:
        ...
