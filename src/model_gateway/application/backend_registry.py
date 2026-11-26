"""Lookup table mapping provider slugs to inference backends."""

from __future__ import annotations

from model_gateway.domain.errors import InvalidRequestError
from model_gateway.domain.ports import InferenceBackend


class InferenceBackendRegistry:
    """Provider slug to :class:`~model_gateway.domain.ports.InferenceBackend` lookup."""

    def __init__(self, backends: dict[str, InferenceBackend] | None = None) -> None:
        """Initialize the registry.

        Args:
            backends: Provider slug to backend mapping; defaults to empty.
        """
        self._backends = dict(backends or ())

    def register(self, provider: str, backend: InferenceBackend) -> None:
        """Register or replace the backend for a provider slug."""
        self._backends[provider] = backend

    def get(self, provider: str) -> InferenceBackend:
        """Return the backend for ``provider``.

        Args:
            provider: Provider slug (for example ``openai``).

        Returns:
            The configured backend.

        Raises:
            InvalidRequestError: When no backend is configured for the provider.
        """
        try:
            return self._backends[provider]
        except KeyError:
            msg = f"Inference backend for provider {provider!r} is not configured."
            raise InvalidRequestError(msg, code="provider_not_configured") from None

    def configured_providers(self) -> frozenset[str]:
        """Return provider slugs that currently have a backend."""
        return frozenset(self._backends)
