"""Composition root: wire adapters to ports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from model_gateway.adapters.inbound.http.app import create_http_app
from model_gateway.adapters.outbound.config import GatewaySettings, load_settings

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_app(settings: GatewaySettings | None = None) -> FastAPI:
    """Create and configure the HTTP application.

    Args:
        settings: Optional pre-loaded settings; when omitted, values are read
            from the environment.

    Returns:
        Configured FastAPI application.
    """
    resolved = settings if settings is not None else load_settings()
    return create_http_app(resolved)
