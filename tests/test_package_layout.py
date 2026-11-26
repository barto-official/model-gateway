"""Verify the hexagonal package layout is importable."""

from __future__ import annotations

import importlib

import pytest
from fastapi import FastAPI

from model_gateway.adapters.outbound.config import load_settings
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
    "model_gateway.adapters.outbound.openai",
)


@pytest.mark.parametrize("package", HEXAGONAL_PACKAGES)
def test_hexagonal_package_importable(package: str) -> None:
    """Each hexagonal subpackage should import without error."""
    importlib.import_module(package)


def test_create_app_returns_fastapi_application() -> None:
    """create_app() returns a configured FastAPI instance."""
    app = create_app(settings=load_settings(environment="layout-test"))
    assert isinstance(app, FastAPI)
