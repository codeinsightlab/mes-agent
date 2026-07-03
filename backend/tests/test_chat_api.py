from fastapi.testclient import TestClient

from app.application.chat_result import ChatUseCaseResult
from app.api.chat import get_chat_service
from app.domain.llm.exceptions import LlmUnavailableError
from app.domain.llm.models import ChatResponse, TokenUsage
from app.main import app


class SuccessfulChatService:
    def chat(self, message):
        return ChatUseCaseResult(
            response=ChatResponse(
                content=f"reply: {message}",
                model="fake-model",
                provider="fake-provider",
                finish_reason="stop",
                usage=TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
            ),
            conversation_key="conversation-key",
            response_message_key="assistant-message-key",
            call_key="call-key",
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
        "conversation_key": "conversation-key",
        "response_message_key": "assistant-message-key",
        "call_key": "call-key",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
        },
    }


def test_health_api_still_returns_ok():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_api_rejects_empty_message():
    app.dependency_overrides[get_chat_service] = lambda: SuccessfulChatService()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": ""})

    app.dependency_overrides.clear()
    assert response.status_code == 422


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
    assert response.json()["detail"]["error"] == "database_configuration_error"


def test_chat_api_default_dependency_missing_db_config_returns_stable_error():
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 500
    assert response.json()["detail"]["error"] in {
        "database_configuration_error",
        "llm_configuration_error",
    }


def test_chat_api_response_does_not_return_database_ids():
    app.dependency_overrides[get_chat_service] = lambda: SuccessfulChatService()
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "hello"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert "conversation_id" not in payload
    assert "message_id" not in payload
    assert "model_call_id" not in payload
