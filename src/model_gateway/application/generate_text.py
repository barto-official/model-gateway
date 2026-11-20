"""Application use case for non-streaming text generation."""

from __future__ import annotations

from model_gateway.domain.generation import GenerationRequest, GenerationResponse
from model_gateway.domain.ports import InferenceBackend


class GenerateTextUseCase:
    """Delegates generation to an :class:`~model_gateway.domain.ports.InferenceBackend`."""

    def __init__(self, backend: InferenceBackend) -> None:
        """Initialize the use case with a generation backend.

        Args:
            backend: Port implementation that performs the actual generation.
        """
        self._backend = backend

    async def execute(self, request: GenerationRequest) -> GenerationResponse:
        """Run text generation for the given request.

        Args:
            request: Canonical generation request.

        Returns:
            The backend response on success.
        """
        return await self._backend.generate(request)
