import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.feedback.enums import FeedbackType
from app.domain.issue.enums import (
    IssuePriority,
    IssueProcessStatus,
    IssueRootCauseType,
    issue_priority_label,
    issue_root_cause_type_label,
    issue_status_label,
)
from app.domain.issue.exceptions import (
    FeedbackNotDislikedError,
    FeedbackNotFoundError,
    InvalidIssueTransitionError,
    IssueNotFoundError,
    IssuePersistenceError,
    IssueValidationError,
)
from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository
from app.infrastructure.database.repositories.issue_repository import IssueRepository
from app.infrastructure.database.session import session_scope


logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS = {
    IssueProcessStatus.PENDING: {IssueProcessStatus.ANALYZING, IssueProcessStatus.IGNORED},
    IssueProcessStatus.ANALYZING: {IssueProcessStatus.LOCATED, IssueProcessStatus.IGNORED},
    IssueProcessStatus.LOCATED: {IssueProcessStatus.FIXED, IssueProcessStatus.IGNORED, IssueProcessStatus.ANALYZING},
    IssueProcessStatus.FIXED: {IssueProcessStatus.CLOSED, IssueProcessStatus.LOCATED},
    IssueProcessStatus.IGNORED: {IssueProcessStatus.CLOSED},
    IssueProcessStatus.CLOSED: set(),
}


