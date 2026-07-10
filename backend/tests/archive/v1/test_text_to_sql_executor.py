from app.agent.execution.tools.text_to_sql.executor import ReadonlySqlExecutor
from app.core.config import Settings


def test_executor_returns_stable_error_when_mes_db_config_missing():
    settings = Settings(
        cors_origins=[],
        llm_provider="deepseek",
        llm_api_key="fake",
        llm_base_url="https://example.invalid",
        llm_model="fake-model",
        llm_timeout_seconds=1,
    )
    executor = ReadonlySqlExecutor(settings=settings, max_rows=100, timeout_seconds=1)

    result = executor.execute("SELECT 1")

    assert result.status == "failed"
    assert result.error_code == "mes_db_configuration_error"
    assert "AGENT_MES_DB_HOST" in (result.error_message or "")
