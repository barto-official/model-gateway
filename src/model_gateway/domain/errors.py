"""Gateway error types for non-success outcomes."""

from __future__ import annotations


class GatewayError(Exception):
    """Base error with a stable machine-readable code and human message.

    Attributes:
        code: Stable identifier for clients and logs.
        message: Human-readable explanation.
    """

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InvalidRequestError(GatewayError):
    """Raised when the client or domain request fails validation."""

    def __init__(self, message: str, *, code: str = "invalid_request") -> None:
        super().__init__(message, code=code)


class UpstreamError(GatewayError):
    """Raised when an upstream provider returns an error or unexpected response."""

    def __init__(self, message: str, *, code: str = "upstream_error") -> None:
        super().__init__(message, code=code)


class TimeoutError(GatewayError):
    """Raised when a generation call exceeds its time budget."""

    def __init__(self, message: str, *, code: str = "timeout") -> None:
        super().__init__(message, code=code)


class CancelledError(GatewayError):
    """Raised when a generation call is cancelled before completion."""

    def __init__(self, message: str, *, code: str = "cancelled") -> None:
        super().__init__(message, code=code)
