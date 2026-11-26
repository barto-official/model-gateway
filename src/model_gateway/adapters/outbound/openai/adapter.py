"""OpenAI Responses inference backend for :class:`~model_gateway.domain.ports.InferenceBackend`."""

from __future__ import annotations

import httpx2
from openai import APIError, AsyncOpenAI

from model_gateway.adapters.outbound.config.settings import OpenAISettings
from model_gateway.adapters.outbound.openai.mapping import (
    exception_to_gateway_error,
    to_generation_response,
    to_responses_create_kwargs,
)
from model_gateway.domain.errors import InvalidRequestError
from model_gateway.domain.generation import GenerationRequest, GenerationResponse


class OpenAIInferenceBackend:
    """Non-streaming text generation via the OpenAI Responses API.

    Args:
        client: Configured async OpenAI client used for upstream calls.
        owns_client: When true, :meth:`aclose` closes the client.
    """

    def __init__(self, client: AsyncOpenAI, *, owns_client: bool = True) -> None:
        self._client = client
        self._owns_client = owns_client

    @property
    def name(self) -> str:
        """Stable backend identifier for logging and diagnostics."""
        return "openai"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Run a single non-streaming generation for the given request.

        Args:
            request: Canonical generation request.

        Returns:
            The provider outcome mapped to domain response fields.
        """
        try:
            response = await self._client.responses.create(**to_responses_create_kwargs(request))
        except APIError as exc:
            gateway_error = exception_to_gateway_error(exc)
            raise gateway_error from exc
        return to_generation_response(response)

    async def aclose(self) -> None:
        """Close the underlying HTTP client when this backend owns it."""
        if self._owns_client:
            await self._client.close()


def create_openai_backend(
    settings: OpenAISettings,
    *,
    http_client: httpx2.AsyncClient | None = None,
) -> OpenAIInferenceBackend:
    """Build an OpenAI inference backend from provider settings.

    Args:
        settings: OpenAI connection and credential settings.
        http_client: Optional HTTP client for tests or custom transports.

    Returns:
        A backend ready to satisfy :class:`~model_gateway.domain.ports.InferenceBackend`.

    Raises:
        InvalidRequestError: When no API key is configured.
    """
    if settings.api_key is None:
        msg = "OpenAI API key is not configured."
        raise InvalidRequestError(msg, code="provider_not_configured")

    client = AsyncOpenAI(
        api_key=settings.api_key.get_secret_value(),
        timeout=settings.timeout_seconds,
        max_retries=0,
        base_url=settings.base_url,
        organization=settings.organization,
        project=settings.project,
        http_client=http_client,
    )
    owns_client = http_client is None
    return OpenAIInferenceBackend(client, owns_client=owns_client)
