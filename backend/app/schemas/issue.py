from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.feedback.enums import FeedbackReasonType
from app.domain.issue.enums import (
    IssuePriority,
    IssueProcessStatus,
    IssueRootCauseType,
)


class CreateIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_key: str = Field(..., min_length=1, max_length=64)
    priority: int = IssuePriority.MEDIUM

    @field_validator("feedback_key")
    @classmethod
    def strip_feedback_key(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("feedback_key cannot be empty.")
        return stripped

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int) -> int:
        try:
            IssuePriority(value)
        except ValueError as exc:
            raise ValueError("priority is not supported.") from exc
        return value


class UpdateIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_status: int | None = None
    priority: int | None = None
    root_cause_type: int | None = None
    root_cause: str | None = Field(default=None, max_length=4000)
    solution: str | None = Field(default=None, max_length=4000)
    processed_by: str | None = Field(default=None, max_length=64)

    @field_validator("process_status")
    @classmethod
    def validate_process_status(cls, value: int | None) -> int | None:
        if value is None:
            return None
        try:
            IssueProcessStatus(value)
        except ValueError as exc:
            raise ValueError("process_status is not supported.") from exc
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int | None) -> int | None:
        if value is None:
            return None
        try:
            IssuePriority(value)
        except ValueError as exc:
            raise ValueError("priority is not supported.") from exc
        return value

    @field_validator("root_cause_type")
    @classmethod
    def validate_root_cause_type(cls, value: int | None) -> int | None:
        if value is None:
            return None
        try:
            IssueRootCauseType(value)
        except ValueError as exc:
            raise ValueError("root_cause_type is not supported.") from exc
        return value

    @field_validator("root_cause", "solution", "processed_by")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class DislikedFeedbackListQuery(BaseModel):
    reason_type: int | None = None
    has_issue: bool | None = None
    issue_status: int | None = None
    feedback_key: str | None = None
    response_message_key: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("reason_type")
    @classmethod
    def validate_reason_type(cls, value: int | None) -> int | None:
        if value is None:
            return None
        try:
            FeedbackReasonType(value)
        except ValueError as exc:
            raise ValueError("reason_type is not supported.") from exc
        return value

    @field_validator("issue_status")
    @classmethod
    def validate_issue_status(cls, value: int | None) -> int | None:
        if value is None:
            return None
        try:
            IssueProcessStatus(value)
        except ValueError as exc:
            raise ValueError("issue_status is not supported.") from exc
        return value

    @field_validator("feedback_key", "response_message_key")
    @classmethod
    def normalize_optional_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class IssueListQuery(BaseModel):
    process_status: int | None = None
    priority: int | None = None
    root_cause_type: int | None = None
    feedback_reason_type: int | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("process_status")
    @classmethod
    def validate_process_status(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return IssueProcessStatus(value)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return IssuePriority(value)

    @field_validator("root_cause_type")
    @classmethod
    def validate_root_cause_type(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return IssueRootCauseType(value)

    @field_validator("feedback_reason_type")
    @classmethod
    def validate_reason_type(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return FeedbackReasonType(value)


class IssueSummaryResponse(BaseModel):
    issue_key: str
    feedback_key: str
    process_status: int
    process_status_label: str
    priority: int
    priority_label: str
    root_cause_type: int | None = None
    root_cause_type_label: str | None = None
    processed_by: str | None = None
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IssueDetailResponse(IssueSummaryResponse):
    root_cause: str | None = None
    solution: str | None = None


class PageResponse(BaseModel):
    page: int
    page_size: int
    total: int


class IssueListResponse(PageResponse):
    items: list[IssueSummaryResponse]


class DislikedFeedbackSummaryResponse(BaseModel):
    feedback_key: str
    response_message_key: str
    reason_type: int | None = None
    reason_type_label: str | None = None
    comment: str | None = None
    visitor_digest: str | None = None
    assistant_content_summary: str | None = None
    user_message_content_summary: str | None = None
    conversation_key: str
    model: str | None = None
    provider: str | None = None
    agent_version: str | None = None
    prompt_version: str | None = None
    tool_version: str | None = None
    created_at: datetime
    has_issue: bool
    issue_key: str | None = None
    issue_status: int | None = None
    issue_status_label: str | None = None


class DislikedFeedbackListResponse(PageResponse):
    items: list[DislikedFeedbackSummaryResponse]


class MessageSceneResponse(BaseModel):
    message_key: str
    role: int
    content: str
    sequence_no: int
    created_at: datetime


class ModelCallSceneResponse(BaseModel):
    call_key: str | None = None
    provider: str | None = None
    model: str | None = None
    agent_version: str | None = None
    prompt_version: str | None = None
    tool_version: str | None = None
    system_prompt_snapshot: str | None = None
    request_snapshot: str | None = None
    response_snapshot: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    duration_ms: int | None = None
    finish_reason: str | None = None
    call_status: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None


class DislikedFeedbackDetailResponse(BaseModel):
    feedback_key: str
    feedback_type: int
    reason_type: int | None = None
    reason_type_label: str | None = None
    comment: str | None = None
    visitor_digest: str | None = None
    created_at: datetime
    updated_at: datetime
    conversation_key: str
    user_message: MessageSceneResponse | None = None
    assistant_message: MessageSceneResponse
    model_call: ModelCallSceneResponse | None = None
    has_issue: bool
    issue: IssueDetailResponse | None = None
