from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.analytics.report.report_generator import MdReportGenerator
from app.analytics.report.repository import SqlAlchemyAnalyticsRepository
from app.core.config import get_settings
from app.domain.persistence.exceptions import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    PersistenceError,
)
from app.infrastructure.database.engine import check_database_connection, create_database_engine


router = APIRouter(prefix="/api/analytics/report", tags=["analytics-report"])
_report_generator: MdReportGenerator | None = None
_database_engine = None


class ReportGenerateRequest(BaseModel):
    type: Literal["daily", "failure", "health"]


class ReportGenerateResponse(BaseModel):
    type: str
    path: str
    status: str
    metrics: dict


def close_report_generator() -> None:
    global _report_generator, _database_engine
    _report_generator = None
    if _database_engine is not None:
        _database_engine.dispose()
        _database_engine = None


def get_report_generator() -> MdReportGenerator:
    global _report_generator, _database_engine
    if _report_generator is not None:
        return _report_generator
    try:
        settings = get_settings()
        _database_engine = create_database_engine(settings)
        check_database_connection(_database_engine)
        _report_generator = MdReportGenerator(
            repository=SqlAlchemyAnalyticsRepository(engine=_database_engine),
        )
        return _report_generator
    except DatabaseConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_configuration_error", "message": str(exc)},
        ) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "database_connection_error", "message": "Database connection failed."},
        ) from exc


@router.post("/generate", response_model=ReportGenerateResponse)
def generate_report(
    request: ReportGenerateRequest,
    generator: MdReportGenerator = Depends(get_report_generator),
):
    try:
        artifact = generator.generate(request.type)
    except PersistenceError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "analytics_report_generation_error", "message": str(exc)},
        ) from exc
    return ReportGenerateResponse(
        type=artifact.report_type,
        path=str(artifact.path),
        status="generated",
        metrics=artifact.metrics,
    )
