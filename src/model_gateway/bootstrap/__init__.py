"""Composition root: wire adapters to ports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from model_gateway.adapters.inbound.http.app import create_http_app
from model_gateway.adapters.outbound.config import GatewaySettings, load_settings
from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.registry import ModelRegistry
from model_gateway.application.runtime import GatewayRuntime
from model_gateway.bootstrap.inference import build_inference_backend_registry
from model_gateway.bootstrap.wiring import build_gateway_runtime

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_app(
    settings: GatewaySettings | None = None,
    *,
    runtime: GatewayRuntime | None = None,
    model_registry: ModelRegistry | None = None,
    inference_backends: InferenceBackendRegistry | None = None,
) -> FastAPI:
    """Create and configure the HTTP application.

    Args:
        settings: Optional pre-loaded settings; when omitted, values are read
            from the environment.
        runtime: Optional fully wired runtime (tests).
        model_registry: Optional catalog override when building the runtime.
        inference_backends: Optional backend override when building the runtime.

    Returns:
        Configured FastAPI application.
    """
    resolved = settings if settings is not None else load_settings()
    wired = (
        runtime
        if runtime is not None
        else build_gateway_runtime(
            resolved,
            model_registry=model_registry,
            inference_backends=inference_backends,
        )
    )
    return create_http_app(wired, environment=resolved.environment)


__all__ = [
    "build_gateway_runtime",
    "build_inference_backend_registry",
    "create_app",
]
