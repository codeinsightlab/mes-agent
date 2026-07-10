import httpx
import pytest

from app.domain.llm.exceptions import LlmResponseFormatError
from app.domain.llm.models import ChatRequest, LlmMessage
from app.infrastructure.llm.deepseek_client import DeepSeekLlmClient


def make_client(response_json, status_code=200):
    def handler(request):
        return httpx.Response(status_code=status_code, json=response_json)

    return DeepSeekLlmClient(
        api_key="test-api-key",
        base_url="https://example.test",
        default_model="deepseek-chat",
        timeout_seconds=1,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_deepseek_response_maps_to_common_chat_response():
    client = make_client(
        {
            "model": "deepseek-chat",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "hello from model"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 4,
                "total_tokens": 7,
            },
        }
    )

    response = client.chat(
        ChatRequest(messages=[LlmMessage(role="user", content="hello")])
    )

    assert response.content == "hello from model"
    assert response.model == "deepseek-chat"
    assert response.provider == "deepseek"
    assert response.finish_reason == "stop"
    assert response.usage.total_tokens == 7


def test_deepseek_missing_content_raises_common_exception():
    client = make_client(
        {
            "model": "deepseek-chat",
            "choices": [{"message": {"role": "assistant"}}],
        }
    )

    with pytest.raises(LlmResponseFormatError):
        client.chat(ChatRequest(messages=[LlmMessage(role="user", content="hello")]))
