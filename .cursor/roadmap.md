
# Implementation roadmap

Phases are sequential in intent; some work can overlap within a phase (e.g. three provider adapters in parallel once contracts exist). **Exit criteria** state what “done” means before moving on. Capability tables above remain the source of truth for scope; this section orders delivery.


## Phase 0 — Repository foundation

**Goals:** Runnable API shell, configuration model, internal domain contracts and the provider port (not OpenAI-shaped), CI unchanged.

| Work item | Maps to |
| --- | --- |
| FastAPI app, lifespan, health endpoints in `adapters/inbound/http` | Execution P0, Observability P0 |
| Pydantic models for canonical chat request/response in `domain` | Domain 1 canonical mapping |
| Provider port (`InferenceBackend`) in `domain` | Provider abstraction |
| Settings from environment in `adapters/outbound/config` | Domain 8 P0, Domain 7 provider secrets P0 |
| Composition root in `bootstrap.py` | Provider abstraction |
| Contract tests harness (mocked port, no SDK imports in `domain` or `application`) | Domain 9 P0 |

Package layout and the dependency rule are defined in `.cursor/project_setup.md` under Architecture. Phase 0 creates `domain`, `application`, `adapters/inbound/http`, `adapters/outbound/config`, and `bootstrap.py` only.

**Exit criteria:** `uv run pytest` passes; ty/ruff/prek clean; `/health` returns OK; no provider call required for CI. `domain` and `application` do not import FastAPI or provider SDKs.

**Out of scope:** Gateway API keys, persistence DB, dashboard.

---

## Phase 1 — Internal provider layer (SDK adapters): (!: Deffered, see @agents.md)

**Goals:** Three outbound adapters behind the `InferenceBackend` port. SDK imports stay inside `adapters/outbound/{openai,anthropic,google}`. No public unified route yet except optionally a dev-only invoke.

| Work item | Maps to |
| --- | --- |
| OpenAI adapter (`openai` async) | Native OpenAI adapter P0 |
| Anthropic adapter (`anthropic`) | Native Anthropic adapter P0 |
| Google adapter (`google-genai`) | Native Google Gemini adapter P0 |
| Request/response translation to canonical models | Canonical mapping P0 |
| Provider error → gateway error taxonomy | Provider error normalization P0 |
| Provider-specific config (base URL, project, region) | Provider-specific configuration P0 |

**Exit criteria:** Integration tests against recorded fixtures or optional live keys; each adapter supports non-streaming chat with system + user messages and returns normalized usage metadata when the SDK exposes it.

**SDK-first rule:** Implement with SDK types and methods; document any HTTP fallback in adapter README or module docstring.

---

## Phase 2 — Unified inference API (MVP)

**Goals:** One HTTP API for applications; explicit `provider` + `model` (or registry id); text generation MVP. Routes in `adapters/inbound/http` stay thin and call a chat use case in `application`. Model identity and capability checks live in `application`. YAML loading stays in `adapters/outbound/config`.

| Work item | Maps to |
| --- | --- |
| Unified chat/completions endpoint | Unified API endpoint P0 |
| Request validation (model id, params, payload) | Request validation P0 |
| Model registry (static config file → later dynamic) | Model registry P0 |
| Registry entries: provider, model id, capabilities flags | Model capability validation P0 |
| Multi-message conversations, system instructions | Inference P0 |
| Generation parameters with cross-provider translation | Parameter translation P0 |
| Normalized stop reasons | Inference P0 |

**Exit criteria:** Same client payload can target OpenAI, Anthropic, or Google by changing registry model id; errors and successes share one response schema. (EDIT: we use only OpenAI)

**Out of scope:** Model aliases, automatic failover, consumer API keys.

---

## Phase 3 — Streaming and execution semantics

**Goals:** Production-grade request lifecycle before retries and routing magic. The provider port yields canonical stream events. The HTTP adapter maps those events to SSE. SDK stream types stay inside each outbound adapter.

| Work item | Maps to |
| --- | --- |
| SSE (or equivalent) streaming end-to-end | Streaming via SSE P0 |
| Stream normalization across providers | Streaming interruption handling P0 |
| Async upstream execution, timeouts | Execution P0 |
| Client disconnect → upstream cancellation | Request cancellation P0 |
| Request IDs in logs and responses | Observability P0 |
| Structured logging, basic latency | Observability P0 |

**Exit criteria:** Streaming contract tests for all three providers; cancellation test demonstrates upstream abort where SDK supports it.

---

## Phase 4 — Capability discovery and inference extensions (tier 1)

**Goals:** Document and enforce what each model supports; add high-value features with capability gates.

