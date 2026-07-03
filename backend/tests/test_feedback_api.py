from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.feedback import get_feedback_service
from app.domain.feedback.exceptions import (
    FeedbackPersistenceError,
    FeedbackTargetNotAssistantError,
    FeedbackTargetNotFoundError,
)
from app.main import app


class SuccessfulFeedbackService:
    def __init__(self):
        self.calls = []

    def submit_feedback(self, identity, command):
        self.calls.append((identity, command))

        class Result:
            feedback_key = "feedback-key"
            response_message_key = command.response_message_key
            feedback_type = command.feedback_type
            feedback_type_label = "喜欢" if command.feedback_type == 1 else "不喜欢"
            reason_type = command.reason_type
            reason_type_label = "答非所问" if command.reason_type == 1 else None
            comment = command.comment
            created_at = datetime(2026, 7, 3, tzinfo=UTC)
            updated_at = datetime(2026, 7, 3, tzinfo=UTC)

        return Result()


class NotFoundFeedbackService:
    def submit_feedback(self, identity, command):
        raise FeedbackTargetNotFoundError("missing")


class NonAssistantFeedbackService:
    def submit_feedback(self, identity, command):
        raise FeedbackTargetNotAssistantError("bad target")


class FailingFeedbackService:
    def submit_feedback(self, identity, command):
        raise FeedbackPersistenceError("db failed")


def test_feedback_api_success_create_returns_stable_response():
    service = SuccessfulFeedbackService()
    app.dependency_overrides[get_feedback_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "response_message_key": "assistant-message-key",
            "visitor_id": "visitor-1",
            "feedback_type": 1,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["feedback_key"] == "feedback-key"
    assert payload["feedback_type"] == 1
    assert payload["feedback_type_label"] == "喜欢"
    assert "id" not in payload
    assert "message_id" not in payload
    assert "conversation_id" not in payload
    assert "user_id" not in payload
    assert service.calls[0][0].user_id is None
    assert service.calls[0][0].visitor_id == "visitor-1"


def test_feedback_api_success_update_returns_200():
    app.dependency_overrides[get_feedback_service] = lambda: SuccessfulFeedbackService()
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "response_message_key": "assistant-message-key",
            "visitor_id": "visitor-1",
            "feedback_type": 2,
            "reason_type": 1,
            "comment": "wrong answer",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["feedback_type"] == 2


def test_feedback_api_not_found_returns_404():
    app.dependency_overrides[get_feedback_service] = lambda: NotFoundFeedbackService()
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "response_message_key": "missing",
            "visitor_id": "visitor-1",
            "feedback_type": 1,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "feedback_target_not_found"


def test_feedback_api_non_assistant_returns_stable_error():
    app.dependency_overrides[get_feedback_service] = lambda: NonAssistantFeedbackService()
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "response_message_key": "user-message-key",
            "visitor_id": "visitor-1",
            "feedback_type": 1,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "feedback_target_not_assistant"


def test_feedback_api_persistence_failure_returns_stable_error():
    app.dependency_overrides[get_feedback_service] = lambda: FailingFeedbackService()
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "response_message_key": "assistant-message-key",
            "visitor_id": "visitor-1",
            "feedback_type": 1,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "feedback_persistence_error"


def test_feedback_api_rejects_user_id():
    app.dependency_overrides[get_feedback_service] = lambda: SuccessfulFeedbackService()
    client = TestClient(app)

    response = client.post(
        "/api/feedback",
        json={
            "response_message_key": "assistant-message-key",
            "visitor_id": "visitor-1",
            "user_id": "not-accepted",
            "feedback_type": 1,
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_feedback_api_does_not_affect_health():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
