"""Mapping tests for the OpenAI Responses translator. No network."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx2
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from openai.types.responses import Response
from openai.types.responses.response import IncompleteDetails

from model_gateway.adapters.outbound.openai import (
    exception_to_gateway_error,
    to_generation_response,
    to_responses_create_kwargs,
)
from model_gateway.domain import (
    CancelledError,
    GenerationRequest,
    GenerationStatus,
    IncompleteReason,
    InputMessage,
    InvalidRequestError,
    TimeoutError,
    UpstreamError,
)

CREATED_AT = 1_763_636_400
_ALLOWED_KEYS = frozenset({"model", "input", "stream", "instructions", "max_output_tokens"})


def _request(
    *,
    instructions: str | None = None,
    messages: list[InputMessage] | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        model="gpt-4.1-mini",
        input=messages or [InputMessage(role="user", content="Hello")],
        instructions=instructions,
    )


def _text_message(text: str, message_id: str = "msg_1") -> dict[str, object]:
    return {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def _response(**overrides: object) -> Response:
    payload: dict[str, object] = {
        "id": "resp_1",
        "created_at": CREATED_AT,
        "model": "gpt-4.1-mini",
        "object": "response",
        "status": "completed",
        "parallel_tool_calls": False,
        "tool_choice": "none",
        "tools": [],
        "output": [_text_message("Hello")],
    }
    payload.update(overrides)
    return Response.model_validate(payload)


def _status_error(
    error_type: type[APIStatusError],
    status_code: int,
    message: str,
) -> APIStatusError:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(status_code, request=request)
    return error_type(message, response=response, body=None)


def test_request_omits_optional_fields_and_disables_streaming() -> None:
    """A bare request sends model, text input, and stream false only."""
    params = to_responses_create_kwargs(_request())

    assert set(params) <= _ALLOWED_KEYS
    assert params["model"] == "gpt-4.1-mini"
    assert params["stream"] is False
    assert "instructions" not in params
    assert "max_output_tokens" not in params
    assert params["input"] == [{"role": "user", "content": "Hello"}]


def test_request_includes_instructions_max_tokens_and_history() -> None:
    """Instructions, max tokens, and user/assistant turns are passed through."""
    request = _request(
        instructions="Be brief.",
        messages=[
            InputMessage(role="user", content="Hello"),
            InputMessage(role="assistant", content="Hi"),
            InputMessage(role="user", content="Again"),
        ],
    )
    request.config.max_output_tokens = 32

    params = to_responses_create_kwargs(request)

    assert params["instructions"] == "Be brief."
    assert params["max_output_tokens"] == 32
    assert params["input"] == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Again"},
    ]


def test_completed_response_maps_usage_and_timestamp() -> None:
    """Completed text keeps provider usage, including cached and reasoning tokens."""
    response = _response(
        usage={
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "input_tokens_details": {"cached_tokens": 2, "cache_write_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 3},
        }
    )

    mapped = to_generation_response(response)

    assert mapped.id == "resp_1"
    assert mapped.model == "gpt-4.1-mini"
    assert mapped.status is GenerationStatus.COMPLETED
    assert mapped.output_text == "Hello"
    assert mapped.refusal is None
    assert mapped.incomplete_reason is None
    assert mapped.created_at == datetime.fromtimestamp(CREATED_AT, tz=UTC)
    assert mapped.usage is not None
    assert mapped.usage.input_tokens == 10
    assert mapped.usage.output_tokens == 5
    assert mapped.usage.total_tokens == 15
    assert mapped.usage.cached_input_tokens == 2
    assert mapped.usage.reasoning_output_tokens == 3


def test_missing_usage_stays_absent() -> None:
    """A result without usage does not invent token counts."""
    mapped = to_generation_response(_response())

    assert mapped.usage is None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("max_output_tokens", IncompleteReason.MAX_OUTPUT_TOKENS),
        ("content_filter", IncompleteReason.CONTENT_FILTER),
        ("max_messages", IncompleteReason.OTHER),
        ("steered", IncompleteReason.OTHER),
        (None, IncompleteReason.OTHER),
    ],
)
def test_incomplete_reason_mapping(reason: str | None, expected: IncompleteReason) -> None:
    """Known incomplete reasons map directly; anything else becomes other."""
    details = None if reason is None else {"reason": reason}
    mapped = to_generation_response(
        _response(
            status="incomplete",
            incomplete_details=details,
            output=[_text_message("Partial")],
        )
    )

    assert mapped.status is GenerationStatus.INCOMPLETE
    assert mapped.incomplete_reason is expected
    assert mapped.output_text == "Partial"
    assert mapped.refusal is None


def test_unknown_incomplete_reason_maps_to_other() -> None:
    """A reason outside the current SDK enum still becomes other."""
    response = _response(status="incomplete", output=[_text_message("Partial")])
    response.incomplete_details = IncompleteDetails.model_construct(reason="brand_new")

    mapped = to_generation_response(response)

    assert mapped.incomplete_reason is IncompleteReason.OTHER


def test_refusal_clears_output_text() -> None:
    """A refusal wins over any text in the same result."""
    mapped = to_generation_response(
        _response(
            output=[
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": "hidden", "annotations": []},
                        {"type": "refusal", "refusal": "safety"},
                    ],
                }
            ]
        )
    )

    assert mapped.status is GenerationStatus.COMPLETED
    assert not mapped.output_text
    assert mapped.refusal is not None
    assert mapped.refusal.reason == "safety"


def test_incomplete_result_drops_refusal() -> None:
    """Incomplete status keeps the text because refusal is not allowed there."""
    mapped = to_generation_response(
        _response(
            status="incomplete",
            incomplete_details={"reason": "max_output_tokens"},
            output=[
                {
                    "id": "msg_1",
                    "type": "message",
                    "role": "assistant",
                    "status": "incomplete",
                    "content": [
                        {"type": "output_text", "text": "Partial", "annotations": []},
                        {"type": "refusal", "refusal": "safety"},
                    ],
                }
            ],
        )
    )

    assert mapped.status is GenerationStatus.INCOMPLETE
    assert mapped.output_text == "Partial"
    assert mapped.refusal is None
    assert mapped.incomplete_reason is IncompleteReason.MAX_OUTPUT_TOKENS


def test_failed_status_raises_upstream_error() -> None:
    """A failed Responses result is an upstream error, not a generation."""
    response = _response(
        status="failed",
        error={"code": "server_error", "message": "upstream blew up"},
        output=[],
    )

    with pytest.raises(UpstreamError, match="upstream blew up") as caught:
        to_generation_response(response)

    assert caught.value.code == "upstream_failed"


def test_failed_status_without_error_uses_fallback_message() -> None:
    """A failed result with no provider message still raises a stable error."""
    with pytest.raises(UpstreamError, match="OpenAI generation failed.") as caught:
        to_generation_response(_response(status="failed", output=[]))

    assert caught.value.code == "upstream_failed"


def test_cancelled_status_raises_cancelled_error() -> None:
    """Provider-reported cancellation becomes the domain cancelled error."""
    response = _response(
        status="cancelled",
        error={"code": "server_error", "message": "client gone"},
        output=[],
    )

    with pytest.raises(CancelledError, match="client gone") as caught:
        to_generation_response(response)

    assert caught.value.code == "cancelled"


@pytest.mark.parametrize("status", ["in_progress", "queued", None])
def test_unexpected_status_raises_upstream_error(status: str | None) -> None:
    """Non-terminal statuses are rejected instead of being treated as success."""
    with pytest.raises(UpstreamError, match="unexpected status") as caught:
        to_generation_response(_response(status=status, output=[]))

    assert caught.value.code == "upstream_unexpected_status"


@pytest.mark.parametrize(
    ("error_type", "status_code", "expected_type", "expected_code"),
    [
        (BadRequestError, 400, InvalidRequestError, "invalid_request"),
        (UnprocessableEntityError, 422, InvalidRequestError, "invalid_request"),
        (NotFoundError, 404, InvalidRequestError, "model_not_found"),
        (AuthenticationError, 401, UpstreamError, "upstream_auth"),
        (PermissionDeniedError, 403, UpstreamError, "upstream_auth"),
        (RateLimitError, 429, UpstreamError, "upstream_rate_limited"),
        (InternalServerError, 500, UpstreamError, "upstream_unavailable"),
    ],
)
def test_status_errors_map_to_gateway_errors(
    error_type: type[APIStatusError],
    status_code: int,
    expected_type: type[Exception],
    expected_code: str,
) -> None:
    """HTTP status errors use the existing gateway taxonomy and stable codes."""
    mapped = exception_to_gateway_error(_status_error(error_type, status_code, "provider said no"))

    assert isinstance(mapped, expected_type)
    assert mapped.code == expected_code
    assert mapped.message == "provider said no"


def test_timeout_and_connection_errors() -> None:
    """Timeout and connection failures do not become generic upstream errors."""
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")

    timeout = exception_to_gateway_error(APITimeoutError(request))
    connection = exception_to_gateway_error(APIConnectionError(request=request))

    assert isinstance(timeout, TimeoutError)
    assert timeout.code == "timeout"
    assert timeout.message == "Request timed out."
    assert isinstance(connection, UpstreamError)
    assert connection.code == "upstream_unavailable"


def test_unclassified_status_error_stays_upstream() -> None:
    """A status outside the known table remains a generic upstream error."""
    mapped = exception_to_gateway_error(_status_error(APIStatusError, 409, "conflict"))

    assert isinstance(mapped, UpstreamError)
    assert mapped.code == "upstream_error"
    assert mapped.message == "conflict"


def test_server_status_without_internal_error_type_is_unavailable() -> None:
    """Any 5xx status is unavailable, even when the SDK uses the base class."""
    mapped = exception_to_gateway_error(_status_error(APIStatusError, 503, "down"))

    assert isinstance(mapped, UpstreamError)
    assert mapped.code == "upstream_unavailable"
