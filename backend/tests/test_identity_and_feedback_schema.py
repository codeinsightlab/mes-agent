import pytest
from pydantic import ValidationError

from app.domain.identity.context import IdentityContext
from app.schemas.feedback import FeedbackRequest


def test_identity_context_accepts_visitor_id():
    identity = IdentityContext(visitor_id=" visitor-1 ")

    assert identity.user_id is None
    assert identity.visitor_id == "visitor-1"
    assert identity.require_anonymous_visitor() == "visitor-1"


def test_identity_context_rejects_empty_identity():
    with pytest.raises(ValueError):
        IdentityContext()


def test_feedback_schema_rejects_empty_response_message_key():
    with pytest.raises(ValidationError):
        FeedbackRequest(
            response_message_key=" ",
            visitor_id="visitor-1",
            feedback_type=1,
        )


def test_feedback_schema_rejects_empty_visitor_id():
    with pytest.raises(ValidationError):
        FeedbackRequest(
            response_message_key="message-1",
            visitor_id=" ",
            feedback_type=1,
        )


def test_feedback_schema_rejects_invalid_feedback_type():
    with pytest.raises(ValidationError):
        FeedbackRequest(
            response_message_key="message-1",
            visitor_id="visitor-1",
            feedback_type=9,
        )


def test_feedback_schema_rejects_invalid_reason_type():
    with pytest.raises(ValidationError):
        FeedbackRequest(
            response_message_key="message-1",
            visitor_id="visitor-1",
            feedback_type=2,
            reason_type=9,
        )


def test_feedback_schema_rejects_like_with_reason_type():
    with pytest.raises(ValidationError):
        FeedbackRequest(
            response_message_key="message-1",
            visitor_id="visitor-1",
            feedback_type=1,
            reason_type=1,
        )


def test_feedback_schema_normalizes_blank_comment():
    request = FeedbackRequest(
        response_message_key="message-1",
        visitor_id="visitor-1",
        feedback_type=2,
        reason_type=1,
        comment="   ",
    )

    assert request.comment is None


def test_feedback_schema_rejects_long_comment():
    with pytest.raises(ValidationError):
        FeedbackRequest(
            response_message_key="message-1",
            visitor_id="visitor-1",
            feedback_type=2,
            reason_type=1,
            comment="x" * 1001,
        )
