from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from app.core.type_defs import JsonObject

ReportType = Literal["daily", "failure", "health"]
MetricValue = int | float | str | None


class ReportMetrics(TypedDict, total=False):
    total_requests: int
    success_rate: float
    avg_loop_depth: float
    avg_latency: float
    tool_hit_rate: float
    sql_success_rate: float
    replan_rate: float
    failure_count: int
    planner_success_rate: float
    system_risk_level: str
    most_used_tool: str


class CountGroup(TypedDict):
    name: str
    count: int


class AnalyticsTraceRecord(TypedDict):
    trace_id: str
    user_query: str
    plan_json: JsonObject | str | None
    final_result: JsonObject | str | None
    status: str
    loop_depth: int
    created_at: datetime


class ReportArtifactMetrics(ReportMetrics, total=False):
    top_failure_types: list[CountGroup]
    top_sql_errors: list[CountGroup]
    tool_usage: list[CountGroup]
    tool_miss_analysis: list[CountGroup]
    schema_gaps: list[CountGroup]
    execution_failures: list[CountGroup]
    degradation_signals: list[str]
    root_cause_summary: str


@dataclass(frozen=True)
class AnalyticsWindow:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class AnalyticsReportData:
    metrics: ReportMetrics = field(default_factory=ReportMetrics)
    top_failure_types: list[CountGroup] = field(default_factory=list)
    top_sql_errors: list[CountGroup] = field(default_factory=list)
    tool_usage: list[CountGroup] = field(default_factory=list)
    tool_miss_analysis: list[CountGroup] = field(default_factory=list)
    schema_gaps: list[CountGroup] = field(default_factory=list)
    execution_failures: list[CountGroup] = field(default_factory=list)
    degradation_signals: list[str] = field(default_factory=list)
    root_cause_summary: str = "No dominant failure pattern in the selected window."


@dataclass(frozen=True)
class ReportArtifact:
    report_type: ReportType
    report_date: date
    path: Path
    content: str
    metrics: ReportArtifactMetrics


class AnalyticsRepository(Protocol):
    def fetch_report_data(self, window: AnalyticsWindow) -> AnalyticsReportData:
        ...

    def get_trace(self, trace_id: str) -> AnalyticsTraceRecord | None:
        ...
