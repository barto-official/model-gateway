"""HTTP tests for POST /v1/generations."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.doubles.fake_inference_backend import FakeInferenceBackend

from model_gateway.adapters.outbound.config import load_model_registry, load_settings
from model_gateway.application.backend_registry import InferenceBackendRegistry
from model_gateway.application.registry import RegistryProvider
from model_gateway.bootstrap import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = REPO_ROOT / "config" / "models.yaml"


def _client_with_fake_backend() -> TestClient:
    settings = load_settings(environment="http-test")
    catalog = load_model_registry(DEFAULT_REGISTRY)
    backends = InferenceBackendRegistry(
        {RegistryProvider.OPENAI.value: FakeInferenceBackend(name="openai")}
    )
    return TestClient(
        create_app(
            settings,
            model_registry=catalog,
            inference_backends=backends,
        ),
    )


def test_post_generations_returns_output() -> None:
    """A valid registry model returns generation JSON."""
    client = _client_with_fake_backend()
    response = client.post(
        "/v1/generations",
        json={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input": [{"role": "user", "content": "Hi"}],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["output_text"] == "Hi [fake]"
    assert body["model"] == "gpt-4o-mini"


def test_post_generations_unknown_model_problem_detail() -> None:
    """Unknown catalog ids return 404 problem details."""
    client = _client_with_fake_backend()
    response = client.post(
        "/v1/generations",
        json={
            "provider": "openai",
            "model": "missing",
            "input": [{"role": "user", "content": "Hi"}],
        },
    )
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["code"] == "model_not_found"


def test_post_generations_rejects_stream() -> None:
    """Streaming requests are rejected at the HTTP schema."""
    client = _client_with_fake_backend()
    response = client.post(
        "/v1/generations",
        json={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input": [{"role": "user", "content": "Hi"}],
            "stream": True,
        },
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
