import pytest

from app.infrastructure.database.session import session_scope


class FakeSession:
    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_session_scope_commits_and_closes():
    session = FakeSession()

    with session_scope(lambda: session):
        pass

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_session_scope_rolls_back_on_error():
    session = FakeSession()

    with pytest.raises(RuntimeError):
        with session_scope(lambda: session):
            raise RuntimeError("boom")

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True
