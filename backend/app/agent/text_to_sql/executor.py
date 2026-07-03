import datetime as dt
import decimal
import json
import time
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine.url import URL

from app.agent.text_to_sql.models import SqlExecutionResult
from app.core.config import Settings
from app.domain.persistence.exceptions import DatabaseConfigurationError


class ReadonlySqlExecutor:
    def __init__(self, settings: Settings, max_rows: int, timeout_seconds: int):
        self._settings = settings
        self._max_rows = max_rows
        self._timeout_seconds = timeout_seconds
        self._engine: Engine | None = None

    def execute(self, sql: str) -> SqlExecutionResult:
        start = time.perf_counter()
        try:
            engine = self._get_engine()
            with engine.connect() as connection:
                timeout_ms = max(self._timeout_seconds, 1) * 1000
                connection.execute(text("SET SESSION MAX_EXECUTION_TIME = :timeout_ms"), {"timeout_ms": timeout_ms})
                result = connection.execute(text(sql))
                rows = [dict(row._mapping) for row in result.fetchmany(self._max_rows)]
                columns = list(result.keys())
            duration_ms = int((time.perf_counter() - start) * 1000)
            return SqlExecutionResult(
                status="success",
                columns=columns,
                rows=[_json_safe_row(row) for row in rows],
                row_count=len(rows),
                duration_ms=duration_ms,
            )
        except DatabaseConfigurationError as exc:
            return SqlExecutionResult(
                status="failed",
                duration_ms=int((time.perf_counter() - start) * 1000),
                error_code="mes_db_configuration_error",
                error_message=str(exc),
            )
        except SQLAlchemyError:
            return SqlExecutionResult(
                status="failed",
                duration_ms=int((time.perf_counter() - start) * 1000),
                error_code="mes_sql_execution_error",
                error_message="MES 只读查询执行失败。",
            )

    def _get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = _create_mes_engine(self._settings)
        return self._engine


def _create_mes_engine(settings: Settings) -> Engine:
    missing = [
        name
        for name, value in [
            ("AGENT_MES_DB_HOST", settings.agent_mes_db_host),
            ("AGENT_MES_DB_NAME", settings.agent_mes_db_name),
            ("AGENT_MES_DB_USER", settings.agent_mes_db_user),
            ("AGENT_MES_DB_PASSWORD", settings.agent_mes_db_password),
        ]
        if value is None or not str(value).strip()
    ]
    if missing:
        raise DatabaseConfigurationError(
            "Missing MES readonly database configuration: " + ", ".join(missing)
        )

    url = URL.create(
        "mysql+pymysql",
        username=settings.agent_mes_db_user,
        password=settings.agent_mes_db_password,
        host=settings.agent_mes_db_host,
        port=settings.agent_mes_db_port,
        database=settings.agent_mes_db_name,
        query={"charset": "utf8mb4"},
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        connect_args={"connect_timeout": settings.agent_mes_db_connect_timeout_seconds},
    )


def _json_safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe_value(value) for key, value in row.items()}


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)
