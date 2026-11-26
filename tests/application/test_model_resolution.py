"""Tests for registry model resolution and generation policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from model_gateway.adapters.outbound.config import load_model_registry
from model_gateway.application.model_resolution import (
    TextGenerationCall,
    prepare_text_generation,
)
from model_gateway.application.registry import (
    ModelCapabilities,
    ModelRegistry,
    ModelRegistryDocument,
    RegistryModelEntry,
    RegistryProvider,
)
from model_gateway.domain.errors import InvalidRequestError
from model_gateway.domain.generation import GenerationConfig, InputMessage

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "models.yaml"
HELLO = [InputMessage(role="user", content="Hi")]


def _default_registry() -> ModelRegistry:
    return load_model_registry(DEFAULT_REGISTRY)


def _single_entry_registry(entry: RegistryModelEntry) -> ModelRegistry:
    return ModelRegistry(ModelRegistryDocument(models=[entry]))


def _entry(model_id: str = "custom", **overrides: object) -> RegistryModelEntry:
    fields: dict[str, object] = {
        "id": model_id,
        "provider": RegistryProvider.OPENAI,
        "upstream_model": "gpt-4o-mini-2024-07-18",
        "capabilities": ModelCapabilities(text_generation=True),
    }
    fields.update(overrides)
    return RegistryModelEntry.model_validate(fields)


def test_request_targets_upstream_model_and_keeps_call_fields() -> None:
    """The prepared request uses upstream_model and the caller's input, instructions, config."""
    registry = _single_entry_registry(
        _entry(capabilities=ModelCapabilities(text_generation=True, system_instructions=True)),
    )
    call = TextGenerationCall(
        provider="openai",
        model_id="custom",
        input=HELLO,
        instructions="Be brief.",
        config=GenerationConfig(max_output_tokens=100),
    )

    prepared = prepare_text_generation(registry, call)

    assert prepared.entry.id == "custom"
    assert prepared.request.model == "gpt-4o-mini-2024-07-18"
    assert prepared.request.input == HELLO
    assert prepared.request.instructions == "Be brief."
    assert prepared.request.config.max_output_tokens == 100


def test_default_registry_row_prepares() -> None:
    """A row from the checked-in registry prepares without errors."""
    call = TextGenerationCall(provider="openai", model_id="gpt-4o-mini", input=HELLO)

    prepared = prepare_text_generation(_default_registry(), call)

    assert prepared.request.model == "gpt-4o-mini"


@pytest.mark.parametrize(
    ("call", "code"),
    [
        (
            TextGenerationCall(provider="anthropic", model_id="claude", input=HELLO),
            "provider_not_available",
        ),
        (
            TextGenerationCall(provider="openai", model_id="does-not-exist", input=HELLO),
            "model_not_found",
        ),
        (
            TextGenerationCall(
                provider="openai",
                model_id="gpt-4o-mini",
                input=HELLO,
                config=GenerationConfig(max_output_tokens=99_999),
            ),
            "max_output_tokens_exceeded",
        ),
    ],
)
def test_invalid_calls_against_default_registry(call: TextGenerationCall, code: str) -> None:
    """Provider, lookup, and limit failures raise InvalidRequestError with a stable code."""
    with pytest.raises(InvalidRequestError) as caught:
        prepare_text_generation(_default_registry(), call)
    assert caught.value.code == code


def test_deprecated_model_points_to_replacement() -> None:
    """Deprecated rows are rejected and name their replacement."""
    registry = _single_entry_registry(_entry("old", deprecated=True, replacement_id="new"))
    call = TextGenerationCall(provider="openai", model_id="old", input=HELLO)

    with pytest.raises(InvalidRequestError, match="'new'") as caught:
        prepare_text_generation(registry, call)
    assert caught.value.code == "model_deprecated"


@pytest.mark.parametrize(
    ("capabilities", "call_overrides", "feature"),
    [
        (ModelCapabilities(text_generation=False), {}, "text generation"),
        (
            ModelCapabilities(text_generation=True, system_instructions=False),
            {"instructions": "You are helpful."},
            "system instructions",
        ),
        (
            ModelCapabilities(text_generation=True, multi_turn_conversation=False),
            {
                "input": [
                    InputMessage(role="user", content="Hi"),
                    InputMessage(role="assistant", content="Hello"),
                    InputMessage(role="user", content="Again"),
                ],
            },
            "multi-turn conversations",
        ),
    ],
)
def test_missing_capability_rejected(
    capabilities: ModelCapabilities,
    call_overrides: dict[str, object],
    feature: str,
) -> None:
    """Calls needing a capability the model lacks are rejected before any provider call."""
    registry = _single_entry_registry(_entry(capabilities=capabilities))
    fields: dict[str, object] = {"provider": "openai", "model_id": "custom", "input": HELLO}
    fields.update(call_overrides)
    call = TextGenerationCall(**fields)  # ty: ignore[invalid-argument-type]

    with pytest.raises(InvalidRequestError, match=feature) as caught:
        prepare_text_generation(registry, call)
    assert caught.value.code == "capability_not_supported"
