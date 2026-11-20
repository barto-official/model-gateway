"""FastAPI application factory for the gateway HTTP surface."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from model_gateway.adapters.outbound.config import GatewaySettings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Attach startup state and release resources on shutdown."""
    yield


def create_http_app(settings: GatewaySettings) -> FastAPI:
    """Build the FastAPI application with health routes and lifespan hooks.

    Args:
        settings: Validated runtime settings for this process.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="Model Gateway",
        version="0.0.0",
        lifespan=_lifespan,
    )
    app.state.settings = settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe for load balancers and orchestrators.

        Returns:
            Status and configured environment name.
        """
        return {"status": "ok", "environment": settings.environment}

    return app
