"""Tests for gateway domain errors."""

from __future__ import annotations

from model_gateway.domain import (
    CancelledError,
    GatewayError,
    InvalidRequestError,
    TimeoutError,
    UpstreamError,
)


def test_gateway_error_exposes_code_and_message() -> None:
    """Base error stores machine-readable code and message."""
    err = GatewayError("bad", code="custom")
    assert err.code == "custom"
    assert err.message == "bad"
    assert str(err) == "bad"


def test_invalid_request_default_code() -> None:
    """InvalidRequestError uses the invalid_request code by default."""
    err = InvalidRequestError("nope")
    assert err.code == "invalid_request"


def test_upstream_error_default_code() -> None:
    """UpstreamError uses the upstream_error code by default."""
    err = UpstreamError("provider down")
    assert err.code == "upstream_error"


def test_timeout_error_default_code() -> None:
    """TimeoutError uses the timeout code by default."""
    err = TimeoutError("slow")
    assert err.code == "timeout"


def test_cancelled_error_default_code() -> None:
    """CancelledError uses the cancelled code by default."""
    err = CancelledError("aborted")
    assert err.code == "cancelled"


def test_subclasses_are_gateway_errors() -> None:
    """Typed errors remain instances of GatewayError."""
    assert isinstance(InvalidRequestError("x"), GatewayError)
    assert isinstance(TimeoutError("x"), GatewayError)
