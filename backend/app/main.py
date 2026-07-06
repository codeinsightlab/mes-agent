from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_issue import close_admin_issue_services, router as admin_issue_router
from app.api.agent import close_agent_query_service, router as agent_router
from app.api.analytics_report import (
    close_report_generator,
    get_report_generator,
    router as analytics_report_router,
)
from app.api.chat import close_chat_service, router as chat_router
from app.api.feedback import close_feedback_service, router as feedback_router
from app.analytics.metrics.snapshot import MetricsSnapshotScheduler, MetricsSnapshotService
from app.analytics.report.scheduler import DailyReportScheduler
from app.core.config import get_settings
from app.domain.persistence.exceptions import PersistenceError
from app.infrastructure.database.engine import (
    check_database_connection,
    create_database_engine,
)


APP_NAME = "MES Agent Backend"
logger = logging.getLogger(__name__)
settings = get_settings()
_report_scheduler: DailyReportScheduler | None = None
_metrics_snapshot_scheduler: MetricsSnapshotScheduler | None = None
_metrics_snapshot_engine = None


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    global _report_scheduler, _metrics_snapshot_scheduler, _metrics_snapshot_engine
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
    if settings.analytics_report_scheduler_enabled:
        try:
            _report_scheduler = DailyReportScheduler(get_report_generator())
            _report_scheduler.start()
            logger.info("Analytics report scheduler started daily_time=00:10")
        except Exception as exc:
            logger.error(
                "Analytics report scheduler startup failed exception_type=%s",
                type(exc).__name__,
            )
    if settings.analytics_metrics_snapshot_enabled:
        try:
            _metrics_snapshot_engine = create_database_engine(settings)
            _metrics_snapshot_scheduler = MetricsSnapshotScheduler(
                MetricsSnapshotService(_metrics_snapshot_engine),
                interval_minutes=settings.analytics_metrics_snapshot_interval_minutes,
            )
            _metrics_snapshot_scheduler.start()
            logger.info(
                "Analytics metrics snapshot scheduler started interval_minutes=%s",
                settings.analytics_metrics_snapshot_interval_minutes,
            )
        except Exception as exc:
            logger.error(
                "Analytics metrics snapshot scheduler startup failed exception_type=%s",
                type(exc).__name__,
            )
    yield
    if _report_scheduler is not None:
        _report_scheduler.stop()
        _report_scheduler = None
    if _metrics_snapshot_scheduler is not None:
        _metrics_snapshot_scheduler.stop()
        _metrics_snapshot_scheduler = None
    if _metrics_snapshot_engine is not None:
        _metrics_snapshot_engine.dispose()
        _metrics_snapshot_engine = None
    close_agent_query_service()
    close_report_generator()
    close_admin_issue_services()
    close_chat_service()
    close_feedback_service()


app = FastAPI(title=APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(admin_issue_router)
app.include_router(agent_router)
app.include_router(analytics_report_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "mes-agent-backend",
        "message": "Backend is reachable.",
    }