| Work item | Maps to |
| --- | --- |
| `GET /models` or registry discover endpoint | Capability discovery P0 |
| Tool/function calling (per provider SDK) | Inference P1 |
| Structured JSON / schema outputs where supported | Inference P1 |
| Vision / image inputs | Inference P1 |
| Provider-reported token usage in responses | Usage P0 |

**Exit criteria:** Calling an unsupported capability returns a validation error referencing the model’s capability set, not an opaque provider 400.

---

## Phase 5 — Reliability and traffic controls (no smart routing)

**Goals:** Explicit execution policies in `application`, wrapping the provider port. Timeouts, retries, and concurrency limits are not reimplemented inside each provider package. No automatic model fallback until telemetry exists.

| Work item | Maps to |
| --- | --- |
| Retry with backoff + jitter (idempotent-safe paths) | Execution P1 |
| Retry budgets / limits | Execution P1 |
| Concurrency limits (global or per-deployment) | Execution P1 |
| Payload size limits | Routing/limits P0 |
| Optional circuit breaker per provider endpoint | Execution P1 |
| Rate limiting (global/deployment — **not** per consumer key yet) | Domain 3 rate limiting (simplified) |

**Exit criteria:** Failure simulation tests (Domain 9 P0); documented semantics for timeout vs retry vs duplicate risk.

**Deferred within phase:** Weighted routing, provider fallback chains, cost-aware routing (Domain 4 P2).

---

## Phase 6 — Routing and configuration depth

**Goals:** Ergonomics for operators without adaptive routing. Alias and fallback resolution stay in `application`. The config adapter only loads the tables.

| Work item | Maps to |
| --- | --- |
| Model aliases (`general-purpose` → concrete model) | Domain 4 P1 |
| Static / config-based routing tables | Domain 4 P1 |
| Primary + fallback targets (explicit config) | Domain 4 P1 |
| Environment + file-based config validation | Domain 8 P0 |
| Persistent configuration (file or store) | Domain 8 P1 |

**Exit criteria:** Alias resolves to a single deployment; optional configured fallback list works with Phase 5 retry semantics.

---

## Phase 7 — Observability, metering, and cost (operational)

**Goals:** Operate the gateway in shared environments before opening multi-tenant access. The use case records canonical usage. OpenTelemetry export is an outbound adapter (`adapters/outbound/telemetry`), added in this phase.

| Work item | Maps to |
| --- | --- |
| OpenTelemetry tracing (optional exporter) | Observability P1 |
| Metrics: latency, errors, throughput | Observability P1 |
| TTFT for streams | Observability P1 |
| Normalized usage aggregation | Domain 6 P0–P1 |
| Model pricing catalog + cost estimation | Domain 6 P1 |
| Administrative read API (models, routes, health) | Domain 8 P1 |

**Exit criteria:** Operator can attribute usage by model/provider; cost estimate available per request when pricing configured.

**Deferred:** Web dashboard (P2), detailed cost optimization (P2).

---

## Phase 8 — Advanced inference and platform features

**Goals:** Lower-priority product surface after the gateway is operable.

| Work item | Maps to |
| --- | --- |
| Embeddings (SDK per provider) | Inference P2 |
| Batch inference where SDK supports it | Inference P2 |
| Gateway-level response caching | Domain 6 P2 |
| Evaluation datasets / regression suites | Domain 9 P1 |
| Weighted or cost-aware routing experiments | Domain 4 P2 |

**Exit criteria:** Each item is independently shippable; no blocker for Phase 9.

---

## Phase 9 — Authentication, access control, and hardening (last)

**Goals:** Everything in **Domain 7** that governs **who** may call the gateway, not how inference works. Access control is an inbound adapter in front of the existing use cases. The chat use case receives an already-identified caller.

| Work item | Maps to |
| --- | --- |
| Gateway API keys (virtual keys) | Domain 7 P1, Capabilities §2 |
| Key rotation and revocation | Domain 7 P1 |
| Consumer / tenant identity on requests | Domain 7 P1 |
| Model access policies per key or tenant | Domain 7 P1 |
| Per-key rate limits and quotas | Domain 3 + Domain 7 |
| Audit logging for admin and security events | Domain 7 P1 |
| Role-based administration | Domain 7 P2 |

**Prerequisites:** Phases 2–7 stable; clear request context propagation (request ID → future consumer ID).

**Exit criteria:** Public or shared deployment checklist satisfied: unauthenticated inference rejected; policies enforce model restrictions; audit trail for key lifecycle.

**Still not in scope unless added later:** Full SSO for humans, billing integrations, web dashboard auth.

---

## Suggested first vertical slice (optional shorter path)

If you want an early demonstrator before completing all of Phase 2:

1. Phase 0 + OpenAI-only slice of Phase 1.
2. Single `POST /v1/chat` with canonical schema (Phase 2 subset).
3. Phase 3 streaming for OpenAI only.
4. Expand to Anthropic and Google before locking public API versioning.
