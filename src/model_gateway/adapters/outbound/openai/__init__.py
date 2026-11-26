"""OpenAI Responses adapter for non-streaming text generation."""

from model_gateway.adapters.outbound.openai.adapter import (
    OpenAIInferenceBackend,
    create_openai_backend,
)
from model_gateway.adapters.outbound.openai.mapping import (
    exception_to_gateway_error,
    to_generation_response,
    to_responses_create_kwargs,
)

__all__ = [
    "OpenAIInferenceBackend",
    "create_openai_backend",
    "exception_to_gateway_error",
    "to_generation_response",
    "to_responses_create_kwargs",
]
