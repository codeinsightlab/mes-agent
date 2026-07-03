import pytest

from app.domain.llm.models import ChatRequest, ChatResponse, LlmMessage


def test_llm_message_rejects_invalid_role():
    with pytest.raises(ValueError):
        LlmMessage(role="tool", content="hello")


def test_chat_request_rejects_empty_messages():
    with pytest.raises(ValueError):
        ChatRequest(messages=[])


def test_chat_response_requires_content():
    with pytest.raises(ValueError):
        ChatResponse(content="", model="deepseek-chat", provider="deepseek")
