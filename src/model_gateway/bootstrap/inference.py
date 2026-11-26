"""Wire provider inference backends from runtime settings."""

from __future__ import annotations

from model_gateway.adapters.outbound.config import GatewaySettings
from model_gateway.adapters.outbound.openai import create_openai_backend
from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.registry import RegistryProvider


def build_inference_backend_registry(
    settings: GatewaySettings,
) -> InferenceBackendRegistry:
    """Create inference backends for providers that are configured.

    OpenAI is registered only when an API key is present. Missing credentials do
    not fail startup; generation calls fail with ``provider_not_configured`` instead.

    Args:
        settings: Gateway runtime settings.

    Returns:
        Registry of provider backends available for this process.
    """
    registry = InferenceBackendRegistry()
    if settings.openai.api_key is not None:
        registry.register(RegistryProvider.OPENAI.value, create_openai_backend(settings.openai))
    return registry
