"""Test double implementing :class:`~model_gateway.domain.ports.InferenceBackend`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum, auto
from uuid import uuid4

from model_gateway.domain.errors import UpstreamError
from model_gateway.domain.generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationStatus,
    IncompleteReason,
    InputMessage,
    ResponseRefusal,
    TokenUsage,
)


class FakeOutcome(StrEnum):
    """Selectable behaviors for contract and application tests."""

    COMPLETED = auto()
    INCOMPLETE = auto()
    REFUSAL = auto()
    UPSTREAM_ERROR = auto()


@dataclass
class FakeInferenceBackend:
    """Structural implementation of :class:`~model_gateway.domain.ports.InferenceBackend`.

    By default, echoes the last user message with a suffix and returns synthetic metadata.

    Attributes:
        name: Stable backend identifier surfaced via the port ``name`` property.
        response_suffix: Appended to the last user message for completed responses.
        outcome: Controls success shape or simulated upstream failure.
        refusal_reason: Used when ``outcome`` is ``REFUSAL``.
        incomplete_reason: Used when ``outcome`` is ``INCOMPLETE``.
    """

    name: str = "fake"
    response_suffix: str = " [fake]"
    outcome: FakeOutcome = FakeOutcome.COMPLETED
    refusal_reason: str = "policy"
    incomplete_reason: IncompleteReason = IncompleteReason.MAX_OUTPUT_TOKENS
    _generation_count: int = field(default=0, init=False, repr=False)

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return a configurable domain response or raise per ``outcome``.

        Raises:
            UpstreamError: When ``outcome`` is ``UPSTREAM_ERROR``.
        """
        self._generation_count += 1

        if self.outcome is FakeOutcome.UPSTREAM_ERROR:
            raise UpstreamError("simulated upstream failure")

        created_at = datetime.now(tz=UTC)
        response_id = f"fake-{uuid4()}"
        usage = TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15)

        last_user = _last_user_content(request.input)

        if self.outcome is FakeOutcome.INCOMPLETE:
            return GenerationResponse(
                id=response_id,
                model=request.model,
                status=GenerationStatus.INCOMPLETE,
                output_text=last_user + self.response_suffix,
                incomplete_reason=self.incomplete_reason,
                usage=usage,
                created_at=created_at,
            )

        if self.outcome is FakeOutcome.REFUSAL:
            return GenerationResponse(
                id=response_id,
                model=request.model,
                status=GenerationStatus.COMPLETED,
                output_text="",
                refusal=ResponseRefusal(reason=self.refusal_reason),
                usage=usage,
                created_at=created_at,
            )

        return GenerationResponse(
            id=response_id,
            model=request.model,
            status=GenerationStatus.COMPLETED,
            output_text=last_user + self.response_suffix,
            usage=usage,
            created_at=created_at,
        )


def _last_user_content(messages: list[InputMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""
