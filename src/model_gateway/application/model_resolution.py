"""Resolve a registry model and prepare a validated text-generation request."""

from __future__ import annotations

from dataclasses import dataclass, field

from model_gateway.application.registry import (
    ALLOWED_REGISTRY_PROVIDERS,
    ModelRegistry,
    RegistryModelEntry,
)
from model_gateway.domain.errors import InvalidRequestError
from model_gateway.domain.generation import (
    GenerationConfig,
    GenerationRequest,
    InputMessage,
)


@dataclass(frozen=True, slots=True)
class TextGenerationCall:
    """A client's text-generation call, addressed by registry ``(provider, model_id)``.

    Attributes:
        provider: Provider slug (for example ``openai``).
        model_id: Gateway registry id.
        input: Conversational turns.
        instructions: Optional system-style instructions.
        config: Generation parameters.
    """

    provider: str
    model_id: str
    input: list[InputMessage]
    instructions: str | None = None
    config: GenerationConfig = field(default_factory=GenerationConfig)


@dataclass(frozen=True, slots=True)
class PreparedGeneration:
    """A validated call ready for an inference backend.

    Attributes:
        entry: Registry row the call resolved to.
        request: Domain request addressed to the entry's upstream model.
    """

    entry: RegistryModelEntry
    request: GenerationRequest


def prepare_text_generation(
    registry: ModelRegistry,
    call: TextGenerationCall,
) -> PreparedGeneration:
    """Resolve the call's registry model, check it can serve the call, and build the request.

    Args:
        registry: Loaded model catalog.
        call: Client call addressed by registry provider and id.

    Returns:
        The resolved registry entry and a request using its ``upstream_model``.

    Raises:
        InvalidRequestError: When the provider is not enabled, the model is unknown or
            deprecated, the model lacks a required capability, or ``max_output_tokens``
            exceeds the model limit.
    """
    if call.provider not in ALLOWED_REGISTRY_PROVIDERS:
        msg = (
            f"Provider {call.provider!r} is not enabled on this gateway "
            f"(allowed: {sorted(ALLOWED_REGISTRY_PROVIDERS)!r})."
        )
        raise InvalidRequestError(msg, code="provider_not_available")

    try:
        entry = registry.get(call.provider, call.model_id)
    except KeyError:
        msg = f"No model registered for provider {call.provider!r} and id {call.model_id!r}."
        raise InvalidRequestError(msg, code="model_not_found") from None

    if entry.deprecated:
        msg = f"Model {entry.id!r} is deprecated."
        if entry.replacement_id:
            msg = f"Model {entry.id!r} is deprecated; use id {entry.replacement_id!r} instead."
        raise InvalidRequestError(msg, code="model_deprecated")

    missing = _missing_capability(entry, call)
    if missing is not None:
        msg = f"Model {entry.id!r} does not support {missing}."
        raise InvalidRequestError(msg, code="capability_not_supported")

    limit = entry.limits.max_output_tokens
    requested = call.config.max_output_tokens
    if limit is not None and requested is not None and requested > limit:
        msg = f"max_output_tokens {requested} exceeds the model limit of {limit}."
        raise InvalidRequestError(msg, code="max_output_tokens_exceeded")

    request = GenerationRequest(
        model=entry.upstream_model,
        input=call.input,
        instructions=call.instructions,
        config=call.config,
    )
    return PreparedGeneration(entry=entry, request=request)


def _missing_capability(entry: RegistryModelEntry, call: TextGenerationCall) -> str | None:
    capabilities = entry.capabilities
    if not capabilities.text_generation:
        return "text generation"
    if call.instructions and not capabilities.system_instructions:
        return "system instructions"
    has_history = any(message.role == "assistant" for message in call.input)
    if has_history and not capabilities.multi_turn_conversation:
        return "multi-turn conversations"
    return None
