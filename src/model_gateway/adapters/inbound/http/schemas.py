"""HTTP request and response bodies for text generation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from model_gateway.application.model_resolution import TextGenerationCall
from model_gateway.domain.generation import (
    GenerationConfig,
    GenerationResponse,
    GenerationStatus,
    IncompleteReason,
    InputMessage,
)


class GenerationConfigBody(BaseModel):
    """Generation parameters on the public API."""

    model_config = ConfigDict(extra="forbid")

    max_output_tokens: int | None = Field(default=None, gt=0)


class TextGenerationRequestBody(BaseModel):
    """POST /v1/generations request body."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1, description="Gateway registry model id.")
    input: list[InputMessage] = Field(min_length=1)
    instructions: str | None = None
    config: GenerationConfigBody = Field(default_factory=GenerationConfigBody)
    stream: bool = False

    @field_validator("stream")
    @classmethod
    def reject_streaming(cls, value: bool) -> bool:
        """Streaming is not supported until a later API version.

        Returns:
            The unchanged ``stream`` flag when streaming is not requested.

        Raises:
            ValueError: When ``stream`` is true.
        """
        if value:
            msg = "Streaming is not supported on this API version."
            raise ValueError(msg)
        return value

    def to_call(self) -> TextGenerationCall:
        """Map the HTTP body to an application :class:`TextGenerationCall`.

        Returns:
            Call parameters for the registry-backed use case.
        """
        return TextGenerationCall(
            provider=self.provider,
            model_id=self.model,
            input=self.input,
            instructions=self.instructions,
            config=GenerationConfig(max_output_tokens=self.config.max_output_tokens),
        )


class ResponseRefusalBody(BaseModel):
    """Refusal fragment in a generation response."""

    model_config = ConfigDict(extra="forbid")

    reason: str


class TokenUsageBody(BaseModel):
    """Usage fragment in a generation response."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int | None = None
    reasoning_output_tokens: int | None = None


class TextGenerationResponseBody(BaseModel):
    """POST /v1/generations success response."""

    model_config = ConfigDict(extra="forbid")

    id: str
    model: str
    status: GenerationStatus
    output_text: str
    refusal: ResponseRefusalBody | None = None
    incomplete_reason: IncompleteReason | None = None
    usage: TokenUsageBody | None = None
    created_at: datetime

    @classmethod
    def from_domain(cls, response: GenerationResponse) -> TextGenerationResponseBody:
        """Build the HTTP response from a domain :class:`GenerationResponse`.

        Returns:
            JSON-serializable response body.
        """
        usage = response.usage
        usage_body = None
        if usage is not None:
            usage_body = TokenUsageBody(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                cached_input_tokens=usage.cached_input_tokens,
                reasoning_output_tokens=usage.reasoning_output_tokens,
            )
        refusal = response.refusal
        refusal_body = ResponseRefusalBody(reason=refusal.reason) if refusal is not None else None
        return cls(
            id=response.id,
            model=response.model,
            status=response.status,
            output_text=response.output_text,
            refusal=refusal_body,
            incomplete_reason=response.incomplete_reason,
            usage=usage_body,
            created_at=response.created_at,
        )
