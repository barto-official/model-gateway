"""Load and validate the static model registry from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from model_gateway.application.registry import (
    ModelRegistry,
    ModelRegistryDocument,
    validate_registry_policy,
)


class RegistryLoadError(Exception):
    """Raised when the registry file cannot be read or parsed."""


def load_model_registry(path: Path) -> ModelRegistry:
    """Read a registry YAML file and return an indexed :class:`ModelRegistry`.

    Schema failures surface as Pydantic ``ValidationError`` and policy failures as
    ``RegistryValidationError``; both propagate from validation unchanged.

    Args:
        path: Filesystem path to the registry document.

    Returns:
        In-memory registry ready for resolution by provider and id.

    Raises:
        RegistryLoadError: When the file is missing, unreadable, empty, or not valid YAML.
    """
    if not path.is_file():
        msg = f"registry file not found: {path}"
        raise RegistryLoadError(msg)

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"cannot read registry file: {path}"
        raise RegistryLoadError(msg) from exc

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        msg = f"invalid YAML in registry file: {path}"
        raise RegistryLoadError(msg) from exc

    if data is None:
        msg = f"registry file is empty: {path}"
        raise RegistryLoadError(msg)

    document = ModelRegistryDocument.model_validate(data)

    validate_registry_policy(document)
    return ModelRegistry(document)
