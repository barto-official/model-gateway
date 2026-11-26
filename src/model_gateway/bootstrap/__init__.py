"""Composition root: wire adapters to ports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from model_gateway.adapters.inbound.http.app import create_http_app
from model_gateway.adapters.outbound.config import GatewaySettings, load_settings
from model_gateway.adapters.outbound.openai import create_openai_backend
from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.registry import RegistryProvider

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    """Create and configure the HTTP application.

    Args:
        settings: Optional pre-loaded settings; when omitted, values are read
            from the environment.

    Returns:
        Configured FastAPI application.
    """
    resolved = settings if settings is not None else load_settings()
    return create_http_app(resolved)


def build_inference_backend_registry(
    settings: GatewaySettings,
) -> InferenceBackendRegistry:
    """Create inference backends for providers that are configured.

    Args:
        settings: Gateway runtime settings.

    Returns:
        Registry of provider backends available for this process.
    """
    registry = InferenceBackendRegistry()
    if settings.openai.api_key is not None:
        registry.register(RegistryProvider.OPENAI.value, create_openai_backend(settings.openai))
    return registry


__all__ = [
    "build_inference_backend_registry",
    "create_app",
]
