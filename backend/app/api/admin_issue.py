from fastapi import APIRouter, Depends, HTTPException, Query

from app.application.feedback_review_service import FeedbackReviewService
from app.application.issue_service import IssueApplicationService
from app.core.config import get_settings
from app.domain.issue.exceptions import (
    FeedbackNotDislikedError,
    FeedbackNotFoundError,
    InvalidIssueTransitionError,
    IssueNotFoundError,
    IssuePersistenceError,
    IssueValidationError,
)
from app.domain.persistence.exceptions import DatabaseConfigurationError, DatabaseConnectionError
from app.infrastructure.database.engine import check_database_connection, create_database_engine
from app.infrastructure.database.session import create_session_factory
from app.schemas.issue import (
    CreateIssueRequest,
    DislikedFeedbackDetailResponse,
    DislikedFeedbackListQuery,
    DislikedFeedbackListResponse,
    IssueDetailResponse,
    IssueListQuery,
    IssueListResponse,
    UpdateIssueRequest,
)


router = APIRouter(prefix="/api/admin", tags=["admin-issues"])
_review_service: FeedbackReviewService | None = None
_issue_service: IssueApplicationService | None = None
_database_engine = None


def _init_services():
    global _review_service, _issue_service, _database_engine
    if _review_service is not None and _issue_service is not None:
        return
    try:
        settings = get_settings()
        _database_engine = create_database_engine(settings)
        check_database_connection(_database_engine)
        session_factory = create_session_factory(_database_engine)
        _review_service = FeedbackReviewService(session_factory)
        _issue_service = IssueApplicationService(session_factory)
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


def get_review_service() -> FeedbackReviewService:
    _init_services()
    assert _review_service is not None
    return _review_service


def get_issue_service() -> IssueApplicationService:
    _init_services()
    assert _issue_service is not None
    return _issue_service


def close_admin_issue_services():
    global _review_service, _issue_service, _database_engine
    _review_service = None
    _issue_service = None
    if _database_engine is not None:
        _database_engine.dispose()
        _database_engine = None


@router.get("/feedbacks/disliked", response_model=DislikedFeedbackListResponse)
def list_disliked_feedbacks(
    reason_type: int | None = Query(default=None),
    has_issue: bool | None = Query(default=None),
    issue_status: int | None = Query(default=None),
    feedback_key: str | None = Query(default=None),
    response_message_key: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: FeedbackReviewService = Depends(get_review_service),
):
    query = DislikedFeedbackListQuery(
        reason_type=reason_type,
        has_issue=has_issue,
        issue_status=issue_status,
        feedback_key=feedback_key,
        response_message_key=response_message_key,
        page=page,
        page_size=page_size,
    )
    try:
        return service.list_disliked_feedbacks(**query.model_dump())
    except IssuePersistenceError as exc:
        raise _server_error("feedback_query_error", "Failed to query disliked feedbacks.") from exc


@router.get("/feedbacks/{feedback_key}", response_model=DislikedFeedbackDetailResponse)
def get_disliked_feedback_detail(
    feedback_key: str,
    service: FeedbackReviewService = Depends(get_review_service),
):
    try:
        return service.get_disliked_feedback_detail(feedback_key)
    except FeedbackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "feedback_not_found", "message": "Disliked feedback was not found."},
        ) from exc
    except IssuePersistenceError as exc:
        raise _server_error("feedback_query_error", "Failed to query disliked feedback detail.") from exc


@router.post("/issues", response_model=IssueDetailResponse)
def create_issue(
    request: CreateIssueRequest,
    service: IssueApplicationService = Depends(get_issue_service),
):
    try:
        return service.create_issue(
            feedback_key=request.feedback_key,
            priority=request.priority,
        )
    except FeedbackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "feedback_not_found", "message": "Feedback was not found."},
        ) from exc
    except FeedbackNotDislikedError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "feedback_not_disliked", "message": "Only disliked feedback can create issue."},
        ) from exc
    except IssueValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_issue", "message": str(exc)},
        ) from exc
    except IssuePersistenceError as exc:
        raise _server_error("issue_persistence_error", "Failed to create issue.") from exc


@router.get("/issues", response_model=IssueListResponse)
def list_issues(
    process_status: int | None = Query(default=None),
    priority: int | None = Query(default=None),
    root_cause_type: int | None = Query(default=None),
    feedback_reason_type: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: IssueApplicationService = Depends(get_issue_service),
):
    query = IssueListQuery(
        process_status=process_status,
        priority=priority,
        root_cause_type=root_cause_type,
        feedback_reason_type=feedback_reason_type,
        page=page,
        page_size=page_size,
    )
    try:
        return service.list_issues(**query.model_dump())
    except IssuePersistenceError as exc:
        raise _server_error("issue_query_error", "Failed to list issues.") from exc


@router.get("/issues/{issue_key}", response_model=IssueDetailResponse)
def get_issue(
    issue_key: str,
    service: IssueApplicationService = Depends(get_issue_service),
):
    try:
        return service.get_issue(issue_key)
    except IssueNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "issue_not_found", "message": "Issue was not found."},
        ) from exc
    except IssuePersistenceError as exc:
        raise _server_error("issue_query_error", "Failed to query issue.") from exc


@router.put("/issues/{issue_key}", response_model=IssueDetailResponse)
def update_issue(
    issue_key: str,
    request: UpdateIssueRequest,
    service: IssueApplicationService = Depends(get_issue_service),
):
    try:
        return service.update_issue(issue_key, **request.model_dump(exclude_unset=True))
    except IssueNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "issue_not_found", "message": "Issue was not found."},
        ) from exc
    except InvalidIssueTransitionError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "invalid_issue_transition", "message": str(exc)},
        ) from exc
    except IssueValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_issue", "message": str(exc)},
        ) from exc
    except IssuePersistenceError as exc:
        raise _server_error("issue_persistence_error", "Failed to update issue.") from exc


def _server_error(error: str, message: str) -> HTTPException:
    return HTTPException(status_code=500, detail={"error": error, "message": message})
