from fastapi.testclient import TestClient

from app.api.agent import get_orchestrator
from app.api.chat import get_chat_service
from app.api.feedback import get_feedback_service
from app.api.admin_issue import get_issue_service, get_review_service
from app.main import app


def test_existing_routes_remain_registered():
    route_paths = {route.path for route in app.routes}

    assert "/api/chat" in route_paths
    assert "/api/feedback" in route_paths
    assert "/api/admin/issues" in route_paths
    assert "/api/health" in route_paths
    assert "/api/agent/run" in route_paths


def test_agent_debug_routes_are_not_public_entrypoints():
    client = TestClient(app)

    assert client.post("/api/agent/query", json={"message": "x"}).status_code == 404
    assert client.post("/api/agent/plan", json={"user_query": "x"}).status_code == 404


class FakeOrchestrator:
    def run(self, request):
        return {
            "trace_id": "trace-test",
            "plan_trace": {
                "initial_plan": {"intent": "tool", "steps": []},
                "replan": None,
            },
            "execution_trace": [
                {
                    "step": 1,
                    "result": {
                        "status": "success",
                        "data": {"value": "ok"},
                        "observation": {
                            "facts_found": ["result"],
                            "missing_facts": [],
                            "decision_signals": [],
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
            "final_result": {"status": "success", "data": {"value": "ok"}, "error": None},
            "debug": {
                "route": "tool",
                "failure_analysis": None,
                "execution_summary": {
                    "planner_calls": 1,
                    "execution_loops": 1,
                    "replanned": False,
                    "max_execution_loop": 2,
                    "max_planner_call": 2,
                },
            },
        }


def test_agent_run_api_returns_unified_orchestrator_schema():
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    client = TestClient(app)

    response = client.post("/api/agent/run", json={"message": "TRACE-HTR-K2-T-FG-001到哪了"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"] == "trace-test"
    assert "plan_trace" in payload
    assert "execution_trace" in payload
    assert payload["final_result"]["status"] == "success"
    assert payload["debug"]["route"] == "tool"
