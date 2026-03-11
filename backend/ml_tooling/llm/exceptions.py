"""Internal exception abstraction for LLM operations.

This module provides an abstraction layer over provider-specific exceptions
(e.g., LiteLLM) to decouple retry logic and tests from provider internals.
"""

from enum import Enum

# Import LiteLLM exceptions only when needed for standardization
# This keeps the coupling localized to this function
try:
    import litellm.exceptions as litellm_exceptions  # type: ignore[import-untyped]
except ImportError:
    litellm_exceptions = None  # type: ignore[assignment]


class ExceptionCategory(Enum):
    """Categorization of exceptions for retry decision logic."""

    AUTH_ERROR = "auth_error"
    INVALID_REQUEST = "invalid_request"
    TRANSIENT = "transient"
    UNRECOVERABLE = "unrecoverable"


class LLMException(Exception):
    """Base exception for all LLM-related errors.

    All LLM exceptions have a category that determines retry behavior,
    and preserve the original exception for debugging via exception chaining.
    """

    category: ExceptionCategory
    original_exception: Exception | None = None

    def __init__(self, message: str, original_exception: Exception | None = None) -> None:
        """Initialize LLM exception.

        Args:
            message: Human-readable error message
            original_exception: The original exception from the provider (e.g., LiteLLM)
                This will be chained via __cause__ for debugging
        """
        super().__init__(message)
        self.original_exception = original_exception
        if original_exception is not None:
            self.__cause__ = original_exception


class LLMAuthError(LLMException):
    """Authentication/authorization error - should not be retried."""

    category = ExceptionCategory.AUTH_ERROR


class LLMInvalidRequestError(LLMException):
    """Invalid request error (bad parameters, schema violations) - should not be retried."""

    category = ExceptionCategory.INVALID_REQUEST


class LLMPermissionDeniedError(LLMException):
    """Permission denied error - should not be retried."""

    category = ExceptionCategory.AUTH_ERROR  # Treated same as auth error for retry logic


class LLMTransientError(LLMException):
    """Transient error (rate limits, timeouts, service unavailable) - should be retried."""

    category = ExceptionCategory.TRANSIENT


class LLMUnrecoverableError(LLMException):
    """Unrecoverable error - should not be retried."""

    category = ExceptionCategory.UNRECOVERABLE


def _extract_exception_message(exception: Exception) -> str:
    message = getattr(exception, "message", str(exception))
    return message or f"{type(exception).__name__}: {exception}"


def _standardize_api_error(exception: Exception, message: str) -> LLMException:
    """Map APIError by status code: 5xx -> transient, else -> invalid_request."""
    status_code = getattr(exception, "status_code", None)
    if status_code and 500 <= status_code < 600:
        return LLMTransientError(message, original_exception=exception)
    return LLMInvalidRequestError(message, original_exception=exception)


def standardize_litellm_exception(exception: Exception) -> LLMException:
    """Standardize LiteLLM exceptions to internal exception types.

    This function serves as the boundary between provider-specific exceptions
    (LiteLLM) and our internal exception abstraction, allowing retry logic
    to be decoupled from provider internals.

    Args:
        exception: The LiteLLM exception that was raised

    Returns:
        Internal LLMException with appropriate category

    Note:
        The original exception is preserved via exception chaining (__cause__)
        for debugging purposes while maintaining clean retry logic.
    """
    if litellm_exceptions is None:
        return LLMTransientError(
            f"LiteLLM exception (LiteLLM not available): {exception}",
            original_exception=exception,
        )

    message = _extract_exception_message(exception)

    # Type -> internal exception class. Order matters: check specific before APIError.
    mappings: list[tuple[type[Exception], type[LLMException]]] = [
        (litellm_exceptions.AuthenticationError, LLMAuthError),  # type: ignore[attr-defined]
        (litellm_exceptions.PermissionDeniedError, LLMPermissionDeniedError),  # type: ignore[attr-defined]
        (litellm_exceptions.InvalidRequestError, LLMInvalidRequestError),  # type: ignore[attr-defined]
    ]
    if hasattr(litellm_exceptions, "BadRequestError"):
        mappings.append(
            (litellm_exceptions.BadRequestError, LLMInvalidRequestError)  # type: ignore[attr-defined]
        )
    for exc_type, llm_cls in mappings:
        if isinstance(exception, exc_type):
            return llm_cls(message, original_exception=exception)

    # Retryable (transient) exception types
    transient_types = (
        litellm_exceptions.RateLimitError,  # type: ignore[attr-defined]
        litellm_exceptions.Timeout,  # type: ignore[attr-defined]
        litellm_exceptions.ServiceUnavailableError,  # type: ignore[attr-defined]
    )
    if isinstance(exception, transient_types):
        return LLMTransientError(message, original_exception=exception)

    if isinstance(exception, litellm_exceptions.APIError):  # type: ignore[attr-defined]
        return _standardize_api_error(exception, message)

    return LLMTransientError(f"Unknown LiteLLM error: {message}", original_exception=exception)
