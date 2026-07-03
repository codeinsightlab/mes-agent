from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.database.models.feedback import AgentFeedback
from app.infrastructure.database.models.issue import AgentIssue


class IssueRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_feedback_id(self, feedback_id: int) -> AgentIssue | None:
        statement = select(AgentIssue).where(AgentIssue.feedback_id == feedback_id)
        return self._session.execute(statement).scalar_one_or_none()

    def get_by_issue_key(self, issue_key: str) -> AgentIssue | None:
        statement = select(AgentIssue).where(AgentIssue.issue_key == issue_key)
        return self._session.execute(statement).scalar_one_or_none()

    def create(
        self,
        issue_key: str,
        feedback_id: int,
        process_status: int,
        priority: int,
        now: datetime,
    ) -> AgentIssue:
        issue = AgentIssue(
            issue_key=issue_key,
            feedback_id=feedback_id,
            process_status=process_status,
            priority=priority,
            root_cause_type=None,
            root_cause=None,
            solution=None,
            processed_by=None,
            processed_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(issue)
        self._session.flush()
        return issue

    def update(
        self,
        issue: AgentIssue,
        process_status: int,
        priority: int,
        root_cause_type: int | None,
        root_cause: str | None,
        solution: str | None,
        processed_by: str | None,
        processed_at: datetime | None,
        now: datetime,
    ) -> AgentIssue:
        issue.process_status = process_status
        issue.priority = priority
        issue.root_cause_type = root_cause_type
        issue.root_cause = root_cause
        issue.solution = solution
        issue.processed_by = processed_by
        issue.processed_at = processed_at
        issue.updated_at = now
        self._session.flush()
        return issue

    def list_issues(
        self,
        page: int,
        page_size: int,
        process_status: int | None = None,
        priority: int | None = None,
        root_cause_type: int | None = None,
        feedback_reason_type: int | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[tuple[AgentIssue, AgentFeedback]], int]:
        statement = select(AgentIssue, AgentFeedback).join(
            AgentFeedback,
            AgentFeedback.id == AgentIssue.feedback_id,
        )
        statement = self._apply_filters(
            statement,
            process_status=process_status,
            priority=priority,
            root_cause_type=root_cause_type,
            feedback_reason_type=feedback_reason_type,
            created_from=created_from,
            created_to=created_to,
        )
        total = self._session.execute(
            select(func.count()).select_from(statement.subquery())
        ).scalar_one()
        rows = self._session.execute(
            statement.order_by(AgentIssue.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [(row[0], row[1]) for row in rows], total

    def _apply_filters(self, statement, **filters):
        if filters["process_status"] is not None:
            statement = statement.where(AgentIssue.process_status == filters["process_status"])
        if filters["priority"] is not None:
            statement = statement.where(AgentIssue.priority == filters["priority"])
        if filters["root_cause_type"] is not None:
            statement = statement.where(AgentIssue.root_cause_type == filters["root_cause_type"])
        if filters["feedback_reason_type"] is not None:
            statement = statement.where(AgentFeedback.reason_type == filters["feedback_reason_type"])
        if filters["created_from"] is not None:
            statement = statement.where(AgentIssue.created_at >= filters["created_from"])
        if filters["created_to"] is not None:
            statement = statement.where(AgentIssue.created_at <= filters["created_to"])
        return statement
