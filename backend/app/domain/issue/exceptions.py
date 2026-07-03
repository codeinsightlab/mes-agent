class IssueError(Exception):
    pass


class FeedbackNotFoundError(IssueError):
    pass


class FeedbackNotDislikedError(IssueError):
    pass


class IssueNotFoundError(IssueError):
    pass


class InvalidIssueTransitionError(IssueError):
    pass


class IssueValidationError(IssueError):
    pass


class IssuePersistenceError(IssueError):
    pass
