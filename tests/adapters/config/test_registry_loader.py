"""Tests for YAML model registry loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from model_gateway.adapters.outbound.config import load_model_registry
from model_gateway.adapters.outbound.config.registry_loader import RegistryLoadError

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "models.yaml"


def test_load_default_models_yaml() -> None:
    """The checked-in registry loads and indexes OpenAI rows."""
    registry = load_model_registry(DEFAULT_REGISTRY)
    entry = registry.get("openai", "gpt-4o-mini")
    assert entry.upstream_model == "gpt-4o-mini"
    assert entry.capabilities.text_generation is True
    assert entry.limits.context_window_tokens == 128000


def test_registry_duplicate_ids_rejected(tmp_path: Path) -> None:
    """Duplicate (provider, id) pairs fail structural validation."""
    path = tmp_path / "dup.yaml"
    path.write_text(
        """
schema_version: 1
models:
  - id: same
    provider: openai
    upstream_model: gpt-4o-mini
    capabilities:
      text_generation: true
  - id: same
    provider: openai
    upstream_model: gpt-4o
    capabilities:
      text_generation: true
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_model_registry(path)


def test_unknown_provider_rejected_by_schema(tmp_path: Path) -> None:
    """Providers without a registry enum entry fail at parse time."""
    path = tmp_path / "anthropic.yaml"
    path.write_text(
        """
schema_version: 1
models:
  - id: claude
    provider: anthropic
    upstream_model: claude-3-5-sonnet
    capabilities:
      text_generation: true
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_model_registry(path)


def test_missing_registry_file() -> None:
    """Missing paths raise RegistryLoadError."""
    with pytest.raises(RegistryLoadError, match="not found"):
        load_model_registry(REPO_ROOT / "config" / "does-not-exist.yaml")
