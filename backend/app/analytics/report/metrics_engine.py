from collections import Counter
from typing import Any

from app.analytics.report.models import AnalyticsRawData


def build_report_metrics(raw_data: AnalyticsRawData) -> dict[str, Any]:
    traces = raw_data.traces
    events = raw_data.events
    failures = raw_data.failures

    total_requests = _count_requests(traces, events)
    success_count = sum(1 for item in traces if _is_success(item))
    failure_count = len(failures) or max(total_requests - success_count, 0)

    tool_names = _collect_tool_names(traces, events)
    sql_items = _collect_sql_items(traces, events)
    sql_errors = _collect_sql_errors(events, failures)
    failure_types = [_text_value(item, "failure_type", "error_type", "code") for item in failures]
    failure_types = [item for item in failure_types if item]

    loop_depths = [_number_value(item, "loop_depth", "execution_loops", "planner_calls") for item in traces]
    loop_depths = [item for item in loop_depths if item is not None]
    replan_count = sum(1 for item in traces if _bool_value(item, "replanned") or _number_value(item, "replan_count") not in (None, 0))

    tool_total = sum(1 for item in traces if _text_value(item, "route") == "tool") or len(tool_names)
    sql_total = len(sql_items)
    sql_success = sum(1 for item in sql_items if _is_success(item) or _bool_value(item, "sql_executed"))

    metrics = {
        "total_requests": total_requests,
        "success_rate": _rate(success_count, total_requests),
        "avg_latency": _average(
            [
                _number_value(item, "latency_ms", "duration_ms", "execution_time_ms")
                for item in traces + events
            ]
        ),
        "most_used_tool": _top_one(tool_names),
        "tool_hit_rate": _rate(tool_total, total_requests),
        "sql_success_rate": _rate(sql_success, sql_total),
        "top_sql_errors": _top_items(sql_errors),
        "top_failure_types": _top_items(failure_types),
        "root_cause_summary": _root_cause_summary(failure_types, sql_errors),
        "replan_rate": _rate(replan_count, total_requests),
        "avg_loop_depth": _average(loop_depths),
        "planner_success_rate": _planner_success_rate(traces, failures, total_requests),
        "system_risk_level": "LOW",
        "degradation_signals": [],
        "tool_miss_analysis": _filter_failures(failures, ["tool_miss"]),
        "sql_error_patterns": _top_items(sql_errors),
        "schema_gaps": _filter_failures(failures, ["schema_gap"]),
        "execution_failures": _filter_failures(failures, ["execution_error"]),
        "failure_count": failure_count,
    }
    metrics["system_risk_level"] = _risk_level(metrics)
    metrics["degradation_signals"] = _degradation_signals(metrics)
    return metrics


def _count_requests(traces: list[dict[str, Any]], events: list[dict[str, Any]]) -> int:
    if traces:
        return len(traces)
    request_events = [item for item in events if _text_value(item, "event_type", "type") in {"request", "agent_run"}]
    return len(request_events)


def _collect_tool_names(traces: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[str]:
    names = []
    for item in traces + events:
        name = _text_value(item, "tool_name", "capability_name", "capability")
        if name:
            names.append(name)
    return names


def _collect_sql_items(traces: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for item in traces + events:
        route = _text_value(item, "route", "event_type", "type")
        if route in {"sql", "text_to_sql"} or _text_value(item, "sql", "generated_sql", "validated_sql"):
            items.append(item)
    return items


def _collect_sql_errors(events: list[dict[str, Any]], failures: list[dict[str, Any]]) -> list[str]:
    errors = []
    for item in events + failures:
        route = _text_value(item, "route", "event_type", "type", "source_layer")
        if route in {"sql", "text_to_sql"} or _text_value(item, "sql", "generated_sql"):
            error = _text_value(item, "error_code", "code", "failure_type", "error_type")
            if error:
                errors.append(error)
    return errors


def _planner_success_rate(traces: list[dict[str, Any]], failures: list[dict[str, Any]], total_requests: int) -> float:
    planner_failures = sum(
        1
        for item in failures
        if _text_value(item, "source_layer", "failure_type", "error_type") in {"planner", "planner_error", "missing_param"}
    )
    return _rate(max(total_requests - planner_failures, 0), total_requests)


def _filter_failures(failures: list[dict[str, Any]], types: list[str]) -> list[str]:
    matched = []
    for item in failures:
        failure_type = _text_value(item, "failure_type", "error_type", "code")
        if failure_type in types:
            matched.append(failure_type)
    return [f"{item['name']}: {item['count']}" for item in _top_items(matched)]


def _risk_level(metrics: dict[str, Any]) -> str:
    if metrics["success_rate"] < 0.8 or metrics["sql_success_rate"] < 0.8 or metrics["failure_count"] >= 10:
        return "HIGH"
    if metrics["success_rate"] < 0.95 or metrics["replan_rate"] > 0.2 or metrics["failure_count"] > 0:
        return "MEDIUM"
    return "LOW"


def _degradation_signals(metrics: dict[str, Any]) -> list[str]:
    signals = []
    if metrics["replan_rate"] > 0.2:
        signals.append("loop instability: replan_rate above 20%")
    if metrics["top_failure_types"]:
        signals.append("rising failure patterns: " + ", ".join(item["name"] for item in metrics["top_failure_types"][:3]))
    if metrics["sql_success_rate"] < 0.95:
        signals.append("sql instability: sql_success_rate below 95%")
    return signals


def _root_cause_summary(failure_types: list[str], sql_errors: list[str]) -> str:
    if not failure_types and not sql_errors:
        return "No dominant failure pattern in the selected window."
    parts = []
    if failure_types:
        parts.append("Top failures: " + ", ".join(item["name"] for item in _top_items(failure_types)[:3]))
    if sql_errors:
        parts.append("Top SQL errors: " + ", ".join(item["name"] for item in _top_items(sql_errors)[:3]))
    return " ".join(parts)


def _is_success(item: dict[str, Any]) -> bool:
    status = _text_value(item, "status", "final_status", "execution_status")
    return status in {"success", "ok", "succeeded"}


def _bool_value(item: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = item.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes"}
    return False


def _number_value(item: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _text_value(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _average(values: list[float | None]) -> float:
    numbers = [value for value in values if value is not None]
    if not numbers:
        return 0.0
    return round(sum(numbers) / len(numbers), 2)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _top_one(values: list[str]) -> str:
    if not values:
        return "N/A"
    return Counter(values).most_common(1)[0][0]


def _top_items(values: list[str]) -> list[dict[str, Any]]:
    return [{"name": name, "count": count} for name, count in Counter(values).most_common(5)]
