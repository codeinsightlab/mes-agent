from app.domain.llm.client import LlmClient
from app.domain.llm.models import ChatRequest, ChatResponse, LlmMessage


class ChatApplicationService:
    def __init__(self, llm_client: LlmClient):
        self._llm_client = llm_client

    def close(self):
        close = getattr(self._llm_client, "close", None)
        if callable(close):
            close()

    def chat(self, message: str) -> ChatResponse:
        if not message or not message.strip():
            raise ValueError("Message cannot be empty.")

        request = ChatRequest(
            messages=[
                LlmMessage(
                    role="system",
                    content="You are a concise assistant for a MES Agent research project.",
                ),
                LlmMessage(role="user", content=message.strip()),
            ]
        )
        return self._llm_client.chat(request)