class IssueApplicationService:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def create_issue(self, feedback_key: str, priority: int = IssuePriority.MEDIUM):
        logger.info("Issue create requested feedback_key=%s priority=%s", feedback_key, priority)
        try:
            priority_enum = IssuePriority(priority)
            with session_scope(self._session_factory) as session:
                feedbacks = FeedbackRepository(session)
                issues = IssueRepository(session)
                feedback = feedbacks.get_by_feedback_key(feedback_key)
                if feedback is None or feedback.deleted != 0:
                    raise FeedbackNotFoundError("Feedback not found.")
                if feedback.feedback_type != FeedbackType.DISLIKE:
                    raise FeedbackNotDislikedError("Only disliked feedback can create issue.")
                existing = issues.get_by_feedback_id(feedback.id)
                if existing is not None:
                    result = self._issue(existing, feedback.feedback_key)
                else:
                    now = self._utc_now()
                    issue = issues.create(
                        issue_key=self._new_key(),
                        feedback_id=feedback.id,
                        process_status=IssueProcessStatus.PENDING,
                        priority=int(priority_enum),
                        now=now,
                    )
                    result = self._issue(issue, feedback.feedback_key)
            logger.info(
                "Issue created transaction committed feedback_key=%s issue_key=%s priority=%s",
                feedback_key,
                result["issue_key"],
                priority,
            )
            return result
        except (FeedbackNotFoundError, FeedbackNotDislikedError):
            raise
        except ValueError as exc:
            raise IssueValidationError("Unsupported issue field value.") from exc
        except SQLAlchemyError as exc:
            logger.error(
                "Issue create failed feedback_key=%s exception_type=%s",
                feedback_key,
                type(exc).__name__,
            )
            raise IssuePersistenceError("Failed to create issue.") from exc

    def get_issue(self, issue_key: str):
        try:
            with session_scope(self._session_factory) as session:
                issues = IssueRepository(session)
                issue = issues.get_by_issue_key(issue_key)
                if issue is None:
                    raise IssueNotFoundError("Issue not found.")
                return self._issue(issue, self._feedback_key(session, issue.feedback_id))
        except IssueNotFoundError:
            raise
        except SQLAlchemyError as exc:
            raise IssuePersistenceError("Failed to query issue.") from exc

    def list_issues(self, page: int, page_size: int, **filters):
        try:
            with session_scope(self._session_factory) as session:
                rows, total = IssueRepository(session).list_issues(
                    page=page,
                    page_size=page_size,
                    **filters,
                )
                return {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "items": [self._issue(issue, feedback.feedback_key, detail=False) for issue, feedback in rows],
                }
        except SQLAlchemyError as exc:
            raise IssuePersistenceError("Failed to list issues.") from exc

    def update_issue(self, issue_key: str, **changes):
        logger.info("Issue update requested issue_key=%s", issue_key)
        try:
            with session_scope(self._session_factory) as session:
                issue_repository = IssueRepository(session)
                issue = issue_repository.get_by_issue_key(issue_key)
                if issue is None:
                    raise IssueNotFoundError("Issue not found.")
                old_status = IssueProcessStatus(issue.process_status)
                new_status = IssueProcessStatus(changes.get("process_status") or issue.process_status)
                if new_status != old_status and new_status not in ALLOWED_TRANSITIONS[old_status]:
                    raise InvalidIssueTransitionError("Issue status transition is not allowed.")
                if old_status == IssueProcessStatus.CLOSED and new_status == IssueProcessStatus.CLOSED:
                    raise InvalidIssueTransitionError("Closed issue cannot be modified.")

                priority = int(IssuePriority(changes.get("priority") or issue.priority))
                root_cause_type = changes.get("root_cause_type", issue.root_cause_type)
                if root_cause_type is not None:
                    root_cause_type = int(IssueRootCauseType(root_cause_type))
                root_cause = changes.get("root_cause", issue.root_cause)
                solution = changes.get("solution", issue.solution)
                processed_by = changes.get("processed_by", issue.processed_by)
                self._validate_required_fields(new_status, root_cause_type, root_cause, solution)
                now = self._utc_now()
                processed_at = issue.processed_at
                if new_status in {
                    IssueProcessStatus.FIXED,
                    IssueProcessStatus.IGNORED,
                    IssueProcessStatus.CLOSED,
                }:
                    processed_at = now
                updated = issue_repository.update(
                    issue=issue,
                    process_status=int(new_status),
                    priority=priority,
                    root_cause_type=root_cause_type,
                    root_cause=root_cause,
                    solution=solution,
                    processed_by=processed_by,
                    processed_at=processed_at,
                    now=now,
                )
                result = self._issue(updated, self._feedback_key(session, updated.feedback_id))
            logger.info(
                "Issue updated transaction committed issue_key=%s old_status=%s new_status=%s priority=%s",
                issue_key,
                int(old_status),
                result["process_status"],
                result["priority"],
            )
            return result
        except (
            IssueNotFoundError,
            InvalidIssueTransitionError,
            IssueValidationError,
        ):
            raise
        except ValueError as exc:
            raise IssueValidationError("Unsupported issue field value.") from exc
        except SQLAlchemyError as exc:
            logger.error(
                "Issue update failed issue_key=%s exception_type=%s",
                issue_key,
                type(exc).__name__,
            )
            raise IssuePersistenceError("Failed to update issue.") from exc

    def _validate_required_fields(
        self,
        status: IssueProcessStatus,
        root_cause_type: int | None,
        root_cause: str | None,
        solution: str | None,
    ):
        if status in {IssueProcessStatus.LOCATED, IssueProcessStatus.FIXED}:
            if root_cause_type is None or not root_cause:
                raise IssueValidationError("Located or fixed issue requires root cause.")
        if status == IssueProcessStatus.FIXED and not solution:
            raise IssueValidationError("Fixed issue requires solution.")

    def _feedback_key(self, session: Session, feedback_id: int) -> str:
        from app.infrastructure.database.models.feedback import AgentFeedback

        return session.get_one(AgentFeedback, feedback_id).feedback_key

    def _issue(self, issue, feedback_key: str, detail: bool = True):
        data = {
            "issue_key": issue.issue_key,
            "feedback_key": feedback_key,
            "process_status": issue.process_status,
            "process_status_label": issue_status_label(issue.process_status),
            "priority": issue.priority,
            "priority_label": issue_priority_label(issue.priority),
            "root_cause_type": issue.root_cause_type,
            "root_cause_type_label": issue_root_cause_type_label(issue.root_cause_type),
            "processed_by": issue.processed_by,
            "processed_at": issue.processed_at,
            "created_at": issue.created_at,
            "updated_at": issue.updated_at,
        }
        if detail:
            data["root_cause"] = issue.root_cause
            data["solution"] = issue.solution
        return data

    def _new_key(self) -> str:
        return uuid.uuid4().hex

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)
