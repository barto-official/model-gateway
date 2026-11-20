"""Outbound port interfaces for provider integrations."""

from __future__ import annotations

from typing import Protocol

from model_gateway.domain.generation import GenerationRequest, GenerationResponse


class InferenceBackend(Protocol):
    """Executes text generation against a configured provider or test double.

    Implementations perform the network or SDK work required to satisfy a
    :class:`~model_gateway.domain.generation.GenerationRequest`.

    On success, ``generate`` returns a :class:`~model_gateway.domain.generation.GenerationResponse`.
    On failure, implementations raise a :class:`~model_gateway.domain.errors.GatewayError`
    subclass (for example :class:`~model_gateway.domain.errors.InvalidRequestError`,
    :class:`~model_gateway.domain.errors.UpstreamError`,
    :class:`~model_gateway.domain.errors.TimeoutError`, or
    :class:`~model_gateway.domain.errors.CancelledError`). Streaming is not part of this
    contract.
    """

    @property
    def name(self) -> str:
        """Stable identifier for logging and diagnostics."""
        ...

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Run a single non-streaming generation for the given request.

        Args:
            request: Canonical gateway generation payload.

        Returns:
            The provider outcome mapped to domain response fields.

        Raises:
            InvalidRequestError: When the request cannot be sent as given.
            UpstreamError: When the provider fails or returns an unusable response.
            TimeoutError: When the call exceeds its deadline.
            CancelledError: When the call is cancelled before completion.
        """
        ...
