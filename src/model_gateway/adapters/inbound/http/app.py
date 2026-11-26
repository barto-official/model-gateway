"""FastAPI application factory for the gateway HTTP surface."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from model_gateway.adapters.inbound.http.problems import (
    gateway_error_handler,
    pydantic_validation_error_handler,
    request_validation_error_handler,
)
from model_gateway.adapters.inbound.http.routes import generations
from model_gateway.application.runtime import GatewayRuntime
from model_gateway.domain.errors import GatewayError


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Attach startup state and release provider clients on shutdown."""
    yield
    runtime: GatewayRuntime = app.state.runtime
    await runtime.inference_backends.aclose_all()


def create_http_app(runtime: GatewayRuntime, *, environment: str) -> FastAPI:
    """Build the FastAPI application with routes and error handlers.

    Args:
        runtime: Catalog, backends, and generation use case for this process.
        environment: Configured environment name reported by the health route.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title="Model Gateway",
        version="0.0.0",
        lifespan=_lifespan,
    )
    app.state.runtime = runtime

    app.add_exception_handler(GatewayError, gateway_error_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)

    app.include_router(generations.router)

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint for the gateway.

        Returns:
            Ok status.
        """
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe for load balancers and orchestrators.

        Returns:
            Ok status and configured environment name.
        """
        return {"status": "ok", "environment": environment}

    return app
