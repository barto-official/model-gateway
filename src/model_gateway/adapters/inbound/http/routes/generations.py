"""Text generation HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from model_gateway.adapters.inbound.http.schemas import (
    TextGenerationRequestBody,
    TextGenerationResponseBody,
)
from model_gateway.application.runtime import GatewayRuntime

router = APIRouter(tags=["generations"])


@router.post("/v1/generations", response_model=TextGenerationResponseBody)
async def create_generation(
    body: TextGenerationRequestBody,
    request: Request,
) -> TextGenerationResponseBody:
    """Run a non-streaming text generation for a registry model.

    Returns:
        Completed or incomplete generation payload from the provider.
    """
    runtime: GatewayRuntime = request.app.state.runtime
    response = await runtime.generate_via_registry.execute(body.to_call())
    return TextGenerationResponseBody.from_domain(response)
