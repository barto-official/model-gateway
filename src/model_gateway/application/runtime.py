"""Process-wide application objects shared by entrypoints."""

from __future__ import annotations

from dataclasses import dataclass

from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.generate_via_registry import GenerateViaRegistryUseCase
from model_gateway.application.registry import ModelRegistry


@dataclass(frozen=True, slots=True)
class GatewayRuntime:
    """Catalog, provider backends, and the generation use case for one process."""

    model_registry: ModelRegistry
    inference_backends: InferenceBackendRegistry
    generate_via_registry: GenerateViaRegistryUseCase
