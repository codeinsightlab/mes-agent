import json

from app.application.chat_persistence_service import ChatPersistenceService
from app.domain.llm.models import ChatRequest, LlmMessage


class DummySessionFactory:
    pass


def test_request_snapshot_does_not_include_secrets():
    service = ChatPersistenceService(DummySessionFactory())
    request = ChatRequest(messages=[LlmMessage(role="user", content="hello")])

    snapshot = service._request_snapshot(request)
    payload = json.loads(snapshot)

    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert "api_key" not in snapshot.lower()
    assert "authorization" not in snapshot.lower()
    assert "bearer" not in snapshot.lower()


def test_error_message_redacts_authorization_terms():
    service = ChatPersistenceService(DummySessionFactory())

    message = service._sanitize_error_message("Authorization: Bearer secret")

    assert "Authorization" not in message
    assert "Bearer" not in message
