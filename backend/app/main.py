from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import close_chat_service, router as chat_router
from app.core.config import get_settings
from app.domain.persistence.exceptions import PersistenceError
from app.infrastructure.database.engine import (
    check_database_connection,
    create_database_engine,
)


APP_NAME = "MES Agent Backend"
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info("Backend settings loaded env_file=%s", settings.env_file_path)
    try:
        startup_engine = create_database_engine(settings)
        try:
            check_database_connection(startup_engine)
        finally:
            startup_engine.dispose()
    except PersistenceError as exc:
        logger.error(
            "Database startup check failed exception_type=%s",
            type(exc).__name__,
        )
    yield
    close_chat_service()


app = FastAPI(title=APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "mes-agent-backend",
        "message": "Backend is reachable.",
    }
