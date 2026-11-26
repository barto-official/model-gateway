"""Verify the hexagonal package layout is importable."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest
from fastapi import FastAPI

from model_gateway.adapters.outbound.config import load_settings
from model_gateway.bootstrap import create_app

HTTP_ADAPTER = (
    Path(__file__).resolve().parents[1] / "src" / "model_gateway" / "adapters" / "inbound" / "http"
)

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


def test_http_adapter_does_not_import_bootstrap() -> None:
    """Inbound HTTP depends on application types, not the composition root."""
    offenders: list[str] = []
    for path in HTTP_ADAPTER.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str | None] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module)
            for module in modules:
                if module is not None and (
                    module == "model_gateway.bootstrap"
                    or module.startswith("model_gateway.bootstrap.")
                ):
                    offenders.append(f"{path.name}: {module}")
    assert offenders == []


def test_create_app_returns_fastapi_application() -> None:
    """create_app() returns a configured FastAPI instance."""
    app = create_app(settings=load_settings(environment="layout-test"))
    assert isinstance(app, FastAPI)
