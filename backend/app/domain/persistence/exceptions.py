class PersistenceError(Exception):
    """Base exception for persistence failures."""


class DatabaseConfigurationError(PersistenceError):
    """Raised when database configuration is missing or invalid."""


class DatabaseConnectionError(PersistenceError):
    """Raised when the database cannot be reached."""


class ConversationInitializationError(PersistenceError):
    """Raised when the initial conversation records cannot be saved."""


class ModelResultPersistenceError(PersistenceError):
    """Raised when a model success or failure result cannot be saved."""
