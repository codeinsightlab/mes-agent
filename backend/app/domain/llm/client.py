from typing import Protocol

from app.domain.llm.models import ChatRequest, ChatResponse


class LlmClient(Protocol):
    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a non-streaming chat request to an LLM provider."""
        raise NotImplementedError
