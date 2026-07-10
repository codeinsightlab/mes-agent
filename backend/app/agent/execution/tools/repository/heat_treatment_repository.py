import time
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL

from app.core.config import Settings, get_settings
from app.domain.persistence.exceptions import DatabaseConfigurationError


HEAT_CURRENT_STAGE_SQL = (
    "SELECT record_no, status "
    "FROM mes_heat_treatment_record "
    "WHERE record_no = :record_no "
    "LIMIT 1"
)
HEAT_CURRENT_STAGE_TABLE = "mes_heat_treatment_record"


@dataclass(frozen=True)
class HeatCurrentStageRecord:
    found: bool
    record_no: str
    status: str | None


@dataclass(frozen=True)
class HeatTreatmentRepositoryTrace:
    sql: str
    used_tables: list[str]
    sql_executed: bool
    sql_valid: bool
    duration_ms: int
    error_type: str | None = None


class HeatTreatmentRepository:
    def __init__(self, engine: Engine | None = None, settings: Settings | None = None):
        self._engine = engine
        self._settings = settings

    def get_heat_current_stage(
        self,
        record_no: str,
    ) -> tuple[HeatCurrentStageRecord, HeatTreatmentRepositoryTrace]:
        start = time.perf_counter()
        with self._get_engine().connect() as connection:
            row = connection.execute(
                text(HEAT_CURRENT_STAGE_SQL),
                {"record_no": record_no},
            ).mappings().first()
        duration_ms = int((time.perf_counter() - start) * 1000)
        trace = HeatTreatmentRepositoryTrace(
            sql=HEAT_CURRENT_STAGE_SQL,
            used_tables=[HEAT_CURRENT_STAGE_TABLE],
            sql_executed=True,
            sql_valid=True,
            duration_ms=duration_ms,
            error_type=None if row is not None else "not_found",
        )
        if row is None:
            return (
                HeatCurrentStageRecord(found=False, record_no=record_no, status=None),
                trace,
            )
        return (
            HeatCurrentStageRecord(
                found=True,
                record_no=str(row["record_no"]),
                status=str(row["status"]) if row["status"] is not None else None,
            ),
            trace,
        )

    def _get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = _create_mes_engine(self._settings or get_settings())
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
