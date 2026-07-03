class LlmError(Exception):
    """Base exception for provider-independent LLM failures."""


class LlmConfigurationError(LlmError):
    """Raised when model provider configuration is missing or invalid."""


class LlmAuthenticationError(LlmError):
    """Raised when the model provider rejects credentials."""


class LlmTimeoutError(LlmError):
    """Raised when the model provider request times out."""


class LlmUnavailableError(LlmError):
    """Raised when the model provider is rate-limited or temporarily unavailable."""


class LlmResponseFormatError(LlmError):
    """Raised when the model provider returns an unexpected response shape."""


class LlmCallError(LlmError):
    """Raised for generic model provider call failures."""
