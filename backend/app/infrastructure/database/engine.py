import logging

from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.domain.persistence.exceptions import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
)


logger = logging.getLogger(__name__)


def create_database_engine(settings: Settings) -> Engine:
    missing = [
        name
        for name, value in (
            ("DB_HOST", settings.db_host),
            ("DB_NAME", settings.db_name),
            ("DB_USER", settings.db_user),
            ("DB_PASSWORD", settings.db_password),
        )
        if not value
    ]
    if missing:
        raise DatabaseConfigurationError(
            f"Missing database configuration: {', '.join(missing)}."
        )

    url = URL.create(
        drivername="mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        query={"charset": "utf8mb4"},
    )

    logger.info(
        "Creating database engine driver=%s host=%s port=%s database=%s user=%s",
        "mysql+pymysql",
        settings.db_host,
        settings.db_port,
        settings.db_name,
        settings.db_user,
    )

    return create_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


def check_database_connection(engine: Engine) -> str:
    try:
        with engine.connect() as connection:
            database_name = connection.execute(text("SELECT DATABASE()")).scalar_one()
            connection.execute(text("SELECT 1")).scalar_one()
            logger.info("Database connectivity check succeeded database=%s", database_name)
            return database_name
    except SQLAlchemyError as exc:
        logger.error(
            "Database connectivity check failed exception_type=%s",
            type(exc).__name__,
        )
        raise DatabaseConnectionError("Database connectivity check failed.") from exc
