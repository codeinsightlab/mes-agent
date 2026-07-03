import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

APP_NAME = "MES Agent Backend"
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def parse_cors_origins(value):
    return [origin.strip() for origin in value.split(",") if origin.strip()]


cors_origins = parse_cors_origins(
    os.getenv("BACKEND_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
)

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "mes-agent-backend",
        "message": "Backend is reachable.",
    }
