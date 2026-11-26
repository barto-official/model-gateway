"""Build the process runtime from settings."""

from __future__ import annotations

from model_gateway.adapters.outbound.config import GatewaySettings, load_model_registry
from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.generate_via_registry import GenerateViaRegistryUseCase
from model_gateway.application.registry import ModelRegistry
from model_gateway.application.runtime import GatewayRuntime
from model_gateway.bootstrap.inference import build_inference_backend_registry


def build_gateway_runtime(
    settings: GatewaySettings,
    *,
    model_registry: ModelRegistry | None = None,
    inference_backends: InferenceBackendRegistry | None = None,
) -> GatewayRuntime:
    """Construct the default runtime graph for a gateway process.

    Args:
        settings: Validated gateway settings.
        model_registry: Optional catalog override (tests).
        inference_backends: Optional backend map override (tests).

    Returns:
        Wired catalog, backends, and generation use case.
    """
    catalog = (
        model_registry
        if model_registry is not None
        else load_model_registry(settings.registry.path)
    )
    backends = (
        inference_backends
        if inference_backends is not None
        else build_inference_backend_registry(settings)
    )
    use_case = GenerateViaRegistryUseCase(catalog, backends)
    return GatewayRuntime(
        model_registry=catalog,
        inference_backends=backends,
        generate_via_registry=use_case,
    )
