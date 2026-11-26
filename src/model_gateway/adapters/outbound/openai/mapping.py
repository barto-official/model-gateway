"""Translate canonical text generation to the OpenAI Responses API.

This module covers non-streaming text only. Multimedia, files, tools, and
streaming stay outside this translation. Task cancellation is not handled
here; callers must let ``asyncio.CancelledError`` propagate.
"""

from __future__ import annotations

from datetime import UTC, datetime

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from openai.types.responses import Response
from openai.types.responses.easy_input_message_param import EasyInputMessageParam
from openai.types.responses.response_create_params import ResponseCreateParamsNonStreaming
from openai.types.responses.response_input_param import ResponseInputParam
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_refusal import ResponseOutputRefusal

from model_gateway.domain.errors import (
    CancelledError,
    GatewayError,
    InvalidRequestError,
    TimeoutError,
    UpstreamError,
)
from model_gateway.domain.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    IncompleteReason,
    ResponseRefusal,
    TokenUsage,
)

_INCOMPLETE_REASONS = {
    "max_output_tokens": IncompleteReason.MAX_OUTPUT_TOKENS,
    "content_filter": IncompleteReason.CONTENT_FILTER,
}
_SUCCESS_STATUSES = frozenset({"completed", "incomplete"})


def to_responses_create_kwargs(request: GenerationRequest) -> ResponseCreateParamsNonStreaming:
    """Build non-streaming Responses API arguments from a generation request.

    Args:
        request: Canonical text-generation request.

    Returns:
        Arguments for ``AsyncOpenAI.responses.create`` with streaming disabled.
    """
    items: ResponseInputParam = []
    for message in request.input:
        item: EasyInputMessageParam = {
            "role": message.role,
            "content": message.content,
        }
        items.append(item)

    params: ResponseCreateParamsNonStreaming = {
        "model": request.model,
        "input": items,
        "stream": False,
    }
    if request.instructions is not None:
        params["instructions"] = request.instructions
    if request.config.max_output_tokens is not None:
        params["max_output_tokens"] = request.config.max_output_tokens
    return params


def to_generation_response(response: Response) -> GenerationResponse:
    """Map a completed or incomplete Responses result to the domain response.

    Failed, cancelled, and unexpected statuses raise a gateway error instead of
    returning a partial result. A refusal replaces any text in the same result.
    An incomplete result keeps its text and drops a refusal, because the domain
    model forbids refusal on an incomplete generation.

    Args:
        response: Non-streaming Responses API result.

    Returns:
        Canonical generation response.

    Raises:
        UpstreamError: When the provider failed or returned an unexpected status.
        CancelledError: When the provider reports that generation was cancelled.
    """
    status = response.status
    if status == "failed":
        raise UpstreamError(
            _provider_message(response, "OpenAI generation failed."),
            code="upstream_failed",
        )
    if status == "cancelled":
        raise CancelledError(_provider_message(response, "OpenAI cancelled the generation."))
    if status not in _SUCCESS_STATUSES:
        raise UpstreamError(
            f"OpenAI returned unexpected status {status!r}.",
            code="upstream_unexpected_status",
        )

    refusal_text = None if status == "incomplete" else _first_refusal(response)
    refusal = None if refusal_text is None else ResponseRefusal(reason=refusal_text)
    incomplete_reason = _incomplete_reason(response) if status == "incomplete" else None
    generation_status = (
        GenerationStatus.INCOMPLETE if status == "incomplete" else GenerationStatus.COMPLETED
    )
    return GenerationResponse(
        id=response.id,
        model=response.model,
        status=generation_status,
        output_text="" if refusal is not None else response.output_text,
        refusal=refusal,
        incomplete_reason=incomplete_reason,
        usage=_token_usage(response),
        created_at=datetime.fromtimestamp(response.created_at, tz=UTC),
    )


def exception_to_gateway_error(exc: APIError) -> GatewayError:
    """Translate an OpenAI SDK error into a gateway error.

    Args:
        exc: Error raised by the OpenAI SDK. This does not accept
            ``asyncio.CancelledError``.

    Returns:
        The gateway error callers should see. Provider messages are preserved.
    """
    if isinstance(exc, APITimeoutError):
        return TimeoutError(exc.message)
    if isinstance(exc, APIConnectionError):
        return UpstreamError(exc.message, code="upstream_unavailable")
    if isinstance(exc, APIStatusError):
        return _status_error_to_gateway_error(exc)
    return UpstreamError(exc.message, code="upstream_error")


def _status_error_to_gateway_error(exc: APIStatusError) -> GatewayError:
    if isinstance(exc, BadRequestError | UnprocessableEntityError):
        return InvalidRequestError(exc.message)
    if isinstance(exc, NotFoundError):
        return InvalidRequestError(exc.message, code="model_not_found")
    if isinstance(exc, AuthenticationError | PermissionDeniedError):
        return UpstreamError(exc.message, code="upstream_auth")
    if isinstance(exc, RateLimitError):
        return UpstreamError(exc.message, code="upstream_rate_limited")
    if exc.status_code >= 500:
        return UpstreamError(exc.message, code="upstream_unavailable")
    return UpstreamError(exc.message, code="upstream_error")


def _provider_message(response: Response, fallback: str) -> str:
    error = response.error
    if error is None:
        return fallback
    message = error.message.strip()
    return message or fallback


def _incomplete_reason(response: Response) -> IncompleteReason:
    details = response.incomplete_details
    if details is None or details.reason is None:
        return IncompleteReason.OTHER
    return _INCOMPLETE_REASONS.get(details.reason, IncompleteReason.OTHER)


def _first_refusal(response: Response) -> str | None:
    for item in response.output:
        if not isinstance(item, ResponseOutputMessage):
            continue
        for content in item.content:
            if isinstance(content, ResponseOutputRefusal):
                return content.refusal
    return None


def _token_usage(response: Response) -> TokenUsage | None:
    usage = response.usage
    if usage is None:
        return None
    return TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        cached_input_tokens=usage.input_tokens_details.cached_tokens,
        reasoning_output_tokens=usage.output_tokens_details.reasoning_tokens,
    )
