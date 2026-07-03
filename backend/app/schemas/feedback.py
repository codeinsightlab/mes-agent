from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.feedback.enums import FeedbackReasonType, FeedbackType


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_message_key: str = Field(..., min_length=1, max_length=64)
    visitor_id: str = Field(..., min_length=1, max_length=64)
    feedback_type: int
    reason_type: int | None = None
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("response_message_key", "visitor_id")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty.")
        return stripped

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, value: int) -> int:
        try:
            FeedbackType(value)
        except ValueError as exc:
            raise ValueError("feedback_type must be 1 or 2.") from exc
        return value

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

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_feedback_combination(self):
        if self.feedback_type == FeedbackType.LIKE and self.reason_type is not None:
            raise ValueError("reason_type must be empty when feedback_type is like.")
        return self


class FeedbackResponse(BaseModel):
    feedback_key: str
    response_message_key: str
    feedback_type: int
    feedback_type_label: str
    reason_type: int | None = None
    reason_type_label: str | None = None
    comment: str | None = None
    created_at: datetime
    updated_at: datetime
