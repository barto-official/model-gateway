"""RFC 7807 problem details for gateway HTTP errors."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

from model_gateway.domain.errors import (
    CancelledError,
    GatewayError,
    InvalidRequestError,
    TimeoutError,
    UpstreamError,
)

PROBLEM_JSON = "application/problem+json"


class ProblemDetail(BaseModel):
    """RFC 7807 problem detail with a gateway ``code`` extension."""

    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: str | None = None
    instance: str | None = None


_INVALID_REQUEST_STATUS: dict[str, int] = {
    "model_not_found": 404,
    "provider_not_configured": 503,
    "provider_not_available": 503,
}


def gateway_error_status(error: GatewayError) -> int:
    """Map a domain gateway error to an HTTP status code.

    Returns:
        HTTP status to use in the problem detail response.
    """
    if isinstance(error, InvalidRequestError):
        return _INVALID_REQUEST_STATUS.get(error.code, 422)
    status_by_type: dict[type[GatewayError], int] = {
        UpstreamError: 502,
        TimeoutError: 504,
        CancelledError: 499,
    }
    return status_by_type.get(type(error), 500)


def problem_from_gateway_error(error: GatewayError, *, instance: str | None) -> ProblemDetail:
    """Build a problem response from a :class:`GatewayError`.

    Returns:
        RFC 7807 problem detail for the error.
    """
    status = gateway_error_status(error)
    return ProblemDetail(
        title=error.__class__.__name__,
        status=status,
        detail=error.message,
        code=error.code,
        instance=instance,
    )


def problem_from_validation(
    errors: Sequence[Mapping[str, Any]],
    *,
    instance: str | None,
) -> ProblemDetail:
    """Build a problem response from request validation failures.

    Returns:
        RFC 7807 problem detail with status 422.
    """
    detail = "; ".join(
        f"{'.'.join(str(part) for part in err.get('loc', ()))}: {err.get('msg', 'invalid')}"
        for err in errors
    )
    return ProblemDetail(
        title="Validation Error",
        status=422,
        detail=detail or "Request validation failed.",
        code="invalid_request",
        instance=instance,
    )


async def gateway_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Translate domain errors to RFC 7807 JSON responses.

    Returns:
        JSON response with ``application/problem+json`` media type.
    """
    if not isinstance(exc, GatewayError):
        raise exc
    problem = problem_from_gateway_error(exc, instance=str(request.url.path))
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON,
    )


async def request_validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Translate FastAPI request validation errors to problem details.

    Returns:
        JSON response with ``application/problem+json`` media type.
    """
    if not isinstance(exc, RequestValidationError):
        raise exc
    problem = problem_from_validation(exc.errors(), instance=str(request.url.path))
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON,
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Translate Pydantic validation errors raised outside FastAPI parsing.

    Returns:
        JSON response with ``application/problem+json`` media type.
    """
    if not isinstance(exc, PydanticValidationError):
        raise exc
    problem = problem_from_validation(exc.errors(), instance=str(request.url.path))
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON,
    )
