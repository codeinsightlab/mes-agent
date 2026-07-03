from fastapi.testclient import TestClient

from app.application.chat_result import ChatUseCaseResult
from app.application.chat_persistence_service import ChatPersistenceService
from app.api.chat import get_chat_service
import app.api.chat as chat_module
from app.core.config import Settings
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


def test_chat_api_missing_database_config_returns_stable_error(monkeypatch):
    app.dependency_overrides.clear()
    chat_module.close_chat_service()
    chat_module._chat_service = None
    chat_module._database_engine = None
    client = TestClient(app)

    monkeypatch.setattr(chat_module, "get_settings", lambda: Settings(
        cors_origins=["http://localhost:5173"],
        llm_provider="deepseek",
        llm_api_key="test",
        llm_base_url="https://api.deepseek.com",
        llm_model="deepseek-chat",
        llm_timeout_seconds=30,
    ))
    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "database_configuration_error"


def test_chat_api_missing_llm_config_returns_stable_error(monkeypatch):
    app.dependency_overrides.clear()
    chat_module.close_chat_service()
    chat_module._chat_service = None
    chat_module._database_engine = None
    client = TestClient(app)

    class FakeEngine:
        def dispose(self):
            pass

    monkeypatch.setattr(chat_module, "get_settings", lambda: Settings(
        cors_origins=["http://localhost:5173"],
        llm_provider="deepseek",
        llm_api_key=None,
        llm_base_url="https://api.deepseek.com",
        llm_model="deepseek-chat",
        llm_timeout_seconds=30,
        db_host="127.0.0.1",
        db_name="mes_agent",
        db_user="test",
        db_password="test",
    ))
    monkeypatch.setattr(chat_module, "create_database_engine", lambda settings: FakeEngine())
    monkeypatch.setattr(chat_module, "check_database_connection", lambda engine: "mes_agent")

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 500
    assert response.json()["detail"]["error"] == "llm_configuration_error"


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


def test_production_chat_service_uses_real_persistence_service(monkeypatch):
    class FakeSettings:
        llm_provider = "fake-provider"
        llm_model = "fake-model"
        agent_version = "0.1.0"
        prompt_version = "chat-v1"
        tool_version = None

    class FakeEngine:
        def dispose(self):
            pass

    class FakeLlmClient:
        pass

    monkeypatch.setattr(chat_module, "_chat_service", None)
    monkeypatch.setattr(chat_module, "_database_engine", None)
    monkeypatch.setattr(chat_module, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(chat_module, "create_database_engine", lambda settings: FakeEngine())
    monkeypatch.setattr(chat_module, "check_database_connection", lambda engine: "mes_agent")
    monkeypatch.setattr(chat_module, "create_session_factory", lambda engine: object())
    monkeypatch.setattr(chat_module, "create_llm_client", lambda settings: FakeLlmClient())

    service = get_chat_service()

    chat_module.close_chat_service()
    assert isinstance(service._persistence_service, ChatPersistenceService)
