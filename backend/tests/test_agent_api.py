from fastapi.testclient import TestClient

from app.agent.models import AgentResult
from app.api.agent import get_agent_query_service
from app.api.chat import get_chat_service
from app.api.feedback import get_feedback_service
from app.api.admin_issue import get_issue_service, get_review_service
from app.main import app


class FakeAgentService:
    def query(self, message):
        return AgentResult(
            route="text_to_sql",
            matched=False,
            capability_name=None,
            capability_status=None,
            confidence=0.1,
            extracted_arguments={},
            missing_fields=[],
            matcher_reason="fake",
            tool_result={"status": "not_implemented"},
            final_message="fake result",
            agent_version="0.1.0",
            prompt_version="chat-v1",
            tool_version="heat-treatment-tools-v1",
        )


def test_agent_query_api_returns_stable_schema():
    app.dependency_overrides[get_agent_query_service] = lambda: FakeAgentService()
    client = TestClient(app)

    response = client.post("/api/agent/query", json={"message": "统计本月热处理数据"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "text_to_sql"
    assert "id" not in payload
    assert "raw_response" not in payload


def test_agent_query_api_rejects_blank_message():
    app.dependency_overrides[get_agent_query_service] = lambda: FakeAgentService()
    client = TestClient(app)

    response = client.post("/api/agent/query", json={"message": "   "})

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_existing_routes_remain_registered():
    route_paths = {route.path for route in app.routes}

    assert "/api/chat" in route_paths
    assert "/api/feedback" in route_paths
    assert "/api/admin/issues" in route_paths
    assert "/api/health" in route_paths
    assert "/api/agent/query" in route_paths
