"""OpenAI Responses adapter for non-streaming text generation."""

from model_gateway.adapters.outbound.openai.mapping import (
    exception_to_gateway_error,
    to_generation_response,
    to_responses_create_kwargs,
)

__all__ = [
    "exception_to_gateway_error",
    "to_generation_response",
    "to_responses_create_kwargs",
]
