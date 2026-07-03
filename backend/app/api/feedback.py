from fastapi import APIRouter, Depends, HTTPException

from app.application.feedback_service import (
    FeedbackApplicationService,
    FeedbackCommand,
    FeedbackResult,
)
from app.core.config import get_settings
from app.domain.feedback.exceptions import (
    FeedbackPersistenceError,
    FeedbackTargetNotAssistantError,
    FeedbackTargetNotFoundError,
    FeedbackValidationError,
)
from app.domain.identity.context import IdentityContext
from app.domain.persistence.exceptions import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
)
from app.infrastructure.database.engine import (
    check_database_connection,
    create_database_engine,
)
from app.infrastructure.database.session import create_session_factory
from app.schemas.feedback import FeedbackRequest, FeedbackResponse


router = APIRouter(prefix="/api", tags=["feedback"])
_feedback_service: FeedbackApplicationService | None = None
_database_engine = None


def get_feedback_service() -> FeedbackApplicationService:
    global _feedback_service, _database_engine
    if _feedback_service is not None:
        return _feedback_service

    try:
        settings = get_settings()
        _database_engine = create_database_engine(settings)
        check_database_connection(_database_engine)
        _feedback_service = FeedbackApplicationService(
            create_session_factory(_database_engine)
        )
        return _feedback_service
    except DatabaseConfigurationError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "database_configuration_error", "message": str(exc)},
        ) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "database_connection_error",
                "message": "Database connection failed.",
            },
        ) from exc


def close_feedback_service():
    global _feedback_service, _database_engine
    _feedback_service = None
    if _database_engine is not None:
        _database_engine.dispose()
        _database_engine = None


def to_api_response(result: FeedbackResult) -> FeedbackResponse:
    return FeedbackResponse(
        feedback_key=result.feedback_key,
        response_message_key=result.response_message_key,
        feedback_type=result.feedback_type,
        feedback_type_label=result.feedback_type_label,
        reason_type=result.reason_type,
        reason_type_label=result.reason_type_label,
        comment=result.comment,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(
    request: FeedbackRequest,
    service: FeedbackApplicationService = Depends(get_feedback_service),
):
    try:
        identity = IdentityContext(user_id=None, visitor_id=request.visitor_id)
        command = FeedbackCommand(
            response_message_key=request.response_message_key,
            feedback_type=request.feedback_type,
            reason_type=request.reason_type,
            comment=request.comment,
        )
        return to_api_response(service.submit_feedback(identity, command))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_identity", "message": str(exc)},
        ) from exc
    except FeedbackValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_feedback", "message": str(exc)},
        ) from exc
    except FeedbackTargetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "feedback_target_not_found",
                "message": "Feedback target message was not found.",
            },
        ) from exc
    except FeedbackTargetNotAssistantError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "feedback_target_not_assistant",
                "message": "Feedback target must be an assistant message.",
            },
        ) from exc
    except FeedbackPersistenceError as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "feedback_persistence_error", "message": "Failed to save feedback."},
        ) from exc
