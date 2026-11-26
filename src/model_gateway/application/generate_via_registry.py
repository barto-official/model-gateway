"""Orchestrate catalog resolution and provider generation."""

from __future__ import annotations

from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.generate_text import GenerateTextUseCase
from model_gateway.application.model_resolution import (
    TextGenerationCall,
    prepare_text_generation,
)
from model_gateway.application.registry import ModelRegistry
from model_gateway.domain.generation import GenerationResponse


class GenerateViaRegistryUseCase:
    """Resolve a registry model, then run generation on the matching provider backend."""

    def __init__(
        self,
        registry: ModelRegistry,
        backends: InferenceBackendRegistry,
    ) -> None:
        """Initialize the use case.

        Args:
            registry: Loaded model catalog.
            backends: Provider slug to inference backend mapping.
        """
        self._registry = registry
        self._backends = backends

    async def execute(self, call: TextGenerationCall) -> GenerationResponse:
        """Prepare the call from the catalog and delegate to the provider backend.

        Args:
            call: Client call addressed by registry provider and id.

        Returns:
            The provider outcome mapped to domain response fields.
        """
        prepared = prepare_text_generation(self._registry, call)
        backend = self._backends.get(call.provider)
        use_case = GenerateTextUseCase(backend)
        return await use_case.execute(prepared.request)
