"""Contract tests for :class:`~model_gateway.domain.ports.InferenceBackend`."""

from __future__ import annotations

import asyncio

import pytest
from tests.doubles.fake_inference_backend import FakeInferenceBackend, FakeOutcome

from model_gateway.application.generate_text import GenerateTextUseCase
from model_gateway.domain import GenerationRequest, GenerationStatus, InputMessage
from model_gateway.domain.errors import UpstreamError


def _sample_request() -> GenerationRequest:
    return GenerationRequest(
        model="gpt-4o-mini",
        input=[InputMessage(role="user", content="Hello")],
    )


def test_inference_backend_happy_path_through_use_case() -> None:
    """Completed generation echoes the last user turn with the fake suffix."""
    backend = FakeInferenceBackend()
    use_case = GenerateTextUseCase(backend)

    response = asyncio.run(use_case.execute(_sample_request()))

    assert response.status is GenerationStatus.COMPLETED
    assert response.output_text == "Hello [fake]"
    assert response.model == "gpt-4o-mini"
    assert response.usage is not None
    assert response.created_at.tzinfo is not None


def test_inference_backend_incomplete_through_use_case() -> None:
    """Incomplete outcomes include a domain incomplete reason."""
    backend = FakeInferenceBackend(outcome=FakeOutcome.INCOMPLETE)
    use_case = GenerateTextUseCase(backend)

    response = asyncio.run(use_case.execute(_sample_request()))

    assert response.status is GenerationStatus.INCOMPLETE
    assert response.incomplete_reason is not None
    assert response.refusal is None


def test_inference_backend_refusal_through_use_case() -> None:
    """Refusal responses keep output empty and attach structured refusal."""
    backend = FakeInferenceBackend(outcome=FakeOutcome.REFUSAL, refusal_reason="safety")
    use_case = GenerateTextUseCase(backend)

    response = asyncio.run(use_case.execute(_sample_request()))

    assert response.status is GenerationStatus.COMPLETED
    assert not response.output_text
    assert response.refusal is not None
    assert response.refusal.reason == "safety"


def test_inference_backend_upstream_error_propagates() -> None:
    """Upstream failures from the backend reach callers without translation."""
    backend = FakeInferenceBackend(outcome=FakeOutcome.UPSTREAM_ERROR)
    use_case = GenerateTextUseCase(backend)

    with pytest.raises(UpstreamError, match="simulated upstream failure"):
        asyncio.run(use_case.execute(_sample_request()))
