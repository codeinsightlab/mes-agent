from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.admin_issue import get_issue_service, get_review_service
from app.domain.issue.exceptions import (
    FeedbackNotDislikedError,
    FeedbackNotFoundError,
    InvalidIssueTransitionError,
    IssueNotFoundError,
)
from app.main import app


NOW = datetime(2026, 7, 3, tzinfo=UTC)


class FakeReviewService:
    def list_disliked_feedbacks(self, **kwargs):
        return {
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "total": 1,
            "items": [
                {
                    "feedback_key": "feedback-key",
                    "response_message_key": "assistant-message-key",
                    "reason_type": 1,
                    "reason_type_label": "答非所问",
                    "comment": "summary",
                    "visitor_digest": "abcdef123456",
                    "assistant_content_summary": "assistant",
                    "user_message_content_summary": "user",
                    "conversation_key": "conversation-key",
                    "model": "model",
                    "provider": "provider",
                    "agent_version": "0.1.0",
                    "prompt_version": "chat-v1",
                    "tool_version": None,
                    "created_at": NOW,
                    "has_issue": False,
                    "issue_key": None,
                    "issue_status": None,
                    "issue_status_label": None,
                }
            ],
        }

    def get_disliked_feedback_detail(self, feedback_key):
        if feedback_key == "missing":
            raise FeedbackNotFoundError("missing")
        return {
            "feedback_key": feedback_key,
            "feedback_type": 2,
            "reason_type": 1,
            "reason_type_label": "答非所问",
            "comment": "comment",
            "visitor_digest": "abcdef123456",
            "created_at": NOW,
            "updated_at": NOW,
            "conversation_key": "conversation-key",
            "user_message": {
                "message_key": "user-message-key",
                "role": 2,
                "content": "user",
                "sequence_no": 1,
                "created_at": NOW,
            },
            "assistant_message": {
                "message_key": "assistant-message-key",
                "role": 3,
                "content": "assistant",
                "sequence_no": 2,
                "created_at": NOW,
            },
            "model_call": None,
            "has_issue": False,
            "issue": None,
        }


class FakeIssueService:
    def create_issue(self, feedback_key, priority=2):
        if feedback_key == "missing":
            raise FeedbackNotFoundError("missing")
        if feedback_key == "liked":
            raise FeedbackNotDislikedError("liked")
        return self._issue(feedback_key=feedback_key)

    def list_issues(self, **kwargs):
        return {
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "total": 1,
            "items": [self._issue(detail=False)],
        }

    def get_issue(self, issue_key):
        if issue_key == "missing":
            raise IssueNotFoundError("missing")
        return self._issue()

    def update_issue(self, issue_key, **changes):
        if issue_key == "bad-transition":
            raise InvalidIssueTransitionError("bad")
        return self._issue(process_status=changes.get("process_status", 2))

    def _issue(self, feedback_key="feedback-key", process_status=1, detail=True):
        data = {
            "issue_key": "issue-key",
            "feedback_key": feedback_key,
            "process_status": process_status,
            "process_status_label": "待处理",
            "priority": 2,
            "priority_label": "中",
            "root_cause_type": None,
            "root_cause_type_label": None,
            "processed_by": None,
            "processed_at": None,
            "created_at": NOW,
            "updated_at": NOW,
        }
        if detail:
            data["root_cause"] = None
            data["solution"] = None
        return data


def setup_overrides():
    app.dependency_overrides[get_review_service] = lambda: FakeReviewService()
    app.dependency_overrides[get_issue_service] = lambda: FakeIssueService()


def test_disliked_feedback_list_success_does_not_return_ids():
    setup_overrides()
    client = TestClient(app)

    response = client.get("/api/admin/feedbacks/disliked")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["feedback_key"] == "feedback-key"
    assert "id" not in item
    assert "visitor_id" not in item
    assert item["visitor_digest"] == "abcdef123456"


def test_disliked_feedback_detail_success():
    setup_overrides()
    client = TestClient(app)

    response = client.get("/api/admin/feedbacks/feedback-key")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["assistant_message"]["role"] == 3


def test_create_issue_success_and_liked_feedback_rejected():
    setup_overrides()
    client = TestClient(app)

    ok = client.post("/api/admin/issues", json={"feedback_key": "feedback-key"})
    rejected = client.post("/api/admin/issues", json={"feedback_key": "liked"})

    app.dependency_overrides.clear()
    assert ok.status_code == 200
    assert ok.json()["issue_key"] == "issue-key"
    assert "id" not in ok.json()
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["error"] == "feedback_not_disliked"


def test_issue_list_detail_and_update_success():
    setup_overrides()
    client = TestClient(app)

    list_response = client.get("/api/admin/issues")
    detail_response = client.get("/api/admin/issues/issue-key")
    update_response = client.put("/api/admin/issues/issue-key", json={"process_status": 2})

    app.dependency_overrides.clear()
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["process_status"] == 2


def test_issue_update_invalid_transition_returns_409():
    setup_overrides()
    client = TestClient(app)

    response = client.put("/api/admin/issues/bad-transition", json={"process_status": 6})

    app.dependency_overrides.clear()
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "invalid_issue_transition"
