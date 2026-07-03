from fastapi.testclient import TestClient

from app.api.chat import get_chat_service
from app.domain.llm.exceptions import LlmUnavailableError
from app.domain.llm.models import ChatResponse, TokenUsage
from app.main import app


class SuccessfulChatService:
    def chat(self, message):
        return ChatResponse(
            content=f"reply: {message}",
            model="fake-model",
            provider="fake-provider",
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


class FailingChatService:
    def chat(self, message):
        raise LlmUnavailableError("provider down")


def test_chat_api_success_returns_stable_response():
    app.dependency_overrides[get_chat_service] = lambda: SuccessfulChatService()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "hello"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "content": "reply: hello",
        "model": "fake-model",
        "provider": "fake-provider",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
        },
    }


def test_chat_api_rejects_blank_message():
    app.dependency_overrides[get_chat_service] = lambda: SuccessfulChatService()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "   "})

    app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_request"


def test_chat_api_model_exception_returns_stable_error():
    app.dependency_overrides[get_chat_service] = lambda: FailingChatService()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "hello"})

    app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "error": "llm_unavailable",
        "message": "LLM provider is temporarily unavailable.",
    }


def test_chat_api_missing_provider_config_returns_stable_error():
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "llm_configuration_error"
