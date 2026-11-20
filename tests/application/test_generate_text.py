"""Tests for :class:`~model_gateway.application.generate_text.GenerateTextUseCase`."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest
from tests.doubles.fake_inference_backend import FakeInferenceBackend

from model_gateway.application.generate_text import GenerateTextUseCase
from model_gateway.domain import GenerationRequest, InputMessage

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "src" / "model_gateway" / "application"
FORBIDDEN_APPLICATION_IMPORTS = ("fastapi", "openai", "httpx")


def test_generate_text_use_case_delegates_to_backend() -> None:
    """The use case forwards the request unchanged and returns the backend response."""
    backend = FakeInferenceBackend(name="test-double", response_suffix="!")
    use_case = GenerateTextUseCase(backend)
    request = GenerationRequest(
        model="gpt-4o-mini",
        input=[InputMessage(role="user", content="ping")],
    )

    response = asyncio.run(use_case.execute(request))

    assert response.output_text == "ping!"
    assert backend.name == "test-double"


@pytest.mark.parametrize("module_name", sorted(p.stem for p in APPLICATION_ROOT.glob("*.py")))
def test_application_module_does_not_import_forbidden_packages(module_name: str) -> None:
    """Application modules must not depend on HTTP frameworks or provider SDKs."""
    path = APPLICATION_ROOT / f"{module_name}.py"
    source = path.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_APPLICATION_IMPORTS:
        assert forbidden not in source, f"{module_name}.py must not reference {forbidden}"

    spec = importlib.util.spec_from_file_location(
        f"model_gateway.application._import_check_{module_name}",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
