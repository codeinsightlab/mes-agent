import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agent.catalog.heat_treatment import TOOL_VERSION
from app.agent.graph import build_agent_graph
from app.agent.nodes.tool_matcher import LangChainToolMatcher
from app.core.config import get_settings
from app.infrastructure.agent.langchain_factory import create_agent_chat_model

CASES_PATH = BACKEND_DIR / "tests" / "fixtures" / "heat_treatment_tool_match_cases.json"
RESULTS_DIR = BACKEND_DIR.parent / "results"
RAW_PATH = RESULTS_DIR / "heat_tool_matcher_eval_raw.jsonl"
SUMMARY_PATH = RESULTS_DIR / "heat_tool_matcher_eval_summary.json"


def main():
    settings = get_settings()
    RESULTS_DIR.mkdir(exist_ok=True)
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    matcher = LangChainToolMatcher(create_agent_chat_model(settings))
    graph = build_agent_graph(
        matcher=matcher,
        match_threshold=settings.agent_tool_match_threshold,
        text_to_sql_node=text_to_sql_eval_node,
    )

    rows = []
    for case in cases:
        final_result = graph.invoke(
            {
                "user_query": case["message"],
                "conversation_key": None,
                "agent_version": settings.agent_version,
                "prompt_version": settings.prompt_version,
                "tool_version": settings.tool_version or TOOL_VERSION,
            }
        )["final_result"]
        actual_arguments = final_result.get("extracted_arguments") or {}
        expected_record_no = case.get("expected_record_no")
        parameter_pass = True
        if expected_record_no:
            parameter_pass = actual_arguments.get("record_no") == expected_record_no
        row = {
            "id": case["id"],
            "message": case["message"],
            "expected_route": case["expected_route"],
            "actual_route": final_result["route"],
            "expected_capability": case.get("expected_capability"),
            "actual_capability": final_result.get("capability_name"),
            "expected_arguments": {"record_no": expected_record_no} if expected_record_no else {},
            "actual_arguments": actual_arguments,
            "confidence": final_result.get("confidence"),
            "route_pass": final_result["route"] == case["expected_route"],
            "capability_pass": final_result.get("capability_name") == case.get("expected_capability"),
            "parameter_pass": parameter_pass,
        }
        row["pass"] = row["route_pass"] and row["capability_pass"] and row["parameter_pass"]
        rows.append(row)

    RAW_PATH.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary = build_summary(rows)
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_summary(rows):
    total = len(rows) or 1
    by_capability = {}
    for row in rows:
        key = row["expected_capability"] or "text_to_sql"
        bucket = by_capability.setdefault(key, {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += 1 if row["pass"] else 0
    for bucket in by_capability.values():
        bucket["accuracy"] = bucket["passed"] / bucket["total"] if bucket["total"] else 0

    def accuracy(field):
        return sum(1 for row in rows if row[field]) / total

    return {
        "total": len(rows),
        "passed": sum(1 for row in rows if row["pass"]),
        "overall_accuracy": sum(1 for row in rows if row["pass"]) / total,
        "route_accuracy": accuracy("route_pass"),
        "capability_match_accuracy": accuracy("capability_pass"),
        "parameter_extraction_accuracy": accuracy("parameter_pass"),
        "clarification_accuracy": route_accuracy_for(rows, "clarification"),
        "blocked_capability_accuracy": route_accuracy_for(rows, "blocked"),
        "text_to_sql_fallback_accuracy": route_accuracy_for(rows, "text_to_sql"),
        "by_expected_capability": by_capability,
        "failed_ids": [row["id"] for row in rows if not row["pass"]],
    }


def route_accuracy_for(rows, route):
    expected = [row for row in rows if row["expected_route"] == route]
    if not expected:
        return None
    return sum(1 for row in expected if row["route_pass"]) / len(expected)


def text_to_sql_eval_node(state):
    return {
        **state,
        "text_to_sql_status": "eval_only",
        "tool_result": {
            "route": "text_to_sql",
            "status": "eval_only",
            "message": "Matcher evaluation only; SQL generation and execution are not run.",
        },
    }


if __name__ == "__main__":
    main()
