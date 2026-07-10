from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import SQLAlchemyError

import app.application.feedback_service as feedback_module
from app.application.feedback_service import FeedbackApplicationService, FeedbackCommand
from app.domain.feedback.exceptions import (
    FeedbackPersistenceError,
    FeedbackTargetNotAssistantError,
    FeedbackTargetNotFoundError,
)
from app.domain.identity.context import IdentityContext


@dataclass
class FakeMessage:
    id: int
    message_key: str
    conversation_id: int
    role: int = 3
    message_status: int = 1


@dataclass
class FakeFeedback:
    id: int
    feedback_key: str
    conversation_id: int
    message_id: int
    user_id: str | None
    visitor_id: str | None
    deleted: int
    feedback_type: int
    reason_type: int | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class FakeSession:
    def __init__(self, state):
        self.state = state
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class FakeMessageRepository:
    def __init__(self, session):
        self._session = session

    def get_by_message_key(self, message_key):
        return self._session.state["messages"].get(message_key)


class FakeFeedbackRepository:
    def __init__(self, session):
        self._session = session

    def get_active_by_message_and_visitor(self, message_id, visitor_id):
        for feedback in self._session.state["feedbacks"]:
            if (
                feedback.message_id == message_id
                and feedback.visitor_id == visitor_id
                and feedback.deleted == 0
            ):
                return feedback
        return None

    def get_active_by_message_and_user(self, message_id, user_id):
        for feedback in self._session.state["feedbacks"]:
            if (
                feedback.message_id == message_id
                and feedback.user_id == user_id
                and feedback.deleted == 0
            ):
                return feedback
        return None

    def create(
        self,
        feedback_key,
        conversation_id,
        message_id,
        user_id,
        visitor_id,
        feedback_type,
        reason_type,
        comment,
        now,
    ):
        if self._session.state.get("fail_create"):
            raise SQLAlchemyError("create failed")
        feedback = FakeFeedback(
            id=len(self._session.state["feedbacks"]) + 1,
            feedback_key=feedback_key,
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id,
            visitor_id=visitor_id,
            deleted=0,
            feedback_type=feedback_type,
            reason_type=reason_type,
            comment=comment,
            created_at=now,
            updated_at=now,
        )
        self._session.state["feedbacks"].append(feedback)
        return feedback

    def update(self, feedback, feedback_type, reason_type, comment, now):
        feedback.feedback_type = feedback_type
        feedback.reason_type = reason_type
        feedback.comment = comment
        feedback.updated_at = now
        return feedback


@pytest.fixture
def feedback_state(monkeypatch):
    state = {
        "messages": {
            "assistant-1": FakeMessage(id=1, message_key="assistant-1", conversation_id=10),
            "assistant-2": FakeMessage(id=2, message_key="assistant-2", conversation_id=10),
            "user-1": FakeMessage(id=3, message_key="user-1", conversation_id=10, role=2),
        },
        "feedbacks": [],
        "sessions": [],
    }

    def session_factory():
        session = FakeSession(state)
        state["sessions"].append(session)
        return session

    monkeypatch.setattr(feedback_module, "MessageRepository", FakeMessageRepository)
    monkeypatch.setattr(feedback_module, "FeedbackRepository", FakeFeedbackRepository)
    return state, session_factory


def test_feedback_service_target_not_found(feedback_state):
    _, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)

    with pytest.raises(FeedbackTargetNotFoundError):
        service.submit_feedback(
            IdentityContext(visitor_id="visitor-1"),
            FeedbackCommand(response_message_key="missing", feedback_type=1),
        )


def test_feedback_service_rejects_non_assistant_message(feedback_state):
    _, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)

    with pytest.raises(FeedbackTargetNotAssistantError):
        service.submit_feedback(
            IdentityContext(visitor_id="visitor-1"),
            FeedbackCommand(response_message_key="user-1", feedback_type=1),
        )


def test_feedback_service_first_like_creates_feedback(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)

    result = service.submit_feedback(
        IdentityContext(visitor_id="visitor-1"),
        FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
    )

    assert result.feedback_type == 1
    assert result.reason_type is None
    assert result.comment is None
    assert len(state["feedbacks"]) == 1
    assert state["sessions"][-1].committed is True


def test_feedback_service_first_dislike_creates_feedback(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)

    result = service.submit_feedback(
        IdentityContext(visitor_id="visitor-1"),
        FeedbackCommand(
            response_message_key="assistant-1",
            feedback_type=2,
            reason_type=1,
            comment="  too vague  ",
        ),
    )

    assert result.feedback_type == 2
    assert result.reason_type == 1
    assert result.comment == "too vague"
    assert len(state["feedbacks"]) == 1


def test_feedback_service_repeated_same_feedback_updates_without_insert(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)
    identity = IdentityContext(visitor_id="visitor-1")
    command = FeedbackCommand(response_message_key="assistant-1", feedback_type=1)

    first = service.submit_feedback(identity, command)
    second = service.submit_feedback(identity, command)

    assert first.feedback_key == second.feedback_key
    assert len(state["feedbacks"]) == 1


def test_feedback_service_like_to_dislike_updates_original(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)
    identity = IdentityContext(visitor_id="visitor-1")

    first = service.submit_feedback(
        identity,
        FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
    )
    second = service.submit_feedback(
        identity,
        FeedbackCommand(
            response_message_key="assistant-1",
            feedback_type=2,
            reason_type=2,
            comment="wrong",
        ),
    )

    assert first.feedback_key == second.feedback_key
    assert second.feedback_type == 2
    assert second.reason_type == 2
    assert second.comment == "wrong"
    assert len(state["feedbacks"]) == 1


def test_feedback_service_dislike_to_like_clears_reason_and_comment(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)
    identity = IdentityContext(visitor_id="visitor-1")

    service.submit_feedback(
        identity,
        FeedbackCommand(
            response_message_key="assistant-1",
            feedback_type=2,
            reason_type=1,
            comment="bad",
        ),
    )
    result = service.submit_feedback(
        identity,
        FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
    )

    assert result.feedback_type == 1
    assert result.reason_type is None
    assert result.comment is None
    assert len(state["feedbacks"]) == 1


def test_feedback_service_same_visitor_can_feedback_different_messages(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)
    identity = IdentityContext(visitor_id="visitor-1")

    service.submit_feedback(
        identity,
        FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
    )
    service.submit_feedback(
        identity,
        FeedbackCommand(response_message_key="assistant-2", feedback_type=1),
    )

    assert len(state["feedbacks"]) == 2


def test_feedback_service_different_visitors_can_feedback_same_message(feedback_state):
    state, session_factory = feedback_state
    service = FeedbackApplicationService(session_factory)

    service.submit_feedback(
        IdentityContext(visitor_id="visitor-1"),
        FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
    )
    service.submit_feedback(
        IdentityContext(visitor_id="visitor-2"),
        FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
    )

    assert len(state["feedbacks"]) == 2


def test_feedback_service_persistence_failure_rolls_back(feedback_state):
    state, session_factory = feedback_state
    state["fail_create"] = True
    service = FeedbackApplicationService(session_factory)

    with pytest.raises(FeedbackPersistenceError):
        service.submit_feedback(
            IdentityContext(visitor_id="visitor-1"),
            FeedbackCommand(response_message_key="assistant-1", feedback_type=1),
        )

    assert state["sessions"][-1].rolled_back is True
