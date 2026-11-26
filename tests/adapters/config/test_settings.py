"""Tests for environment-backed gateway settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from model_gateway.adapters.outbound.config import (
    GatewaySettings,
    LogLevel,
    load_settings,
)


def test_load_settings_defaults_without_env() -> None:
    """Settings load with defaults when no overrides are set."""
    settings = load_settings()
    assert settings.environment == "development"
    assert settings.log_level == LogLevel.INFO
    assert settings.http.port == 8000
    assert settings.openai.api_key is None


def test_load_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nested environment variables map into typed settings."""
    monkeypatch.setenv("MODEL_GATEWAY_ENVIRONMENT", "staging")
    monkeypatch.setenv("MODEL_GATEWAY_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MODEL_GATEWAY_HTTP__HOST", "127.0.0.1")
    monkeypatch.setenv("MODEL_GATEWAY_HTTP__PORT", "9001")
    monkeypatch.setenv("MODEL_GATEWAY_OPENAI__API_KEY", "sk-test-key")
    settings = load_settings()
    assert settings.environment == "staging"
    assert settings.log_level == LogLevel.DEBUG
    assert settings.http.host == "127.0.0.1"
    assert settings.http.port == 9001
    assert settings.openai.api_key is not None
    assert settings.openai.api_key.get_secret_value() == "sk-test-key"


def test_openai_api_key_not_leaked_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secret values must not appear in model repr."""
    monkeypatch.setenv("MODEL_GATEWAY_OPENAI__API_KEY", "sk-top-secret")
    settings = load_settings()
    rendered = repr(settings)
    assert "sk-top-secret" not in rendered


def test_invalid_http_port_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Out-of-range ports fail validation at load time."""
    monkeypatch.setenv("MODEL_GATEWAY_HTTP__PORT", "0")
    with pytest.raises(ValidationError):
        load_settings()


def test_load_settings_accepts_overrides() -> None:
    """Explicit overrides support tests without mutating the environment."""
    settings = load_settings(
        environment="test",
        http={"host": "127.0.0.1", "port": 8765},
    )
    assert isinstance(settings, GatewaySettings)
    assert settings.environment == "test"
    assert settings.http.port == 8765
