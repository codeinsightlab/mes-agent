from dataclasses import dataclass
from typing import Literal


LlmRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class LlmMessage:
    role: LlmRole
    content: str

    def __post_init__(self):
        if self.role not in ("system", "user", "assistant"):
            raise ValueError("LLM message role must be system, user, or assistant.")
        if not self.content or not self.content.strip():
            raise ValueError("LLM message content cannot be empty.")


@dataclass(frozen=True)
class ChatRequest:
    messages: list[LlmMessage]
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None

    def __post_init__(self):
        if not self.messages:
            raise ValueError("Chat request must contain at least one message.")
        if self.temperature is not None and not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0.")


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    provider: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("Chat response content cannot be empty.")
        if not self.model or not self.model.strip():
            raise ValueError("Chat response model cannot be empty.")
        if not self.provider or not self.provider.strip():
            raise ValueError("Chat response provider cannot be empty.")
