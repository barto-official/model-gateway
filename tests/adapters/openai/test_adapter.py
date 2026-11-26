"""Tests for the OpenAI inference backend adapter."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from pathlib import Path

import httpx2
import pytest
from pydantic import SecretStr

from model_gateway.adapters.outbound.config.settings import OpenAISettings
from model_gateway.adapters.outbound.openai.adapter import (
    OpenAIInferenceBackend,
    create_openai_backend,
)
from model_gateway.application.generate_text import GenerateTextUseCase
from model_gateway.domain import (
    GenerationRequest,
    GenerationStatus,
    InputMessage,
    InvalidRequestError,
    TimeoutError,
    UpstreamError,
)

CREATED_AT = 1_763_636_400
RESPONSES_PATH = "/v1/responses"
_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "model_gateway"
_OPENAI_IMPORT = re.compile(r"^\s*(from openai|import openai)\b", re.MULTILINE)


def _completed_response_payload(text: str = "Hello") -> dict[str, object]:
    return {
        "id": "resp_test",
        "created_at": CREATED_AT,
        "model": "gpt-4.1-mini",
        "object": "response",
        "status": "completed",
        "parallel_tool_calls": False,
        "tool_choice": "none",
        "tools": [],
        "output": [
            {
                "id": "msg_1",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
    }


def _openai_settings() -> OpenAISettings:
    return OpenAISettings(api_key=SecretStr("sk-test-key"))


def _backend_with_transport(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> tuple[OpenAIInferenceBackend, httpx2.AsyncClient]:
    transport = httpx2.MockTransport(handler)
    http_client = httpx2.AsyncClient(transport=transport)
    backend = create_openai_backend(_openai_settings(), http_client=http_client)
    return backend, http_client


def test_create_openai_backend_rejects_missing_api_key() -> None:
    """Factory fails fast when credentials are absent."""
    with pytest.raises(InvalidRequestError, match="not configured") as caught:
        create_openai_backend(OpenAISettings())

    assert caught.value.code == "provider_not_configured"


def test_create_openai_backend_does_not_leak_api_key_in_repr() -> None:
    """Backend string form must not expose secrets."""
    backend = create_openai_backend(_openai_settings())

    text = repr(backend)
    assert "sk-test-key" not in text
    assert "sk-test" not in text


def test_generate_posts_responses_payload_without_stream_or_tools() -> None:
    """The SDK call uses Responses create with text-only fields."""
    captured: dict[str, object] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "POST"
        assert request.url.path.endswith(RESPONSES_PATH)
        body = json.loads(request.content)
        captured.update(body)
        return httpx2.Response(200, json=_completed_response_payload("Hi there"))

    backend, http_client = _backend_with_transport(handler)
    try:
        request = GenerationRequest(
            model="gpt-4.1-mini",
            instructions="Be concise.",
            input=[
                InputMessage(role="user", content="Hello"),
                InputMessage(role="assistant", content="Hi"),
                InputMessage(role="user", content="Again"),
            ],
        )
        request.config.max_output_tokens = 64

        response = asyncio.run(backend.generate(request))

        assert captured["model"] == "gpt-4.1-mini"
        assert captured["stream"] is False
        assert captured["instructions"] == "Be concise."
        assert captured["max_output_tokens"] == 64
        assert "tools" not in captured
        assert captured["input"] == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Again"},
        ]
        assert response.status is GenerationStatus.COMPLETED
        assert response.output_text == "Hi there"
    finally:
        asyncio.run(http_client.aclose())


@pytest.mark.parametrize(
    ("status_code", "body", "expected_type", "expected_code"),
    [
        (400, {"error": {"message": "bad request"}}, InvalidRequestError, "invalid_request"),
        (404, {"error": {"message": "missing model"}}, InvalidRequestError, "model_not_found"),
        (401, {"error": {"message": "unauthorized"}}, UpstreamError, "upstream_auth"),
        (429, {"error": {"message": "slow down"}}, UpstreamError, "upstream_rate_limited"),
        (500, {"error": {"message": "oops"}}, UpstreamError, "upstream_unavailable"),
    ],
)
def test_generate_maps_http_errors(
    status_code: int,
    body: dict[str, object],
    expected_type: type[Exception],
    expected_code: str,
) -> None:
    """HTTP failures from the SDK are translated before they leave the adapter."""

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, json=body)

    backend, http_client = _backend_with_transport(handler)
    try:
        with pytest.raises(expected_type, match=body["error"]["message"]) as caught:  # type: ignore[index]
            asyncio.run(
                backend.generate(
                    GenerationRequest(
                        model="gpt-4.1-mini",
                        input=[InputMessage(role="user", content="Hello")],
                    )
                )
            )
        assert caught.value.code == expected_code
    finally:
        asyncio.run(http_client.aclose())


def test_generate_timeout_maps_to_domain_timeout() -> None:
    """Read timeouts surface as gateway timeout errors."""

    def handler(_: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout(
            "timed out", request=httpx2.Request("POST", "https://api.openai.com")
        )

    backend, http_client = _backend_with_transport(handler)
    try:
        with pytest.raises(TimeoutError, match="timed out"):
            asyncio.run(
                backend.generate(
                    GenerationRequest(
                        model="gpt-4.1-mini",
                        input=[InputMessage(role="user", content="Hello")],
                    )
                )
            )
    finally:
        asyncio.run(http_client.aclose())


def test_backend_satisfies_contract_through_use_case() -> None:
    """Completed generation works end-to-end through the application use case."""

    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=_completed_response_payload("use-case"))

    backend, http_client = _backend_with_transport(handler)
    try:
        use_case = GenerateTextUseCase(backend)
        response = asyncio.run(
            use_case.execute(
                GenerationRequest(
                    model="gpt-4.1-mini",
                    input=[InputMessage(role="user", content="Hello")],
                )
            )
        )
        assert response.output_text == "use-case"
        assert response.status is GenerationStatus.COMPLETED
    finally:
        asyncio.run(http_client.aclose())


def test_openai_sdk_imports_stay_inside_openai_adapter_package() -> None:
    """The OpenAI SDK must not leak into domain, application, or other adapters."""
    openai_adapter = _SRC_ROOT / "adapters" / "outbound" / "openai"

    for path in _SRC_ROOT.rglob("*.py"):
        relative = path.relative_to(_SRC_ROOT)
        parts = relative.parts
        if parts[:3] == ("adapters", "outbound", "openai"):
            continue
        source = path.read_text(encoding="utf-8")
        match = _OPENAI_IMPORT.search(source)
        assert match is None, f"{relative} must not import the OpenAI SDK"

    for path in openai_adapter.glob("*.py"):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        assert _OPENAI_IMPORT.search(source) is not None, f"{path.name} should use the OpenAI SDK"
