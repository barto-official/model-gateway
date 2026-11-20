"""Verify the hexagonal package layout is importable."""

from __future__ import annotations

import importlib

import pytest

from model_gateway.bootstrap import create_app

HEXAGONAL_PACKAGES = (
    "model_gateway",
    "model_gateway.bootstrap",
    "model_gateway.domain",
    "model_gateway.application",
    "model_gateway.adapters",
    "model_gateway.adapters.inbound",
    "model_gateway.adapters.inbound.http",
    "model_gateway.adapters.outbound",
    "model_gateway.adapters.outbound.config",
)


@pytest.mark.parametrize("package", HEXAGONAL_PACKAGES)
def test_hexagonal_package_importable(package: str) -> None:
    """Each hexagonal subpackage should import without error."""
    importlib.import_module(package)


def test_create_app_not_implemented_until_phase_0f() -> None:
    """Composition root remains a stub until Phase 0f."""
    with pytest.raises(NotImplementedError, match="Phase 0f"):
        create_app()
