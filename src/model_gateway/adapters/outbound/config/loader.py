"""Load and validate gateway settings."""

from __future__ import annotations

from model_gateway.adapters.outbound.config.settings import GatewaySettings


def load_settings(**overrides: object) -> GatewaySettings:
    """Build validated settings from the environment and optional overrides.

    Args:
        **overrides: Field overrides for tests or explicit bootstrap injection.

    Returns:
        Parsed ``GatewaySettings`` instance.
    """
    if overrides:
        return GatewaySettings.model_validate(overrides)
    return GatewaySettings()
