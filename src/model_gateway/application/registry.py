"""Model registry types and in-memory index (application-owned model identity)."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from model_gateway.domain.schema import Schema


class RegistryProvider(StrEnum):
    """Providers allowed in the static registry file for the current release."""

    OPENAI = "openai"


ALLOWED_REGISTRY_PROVIDERS: frozenset[str] = frozenset(p.value for p in RegistryProvider)


class ModelCapabilities(Schema):
    """Capability flags for a single registry entry (aligned with gateway roadmap domains)."""

    text_generation: bool = False
    multi_turn_conversation: bool = False
    system_instructions: bool = False
    streaming: bool = False
    tool_calling: bool = False
    structured_json_output: bool = False
    vision: bool = False
    extended_reasoning: bool = False
    audio_input: bool = False
    audio_output: bool = False
    embeddings: bool = False
    batch_inference: bool = False
    realtime: bool = False


class ModelLimits(Schema):
    """Known upstream limits for validation and future parameter translation."""

    context_window_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)


class RegistryModelEntry(Schema):
    """One deployable model row in the static registry."""

    id: str = Field(min_length=1, description="Gateway registry identifier.")
    provider: RegistryProvider
    upstream_model: str = Field(
        min_length=1,
        description="Provider-native model id passed to the SDK.",
    )
    display_name: str | None = None
    description: str | None = None
    capabilities: ModelCapabilities
    limits: ModelLimits = Field(default_factory=ModelLimits)
    tags: list[str] = Field(default_factory=list)
    deprecated: bool = False
    replacement_id: str | None = Field(
        default=None,
        min_length=1,
        description="Suggested registry id when this entry is deprecated.",
    )


class ModelRegistryDocument(Schema):
    """Validated contents of a registry YAML file."""

    schema_version: int = Field(default=1, ge=1)
    models: list[RegistryModelEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_provider_and_id(self) -> Self:
        """Ensure (provider, id) pairs are unique within the file.

        Returns:
            The validated document.

        Raises:
            ValueError: When two rows share the same provider and id.
        """
        seen: set[tuple[str, str]] = set()
        for entry in self.models:
            key = (entry.provider.value, entry.id)
            if key in seen:
                msg = f"duplicate registry entry for provider={entry.provider!s} id={entry.id!r}"
                raise ValueError(msg)
            seen.add(key)
        return self


class ModelRegistry:
    """Lookup index built from a validated registry document."""

    def __init__(self, document: ModelRegistryDocument) -> None:
        """Build an index keyed by (provider, id).

        Args:
            document: Validated registry file contents.
        """
        self._document = document
        self._by_key: dict[tuple[str, str], RegistryModelEntry] = {
            (entry.provider.value, entry.id): entry for entry in document.models
        }

    @property
    def schema_version(self) -> int:
        """Registry file schema version."""
        return self._document.schema_version

    def entries(self) -> tuple[RegistryModelEntry, ...]:
        """Return all registry rows in file order."""
        return tuple(self._document.models)

    def get(self, provider: str, model_id: str) -> RegistryModelEntry:
        """Resolve a registry row by provider and gateway id.

        Args:
            provider: Provider slug (for example ``openai``).
            model_id: Gateway registry id from the catalog.

        Returns:
            The matching registry entry.

        Raises:
            KeyError: When no row exists for the pair.
        """
        key = (provider, model_id)
        try:
            return self._by_key[key]
        except KeyError:
            msg = f"no registry model for provider={provider!r} id={model_id!r}"
            raise KeyError(msg) from None

    def contains(self, provider: str, model_id: str) -> bool:
        """Return whether a registry row exists for the pair."""
        return (provider, model_id) in self._by_key


class RegistryValidationError(ValueError):
    """Raised when registry file contents fail gateway policy checks."""


def validate_registry_policy(document: ModelRegistryDocument) -> None:
    """Apply gateway policy on top of structural validation.

    Args:
        document: Parsed registry document.

    Raises:
        RegistryValidationError: When a provider is not yet supported by an adapter.
    """
    for entry in document.models:
        if entry.provider.value not in ALLOWED_REGISTRY_PROVIDERS:
            msg = (
                f"provider {entry.provider.value!r} is not enabled; "
                f"allowed: {sorted(ALLOWED_REGISTRY_PROVIDERS)!r}"
            )
            raise RegistryValidationError(msg)
