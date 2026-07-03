import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.domain.llm.exceptions import LlmConfigurationError
from app.domain.persistence.exceptions import DatabaseConfigurationError


BACKEND_DIR = Path(__file__).resolve().parents[2]
BACKEND_ENV_PATH = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=BACKEND_ENV_PATH)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_LLM_PROVIDER = "deepseek"
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_LLM_TIMEOUT_SECONDS = 30.0
DEFAULT_DB_PORT = 3306
DEFAULT_DB_POOL_SIZE = 5
DEFAULT_DB_MAX_OVERFLOW = 10
DEFAULT_DB_POOL_RECYCLE_SECONDS = 1800
DEFAULT_DB_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_AGENT_VERSION = "0.1.0"
DEFAULT_PROMPT_VERSION = "chat-v1"
DEFAULT_AGENT_TOOL_MATCH_THRESHOLD = 0.75


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
    db_host: str | None = None
    db_port: int = DEFAULT_DB_PORT
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_pool_size: int = DEFAULT_DB_POOL_SIZE
    db_max_overflow: int = DEFAULT_DB_MAX_OVERFLOW
    db_pool_recycle_seconds: int = DEFAULT_DB_POOL_RECYCLE_SECONDS
    db_connect_timeout_seconds: int = DEFAULT_DB_CONNECT_TIMEOUT_SECONDS
    agent_version: str = DEFAULT_AGENT_VERSION
    prompt_version: str = DEFAULT_PROMPT_VERSION
    tool_version: str | None = None
    agent_tool_match_threshold: float = DEFAULT_AGENT_TOOL_MATCH_THRESHOLD
    env_file_path: str = str(BACKEND_ENV_PATH)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise DatabaseConfigurationError(f"{name} must be an integer.") from exc
    if value < 0:
        raise DatabaseConfigurationError(f"{name} must be greater than or equal to 0.")
    return value


def get_settings() -> Settings:
    timeout_raw = os.getenv("LLM_TIMEOUT_SECONDS", str(DEFAULT_LLM_TIMEOUT_SECONDS))
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise LlmConfigurationError("LLM_TIMEOUT_SECONDS must be a number.") from exc

    if timeout_seconds <= 0:
        raise LlmConfigurationError("LLM_TIMEOUT_SECONDS must be greater than 0.")

    threshold_raw = os.getenv(
        "AGENT_TOOL_MATCH_THRESHOLD",
        str(DEFAULT_AGENT_TOOL_MATCH_THRESHOLD),
    )
    try:
        threshold = float(threshold_raw)
    except ValueError as exc:
        raise LlmConfigurationError("AGENT_TOOL_MATCH_THRESHOLD must be a number.") from exc
    if threshold < 0 or threshold > 1:
        raise LlmConfigurationError("AGENT_TOOL_MATCH_THRESHOLD must be between 0 and 1.")

    return Settings(
        env_file_path=str(BACKEND_ENV_PATH),
        cors_origins=_parse_cors_origins(
            os.getenv("BACKEND_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
        ),
        llm_provider=os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).strip(),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip(),
        llm_model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip(),
        llm_timeout_seconds=timeout_seconds,
        db_host=os.getenv("DB_HOST"),
        db_port=_int_env("DB_PORT", DEFAULT_DB_PORT),
        db_name=os.getenv("DB_NAME"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_pool_size=_int_env("DB_POOL_SIZE", DEFAULT_DB_POOL_SIZE),
        db_max_overflow=_int_env("DB_MAX_OVERFLOW", DEFAULT_DB_MAX_OVERFLOW),
        db_pool_recycle_seconds=_int_env(
            "DB_POOL_RECYCLE_SECONDS", DEFAULT_DB_POOL_RECYCLE_SECONDS
        ),
        db_connect_timeout_seconds=_int_env(
            "DB_CONNECT_TIMEOUT_SECONDS", DEFAULT_DB_CONNECT_TIMEOUT_SECONDS
        ),
        agent_version=os.getenv("AGENT_VERSION", DEFAULT_AGENT_VERSION).strip(),
        prompt_version=os.getenv("PROMPT_VERSION", DEFAULT_PROMPT_VERSION).strip(),
        tool_version=os.getenv("TOOL_VERSION") or None,
        agent_tool_match_threshold=threshold,
    )
