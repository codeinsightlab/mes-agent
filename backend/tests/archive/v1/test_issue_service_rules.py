import pytest

from app.application.issue_service import IssueApplicationService
from app.domain.issue.enums import IssueProcessStatus
from app.domain.issue.exceptions import IssueValidationError


def test_issue_service_requires_root_cause_when_located():
    service = IssueApplicationService(session_factory=object())

    with pytest.raises(IssueValidationError):
        service._validate_required_fields(
            IssueProcessStatus.LOCATED,
            root_cause_type=None,
            root_cause=None,
            solution=None,
        )


def test_issue_service_requires_solution_when_fixed():
    service = IssueApplicationService(session_factory=object())

    with pytest.raises(IssueValidationError):
        service._validate_required_fields(
            IssueProcessStatus.FIXED,
            root_cause_type=1,
            root_cause="root cause",
            solution=None,
        )


def test_issue_service_allows_fixed_with_root_cause_and_solution():
    service = IssueApplicationService(session_factory=object())

    service._validate_required_fields(
        IssueProcessStatus.FIXED,
        root_cause_type=1,
        root_cause="root cause",
        solution="solution",
    )
