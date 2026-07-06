from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import Settings
from app.domain.llm.exceptions import LlmConfigurationError


def create_agent_chat_model(settings: Settings) -> ChatOpenAI:
    if not settings.llm_api_key or not settings.llm_api_key.strip():
        raise LlmConfigurationError("LLM_API_KEY is required for Agent matcher.")
    return ChatOpenAI(
        api_key=SecretStr(settings.llm_api_key),
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        temperature=0,
        timeout=settings.llm_timeout_seconds,
    )
