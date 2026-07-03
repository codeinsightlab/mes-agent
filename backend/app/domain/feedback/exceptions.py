class FeedbackError(Exception):
    pass


class FeedbackValidationError(FeedbackError):
    pass


class FeedbackTargetNotFoundError(FeedbackError):
    pass


class FeedbackTargetNotAssistantError(FeedbackError):
    pass


class FeedbackPersistenceError(FeedbackError):
    pass
