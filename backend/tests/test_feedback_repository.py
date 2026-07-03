from app.infrastructure.database.repositories.feedback_repository import FeedbackRepository


class FakeScalarResult:
    def scalar_one_or_none(self):
        return None


class FakeSession:
    def __init__(self):
        self.statement = None
        self.added = []
        self.flushed = False

    def execute(self, statement):
        self.statement = statement
        return FakeScalarResult()

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flushed = True


def test_feedback_repository_query_active_by_message_and_visitor_filters_deleted():
    session = FakeSession()
    repository = FeedbackRepository(session)

    repository.get_active_by_message_and_visitor(message_id=1, visitor_id="visitor-1")

    sql = str(session.statement)
    assert "agent_feedback.message_id" in sql
    assert "agent_feedback.visitor_id" in sql
    assert "agent_feedback.deleted" in sql


def test_feedback_repository_create_and_update_use_same_session():
    session = FakeSession()
    repository = FeedbackRepository(session)

    feedback = repository.create(
        feedback_key="feedback-key",
        conversation_id=1,
        message_id=2,
        user_id=None,
        visitor_id="visitor-1",
        feedback_type=1,
        reason_type=None,
        comment=None,
        now=None,
    )
    repository.update(
        feedback=feedback,
        feedback_type=2,
        reason_type=1,
        comment="bad",
        now=None,
    )

    assert session.added == [feedback]
    assert session.flushed is True
    assert feedback.feedback_type == 2
