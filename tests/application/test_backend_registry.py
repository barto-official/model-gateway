"""Tests for :class:`~model_gateway.application.backend_registry.InferenceBackendRegistry`."""

from __future__ import annotations

import pytest
from tests.doubles.fake_inference_backend import FakeInferenceBackend

from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.domain.errors import InvalidRequestError


def test_get_returns_registered_backend() -> None:
    """Registered providers resolve to their backend."""
    backend = FakeInferenceBackend(name="openai")
    registry = InferenceBackendRegistry({"openai": backend})

    assert registry.get("openai") is backend
    assert registry.configured_providers() == frozenset({"openai"})


def test_get_missing_provider_raises() -> None:
    """Unconfigured providers fail with provider_not_configured."""
    registry = InferenceBackendRegistry()

    with pytest.raises(InvalidRequestError, match="not configured") as caught:
        registry.get("openai")

    assert caught.value.code == "provider_not_configured"
