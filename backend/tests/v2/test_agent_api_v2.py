from fastapi.testclient import TestClient

from app.api.agent import get_mes_agent
from app.main import app


class FakeMesAgent:
    def run(self, request):
        return {
            "request_id": "request-v2",
            "agent": "heat_treatment_agent",
            "status": "success",
            "capability": "heat_current_stage",
            "data": {"record_no": "TRACE-HTR-B-H-001"},
            "trace": [],
        }


def test_agent_run_uses_v2_mes_agent_dependency():
    app.dependency_overrides[get_mes_agent] = lambda: FakeMesAgent()
    response = TestClient(app).post(
        "/api/agent/run", json={"message": "TRACE-HTR-B-H-001什么状态"}
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["agent"] == "heat_treatment_agent"
    assert response.json()["capability"] == "heat_current_stage"
