"""HTTP adapter tests for health endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from model_gateway.adapters.outbound.config import load_settings
from model_gateway.bootstrap import create_app


def test_health_returns_ok() -> None:
    """GET /health returns ok and echoes the configured environment."""
    settings = load_settings(environment="test")
    client = TestClient(create_app(settings))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}


def test_create_app_loads_from_environment_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create_app() reads the environment when settings are omitted."""
    monkeypatch.setenv("MODEL_GATEWAY_ENVIRONMENT", "ci")
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.json()["environment"] == "ci"
