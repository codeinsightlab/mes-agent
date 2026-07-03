from dataclasses import dataclass

from app.domain.llm.models import ChatResponse


@dataclass(frozen=True)
class ChatUseCaseResult:
    response: ChatResponse
    conversation_key: str
    response_message_key: str
    call_key: str
