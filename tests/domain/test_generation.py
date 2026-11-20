"""Tests for generation domain models."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from model_gateway.domain import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    IncompleteReason,
    InputMessage,
    ResponseRefusal,
    TokenUsage,
)

DOMAIN_ROOT = Path(__file__).resolve().parents[2] / "src" / "model_gateway" / "domain"
FORBIDDEN_DOMAIN_IMPORTS = ("fastapi", "openai", "httpx")


def _completed_response_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "gen-1",
        "model": "gpt-4o-mini",
        "status": GenerationStatus.COMPLETED,
        "output_text": "Hello",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    base.update(overrides)
    return base


def test_generation_request_happy_path() -> None:
    """Valid request with defaults for config."""
    request = GenerationRequest(
        model="gpt-4o-mini",
        input=[InputMessage(role="user", content="Hi")],
    )
    assert request.config.max_output_tokens is None
    assert request.instructions is None


def test_input_message_rejects_empty_content() -> None:
    """Message content must be non-empty."""
    with pytest.raises(ValidationError):
        InputMessage(role="user", content="")


def test_generation_request_rejects_empty_input() -> None:
    """At least one input message is required."""
    with pytest.raises(ValidationError):
        GenerationRequest(model="gpt-4o-mini", input=[])


def test_generation_request_forbids_extra_fields() -> None:
    """Unknown fields are rejected on strict schema types."""
    with pytest.raises(ValidationError):
        GenerationRequest(
            model="gpt-4o-mini",
            input=[InputMessage(role="user", content="Hi")],
            stream=True,  # type: ignore[call-arg]
        )


def test_generation_config_rejects_non_positive_max_output_tokens() -> None:
    """max_output_tokens must be greater than zero when set."""
    with pytest.raises(ValidationError):
        GenerationRequest(
            model="gpt-4o-mini",
            input=[InputMessage(role="user", content="Hi")],
            config={"max_output_tokens": 0},  # type: ignore[arg-type]
        )


def test_incomplete_response_requires_reason() -> None:
    """INCOMPLETE status requires incomplete_reason."""
    with pytest.raises(ValidationError, match="incomplete_reason"):
        GenerationResponse(
            **_completed_response_kwargs(
                status=GenerationStatus.INCOMPLETE,
                output_text="partial",
            ),
        )


def test_completed_response_rejects_incomplete_reason() -> None:
    """COMPLETED status must not carry incomplete_reason."""
    with pytest.raises(ValidationError, match="incomplete_reason"):
        GenerationResponse(
            **_completed_response_kwargs(
                incomplete_reason=IncompleteReason.OTHER,
            ),
        )


def test_incomplete_response_rejects_refusal() -> None:
    """Refusals are only valid for completed generations."""
    with pytest.raises(ValidationError, match="refusal"):
        GenerationResponse(
            **_completed_response_kwargs(
                status=GenerationStatus.INCOMPLETE,
                output_text="",
                incomplete_reason=IncompleteReason.CONTENT_FILTER,
                refusal=ResponseRefusal(reason="policy"),
            ),
        )


def test_refusal_requires_empty_output_text() -> None:
    """When refusal is present, output_text must be empty."""
    with pytest.raises(ValidationError, match="output_text"):
        GenerationResponse(
            **_completed_response_kwargs(
                output_text="nope",
                refusal=ResponseRefusal(reason="policy"),
            ),
        )


def test_refusal_happy_path() -> None:
    """Completed refusal with empty output is valid."""
    response = GenerationResponse(
        **_completed_response_kwargs(
            output_text="",
            refusal=ResponseRefusal(reason="policy"),
        ),
    )
    assert response.refusal is not None
    assert not response.output_text


def test_incomplete_happy_path() -> None:
    """Incomplete response with reason and no refusal."""
    response = GenerationResponse(
        **_completed_response_kwargs(
            status=GenerationStatus.INCOMPLETE,
            output_text="partial",
            incomplete_reason=IncompleteReason.MAX_OUTPUT_TOKENS,
        ),
    )
    assert response.incomplete_reason is IncompleteReason.MAX_OUTPUT_TOKENS


def test_token_usage_optional_fields() -> None:
    """Optional usage breakdown fields accept non-negative integers."""
    usage = TokenUsage(
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        cached_input_tokens=2,
        reasoning_output_tokens=None,
    )
    assert usage.cached_input_tokens == 2


@pytest.mark.parametrize("module_name", sorted(p.stem for p in DOMAIN_ROOT.glob("*.py")))
def test_domain_module_does_not_import_forbidden_packages(module_name: str) -> None:
    """Domain modules must not depend on HTTP frameworks or provider SDKs."""
    path = DOMAIN_ROOT / f"{module_name}.py"
    source = path.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_DOMAIN_IMPORTS:
        assert forbidden not in source, f"{module_name}.py must not reference {forbidden}"

    spec = importlib.util.spec_from_file_location(
        f"model_gateway.domain._import_check_{module_name}",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
