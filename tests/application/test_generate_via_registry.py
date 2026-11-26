"""Tests for registry-backed text generation use case."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from tests.doubles.fake_inference_backend import FakeInferenceBackend

from model_gateway.adapters.outbound.config import load_model_registry, load_settings
from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.generate_via_registry import GenerateViaRegistryUseCase
from model_gateway.application.model_resolution import TextGenerationCall
from model_gateway.application.registry import (
    ModelCapabilities,
    ModelRegistry,
    ModelRegistryDocument,
    RegistryModelEntry,
    RegistryProvider,
)
from model_gateway.bootstrap import build_inference_backend_registry
from model_gateway.domain.errors import InvalidRequestError
from model_gateway.domain.generation import InputMessage

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "models.yaml"
HELLO = [InputMessage(role="user", content="Hi")]


def _use_case_with_fake(
    *,
    catalog: ModelRegistry | None = None,
) -> tuple[GenerateViaRegistryUseCase, FakeInferenceBackend]:
    catalog = catalog if catalog is not None else load_model_registry(DEFAULT_REGISTRY)
    fake = FakeInferenceBackend(name="openai")
    backends = InferenceBackendRegistry({RegistryProvider.OPENAI.value: fake})
    return GenerateViaRegistryUseCase(catalog, backends), fake


def test_execute_uses_upstream_model_from_catalog() -> None:
    """Changing the registry model id changes the upstream model on the backend request."""
    document = ModelRegistryDocument(
        schema_version=1,
        models=[
            RegistryModelEntry(
                id="small",
                provider=RegistryProvider.OPENAI,
                upstream_model="gpt-4o-mini",
                capabilities=ModelCapabilities(text_generation=True),
            ),
            RegistryModelEntry(
                id="large",
                provider=RegistryProvider.OPENAI,
                upstream_model="gpt-4o",
                capabilities=ModelCapabilities(text_generation=True),
            ),
        ],
    )
    use_case, fake = _use_case_with_fake(catalog=ModelRegistry(document))

    response = asyncio.run(
        use_case.execute(TextGenerationCall(provider="openai", model_id="small", input=HELLO))
    )
    assert response.model == "gpt-4o-mini"

    response = asyncio.run(
        use_case.execute(TextGenerationCall(provider="openai", model_id="large", input=HELLO))
    )
    assert response.model == "gpt-4o"


def test_execute_with_checked_in_registry() -> None:
    """The default YAML catalog runs end-to-end with a fake backend."""
    use_case, _fake = _use_case_with_fake()
    call = TextGenerationCall(provider="openai", model_id="gpt-4o-mini", input=HELLO)

    response = asyncio.run(use_case.execute(call))

    assert response.output_text == "Hi [fake]"


def test_unknown_model_not_invoked() -> None:
    """Resolution failures stop before the backend is called."""
    use_case, _fake = _use_case_with_fake()

    with pytest.raises(InvalidRequestError, match="No model registered") as caught:
        asyncio.run(
            use_case.execute(
                TextGenerationCall(provider="openai", model_id="missing", input=HELLO),
            ),
        )
    assert caught.value.code == "model_not_found"


def test_missing_backend_configuration() -> None:
    """Calls fail when the provider has no wired backend."""
    catalog = load_model_registry(DEFAULT_REGISTRY)
    use_case = GenerateViaRegistryUseCase(catalog, InferenceBackendRegistry())

    call = TextGenerationCall(provider="openai", model_id="gpt-4o-mini", input=HELLO)
    with pytest.raises(InvalidRequestError, match="not configured") as caught:
        asyncio.run(use_case.execute(call))
    assert caught.value.code == "provider_not_configured"


def test_build_inference_registry_without_openai_key() -> None:
    """Startup does not require an OpenAI key; the backend map stays empty."""
    settings = load_settings(openai={"api_key": None})

    registry = build_inference_backend_registry(settings)

    assert registry.configured_providers() == frozenset()
