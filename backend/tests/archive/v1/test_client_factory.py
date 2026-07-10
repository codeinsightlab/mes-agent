import pytest

from app.core.config import Settings
from app.domain.llm.exceptions import LlmConfigurationError
from app.infrastructure.llm.client_factory import create_llm_client


def test_deepseek_requires_api_key():
    settings = Settings(
        cors_origins=["http://localhost:5173"],
        llm_provider="deepseek",
        llm_api_key=None,
        llm_base_url="https://api.deepseek.com",
        llm_model="deepseek-chat",
        llm_timeout_seconds=30,
    )

    with pytest.raises(LlmConfigurationError):
        create_llm_client(settings)


def test_unsupported_provider_fails_clearly():
    settings = Settings(
        cors_origins=["http://localhost:5173"],
        llm_provider="unknown",
        llm_api_key="test",
        llm_base_url="https://api.deepseek.com",
        llm_model="deepseek-chat",
        llm_timeout_seconds=30,
    )

    with pytest.raises(LlmConfigurationError):
        create_llm_client(settings)
