from app.core.config import Settings
from app.domain.llm.client import LlmClient
from app.domain.llm.exceptions import LlmConfigurationError
from app.infrastructure.llm.deepseek_client import DeepSeekLlmClient


def create_llm_client(settings: Settings) -> LlmClient:
    provider = settings.llm_provider.lower()

    if provider == "deepseek":
        if not settings.llm_api_key or not settings.llm_api_key.strip():
            raise LlmConfigurationError("LLM_API_KEY is required for DeepSeek.")
        if not settings.llm_base_url:
            raise LlmConfigurationError("LLM_BASE_URL is required.")
        if not settings.llm_model:
            raise LlmConfigurationError("LLM_MODEL is required.")

        return DeepSeekLlmClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            default_model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    raise LlmConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}.")
