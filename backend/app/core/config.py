import os
from dataclasses import dataclass

from dotenv import load_dotenv

from app.domain.llm.exceptions import LlmConfigurationError


load_dotenv()

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_LLM_PROVIDER = "deepseek"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0


def _parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    llm_provider: str
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: float


def get_settings() -> Settings:
    timeout_raw = os.getenv("LLM_TIMEOUT_SECONDS", str(DEFAULT_LLM_TIMEOUT_SECONDS))
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise LlmConfigurationError("LLM_TIMEOUT_SECONDS must be a number.") from exc

    if timeout_seconds <= 0:
        raise LlmConfigurationError("LLM_TIMEOUT_SECONDS must be greater than 0.")

    return Settings(
        cors_origins=_parse_cors_origins(
            os.getenv("BACKEND_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
        ),
        llm_provider=os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).strip(),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip(),
        llm_model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip(),
        llm_timeout_seconds=timeout_seconds,
    )
