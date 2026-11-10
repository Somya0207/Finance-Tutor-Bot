"""Application-level errors that the UI can show to the user as-is."""


class AppError(Exception):
    """Base class for errors with a user-friendly message."""


class LLMConfigError(AppError):
    """The LLM is not configured (e.g. missing API key)."""


class LLMError(AppError):
    """The LLM request failed (network, rate limit, bad key, ...)."""


class KnowledgeBaseEmpty(AppError):
    """There are no documents to build or search the knowledge base from."""


class VoiceError(AppError):
    """Speech-to-text or text-to-speech failed."""


class AuthError(AppError):
    """Registration or login problem."""
