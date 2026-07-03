from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

from app.core.config import Settings
from app.domain.persistence.exceptions import DatabaseConfigurationError


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

    return create_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )
