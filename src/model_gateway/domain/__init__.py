"""Domain layer: canonical models, errors, and port interfaces."""

from model_gateway.domain.errors import (
    CancelledError,
    GatewayError,
    InvalidRequestError,
    TimeoutError,
    UpstreamError,
)
from model_gateway.domain.generation import (
    GenerationConfig,
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    IncompleteReason,
    InputMessage,
    ResponseRefusal,
    TokenUsage,
)
from model_gateway.domain.schema import Schema

__all__ = [
    "CancelledError",
    "GatewayError",
    "GenerationConfig",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationStatus",
    "IncompleteReason",
    "InputMessage",
    "InvalidRequestError",
    "ResponseRefusal",
    "Schema",
    "TimeoutError",
    "TokenUsage",
    "UpstreamError",
]
