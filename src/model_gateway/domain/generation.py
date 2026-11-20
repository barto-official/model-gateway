"""Canonical text-generation request and response models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from model_gateway.domain.schema import Schema


class InputMessage(Schema):
    """A single conversational turn in a generation request."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class GenerationConfig(Schema):
    """Provider-agnostic generation parameters for v0.1."""

    max_output_tokens: int | None = Field(default=None, gt=0, strict=True)


class GenerationRequest(Schema):
    """Text generation request for a configured provider model."""

    model: str = Field(min_length=1)
    input: list[InputMessage] = Field(min_length=1)
    instructions: str | None = None
    config: GenerationConfig = Field(default_factory=GenerationConfig)


class GenerationStatus(StrEnum):
    """Overall outcome of a generation call."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


class IncompleteReason(StrEnum):
    """Why a generation ended before a normal completion."""

    MAX_OUTPUT_TOKENS = "max_output_tokens"
    CONTENT_FILTER = "content_filter"
    OTHER = "other"


class ResponseRefusal(Schema):
    """Structured indication that the model refused to produce output."""

    reason: str


class TokenUsage(Schema):
    """Token accounting for a generation response."""

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_output_tokens: int | None = Field(default=None, ge=0)


class GenerationResponse(Schema):
    """Text generation response returned by the gateway domain layer.

    Cross-field rules:

    * ``status`` ``INCOMPLETE`` requires ``incomplete_reason``; ``COMPLETED`` forbids it.
    * When ``refusal`` is set, ``output_text`` must be empty (the model declined instead of
      answering).
    * ``refusal`` is only allowed when ``status`` is ``COMPLETED``.
    """

    id: str
    model: str
    status: GenerationStatus
    output_text: str
    refusal: ResponseRefusal | None = None
    incomplete_reason: IncompleteReason | None = None
    usage: TokenUsage | None = None
    created_at: datetime

    @model_validator(mode="after")
    def validate_status_fields(self) -> Self:
        """Enforce consistency between status, incomplete_reason, refusal, and output.

        Returns:
            The validated model instance.

        Raises:
            ValueError: When status, incomplete_reason, refusal, and output disagree.
        """
        if self.status is GenerationStatus.INCOMPLETE:
            if self.incomplete_reason is None:
                msg = "incomplete_reason is required when status is incomplete"
                raise ValueError(msg)
            if self.refusal is not None:
                msg = "refusal must be absent when status is incomplete"
                raise ValueError(msg)
        elif self.incomplete_reason is not None:
            msg = "incomplete_reason must be absent when status is completed"
            raise ValueError(msg)

        if self.refusal is not None:
            if self.status is not GenerationStatus.COMPLETED:
                msg = "refusal is only allowed when status is completed"
                raise ValueError(msg)
            if self.output_text:
                msg = "output_text must be empty when refusal is set"
                raise ValueError(msg)

        return self
