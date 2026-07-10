from app.application.chat_service import ChatApplicationService
from app.application.chat_persistence_service import ChatRecordStart, ChatRecordSuccess
from app.domain.llm.exceptions import LlmCallError, LlmTimeoutError
from app.domain.persistence.exceptions import (
    ConversationInitializationError,
    ModelResultPersistenceError,
)
from app.domain.llm.models import ChatResponse, TokenUsage


class FakeLlmClient:
    def __init__(self, exception=None):
        self.received_request = None
        self.called = False
        self.exception = exception

    def chat(self, request):
        self.called = True
        self.received_request = request
        if self.exception:
            raise self.exception
        return ChatResponse(
            content="pong",
            model="fake-model",
            provider="fake-provider",
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3),
        )


class FakePersistenceService:
    def __init__(self, initialize_exception=None, success_exception=None):
        self.initialize_exception = initialize_exception
        self.success_exception = success_exception
        self.initialize_calls = []
        self.success_calls = []
        self.failure_calls = []

    def initialize_chat(self, **kwargs):
        if self.initialize_exception:
            raise self.initialize_exception
        self.initialize_calls.append(kwargs)
        return ChatRecordStart(
            conversation_id=1,
            conversation_key="conversation-key",
            user_message_id=2,
            user_message_key="user-message-key",
            call_id=3,
            call_key="call-key",
        )

    def save_success(self, **kwargs):
        if self.success_exception:
            raise self.success_exception
        self.success_calls.append(kwargs)
        return ChatRecordSuccess(
            conversation_key="conversation-key",
            response_message_key="assistant-message-key",
            call_key="call-key",
        )

    def save_failure(self, **kwargs):
        self.failure_calls.append(kwargs)


def make_service(llm_client, persistence_service):
    return ChatApplicationService(
        llm_client=llm_client,
        persistence_service=persistence_service,
        provider="fake-provider",
        model="fake-model",
        agent_version="0.1.0",
        prompt_version="chat-v1",
        tool_version=None,
    )


def test_chat_service_calls_llm_client_with_user_message():
    client = FakeLlmClient()
    persistence = FakePersistenceService()
    service = make_service(client, persistence)

    response = service.chat("hello")

    assert response.response.content == "pong"
    assert response.conversation_key == "conversation-key"
    assert response.response_message_key == "assistant-message-key"
    assert response.call_key == "call-key"
    assert client.received_request is not None
    assert client.received_request.messages[-1].role == "user"
    assert client.received_request.messages[-1].content == "hello"
    assert persistence.initialize_calls
    assert persistence.success_calls


def test_chat_service_does_not_reuse_previous_user_message():
    client = FakeLlmClient()
    persistence = FakePersistenceService()
    service = make_service(client, persistence)

    service.chat("first question")
    service.chat("second question")

    contents = [message.content for message in client.received_request.messages]
    assert "second question" in contents
    assert "first question" not in contents


def test_first_persistence_failure_does_not_call_llm():
    client = FakeLlmClient()
    persistence = FakePersistenceService(
        initialize_exception=ConversationInitializationError("init failed")
    )
    service = make_service(client, persistence)

    try:
        service.chat("hello")
    except ConversationInitializationError:
        pass

    assert client.called is False


def test_model_success_saves_usage_duration_and_response():
    client = FakeLlmClient()
    persistence = FakePersistenceService()
    service = make_service(client, persistence)

    service.chat("hello")

    save_call = persistence.success_calls[0]
    assert save_call["response"].usage.total_tokens == 3
    assert save_call["duration_ms"] >= 0


def test_model_timeout_updates_failure_status_then_reraises():
    client = FakeLlmClient(exception=LlmTimeoutError("timeout"))
    persistence = FakePersistenceService()
    service = make_service(client, persistence)

    try:
        service.chat("hello")
    except LlmTimeoutError:
        pass

    failure_call = persistence.failure_calls[0]
    assert failure_call["timed_out"] is True
    assert failure_call["error_code"] == "llm_timeout"


def test_model_failure_updates_failure_status_then_reraises():
    client = FakeLlmClient(exception=LlmCallError("Authorization should be redacted"))
    persistence = FakePersistenceService()
    service = make_service(client, persistence)

    try:
        service.chat("hello")
    except LlmCallError:
        pass

    failure_call = persistence.failure_calls[0]
    assert failure_call["timed_out"] is False
    assert failure_call["error_code"] == "llm_call_error"
    assert "Authorization" in failure_call["error_message"]


def test_second_persistence_failure_does_not_return_fake_success():
    client = FakeLlmClient()
    persistence = FakePersistenceService(
        success_exception=ModelResultPersistenceError("save failed")
    )
    service = make_service(client, persistence)

    try:
        service.chat("hello")
    except ModelResultPersistenceError:
        pass
    else:
        raise AssertionError("expected persistence error")
