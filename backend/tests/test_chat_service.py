from app.application.chat_service import ChatApplicationService
from app.domain.llm.models import ChatResponse


class FakeLlmClient:
    def __init__(self):
        self.received_request = None

    def chat(self, request):
        self.received_request = request
        return ChatResponse(
            content="pong",
            model="fake-model",
            provider="fake-provider",
            finish_reason="stop",
        )


def test_chat_service_calls_llm_client_with_user_message():
    client = FakeLlmClient()
    service = ChatApplicationService(client)

    response = service.chat("hello")

    assert response.content == "pong"
    assert client.received_request is not None
    assert client.received_request.messages[-1].role == "user"
    assert client.received_request.messages[-1].content == "hello"


def test_chat_service_does_not_reuse_previous_user_message():
    client = FakeLlmClient()
    service = ChatApplicationService(client)

    service.chat("first question")
    service.chat("second question")

    contents = [message.content for message in client.received_request.messages]
    assert "second question" in contents
    assert "first question" not in contents
