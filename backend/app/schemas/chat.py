from pydantic import BaseModel, Field


class ChatApiRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class TokenUsageApiResponse(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatApiResponse(BaseModel):
    content: str
    model: str
    provider: str
    conversation_key: str
    response_message_key: str
    call_key: str
    finish_reason: str | None = None
    usage: TokenUsageApiResponse | None = None


class ErrorApiResponse(BaseModel):
    error: str
    message: str
