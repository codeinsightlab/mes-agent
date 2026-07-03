from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import close_chat_service, router as chat_router
from app.core.config import get_settings


APP_NAME = "MES Agent Backend"
settings = get_settings()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
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
