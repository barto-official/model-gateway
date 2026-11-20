# Tech stack

- Python 3.12+
- FastAPI
- Pydantic v2
- HTTPX
- asyncio
- uv
- pytest
- Ruff
- ty

# Architecture

Modular monolith with hexagonal architecture (ports and adapters). One deployable API process. The CLI is a second entrypoint over the same package.

`domain` and `application` do not import FastAPI, the provider SDKs, or the YAML loader. Adapters and `bootstrap.py` import inward.

```text
src/model_gateway/
  domain/                 # canonical chat, errors, model descriptor, ports
  application/            # chat and stream use cases, routing, execution policy
  adapters/
    inbound/http/         # FastAPI, SSE mapping
    outbound/openai/      # openai SDK
    outbound/anthropic/   # anthropic SDK
    outbound/google/      # google-genai SDK
    outbound/config/      # env and YAML registry loader
  bootstrap.py            # composition root: wire adapters to ports
```

Phase 0 creates `domain`, `application`, `adapters/inbound/http`, `adapters/outbound/config`, and `bootstrap.py`. Each provider package arrives with its adapter. Telemetry and access-control packages arrive in their own phases.

Model identity, capabilities, and alias resolution live in `application`. Reading YAML lives in `adapters/outbound/config`.

# CICD
- Github Actions
- Conventional Commits and Branches

# Model Providers:
- OpenAI
- Claude
- Google

## Provider integration strategy

Integrate OpenAI, Anthropic (Claude), and Google (Gemini) through their **official Python SDKs**, not hand-rolled REST clients.

| Provider | Preferred SDK package | Notes |
| --- | --- | --- |
| OpenAI | `openai` |
| Anthropic | `anthropic` |  |
| Google | `google-genai` | |

**HTTPX** remains in the stack for the gateway’s own HTTP surface (clients calling us), health probes, and tests—not as the primary path to provider APIs.

Use raw HTTP only when there is a documented reason, for example: an SDK gap for a required feature, a bug blocking production behavior, or a temporary workaround until the SDK catches up. Adapters that need a HTTP escape hatch should isolate it behind a small internal helper so the default path stays SDK-based.


# Capabilities

The uploaded document contains two tables.

## **1. Unified API and model abstraction**

| Capability             | Description                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| Unified API endpoint   | Exposes one endpoint for accessing multiple LLM providers.                                       |
| Provider abstraction   | Hides provider-specific API differences from applications.                                       |
| Request normalization  | Converts requests into provider-compatible formats.                                              |
| Response normalization | Returns responses in a consistent schema.                                                        |
| Model registry         | Maintains a catalog of available models and deployments.                                         |
| Model aliases          | Allows applications to use logical names such as general-purpose rather than physical model IDs. |
| Provider adapters      | Integrates with OpenAI, Anthropic, Google, Azure, AWS, self-hosted models, etc.                  |
| Streaming support      | Relays responses incrementally to clients.                                                       |
| Error normalization    | Converts provider-specific errors into common error categories.                                  |
| Capability discovery   | Exposes which models support tools, JSON output, vision, embeddings, streaming, etc.             |
| Parameter translation  | Maps compatible generation parameters across providers.                                          |
| Request validation     | Checks inputs, model IDs, parameters, and payload schemas before forwarding.                     |

## **2. Authentication and access control**

| Capability                     | Description                                                           |
| ------------------------------ | --------------------------------------------------------------------- |
| API key authentication         | Authenticates applications requesting model access.                   |
| Provider credential management | Stores and manages upstream provider credentials.                     |
| Virtual API keys               | Issues gateway-specific keys to applications, users, or teams.        |
| Key rotation                   | Supports credential rotation and revocation.                          |
| Model access restrictions      | Controls which models particular consumers can invoke.                |
| Role-based access control      | Defines permissions for administrators, developers, and consumers.    |
| Consumer identification        | Associates requests with specific users, teams, services, or tenants. |
| Key scoping                    | Restricts keys by environment, model, application, or organization.   |

## **3. Basic model routing and traffic management**

| Capability            | Description                                                 |
| --------------------- | ----------------------------------------------------------- |
| Model selection       | Routes a request to its designated model.                   |
| Provider selection    | Selects the provider or deployment serving the model.       |
| Static routing        | Uses predefined mappings from model aliases to deployments. |
| Weighted routing      | Distributes requests using configurable percentages.        |
| Round-robin balancing | Alternates requests between eligible deployments.           |
| Basic load balancing  | Spreads traffic across multiple endpoints.                  |
| Rate limiting         | Restricts request frequency per key, user, or application.  |
| Concurrency limiting  | Limits simultaneous in-flight requests.                     |
| Request quotas        | Restricts usage over daily, weekly, or monthly periods.     |
| Request timeouts      | Enforces maximum durations for upstream calls.              |
| Payload size limits   | Rejects oversized request bodies.                           |

## **4. Reliability and resilience**

| Capability           | Description                                                    |
| -------------------- | -------------------------------------------------------------- |
| Automatic retries    | Retries transient failures.                                    |
| Retry backoff        | Spaces retries to avoid overloading providers.                 |
| Provider fallback    | Switches providers after a failure.                            |
| Model fallback       | Switches to another eligible model.                            |
| Circuit breakers     | Temporarily stops sending traffic to unhealthy endpoints.      |
| Health checks        | Tracks whether configured deployments are reachable or usable. |
| Error handling       | Standardizes upstream errors and recovery behavior.            |
| Retry limits         | Prevents uncontrolled retry loops.                             |
| Deadline propagation | Ensures the request respects a time budget across attempts.    |
| Connection pooling   | Reuses upstream connections where supported.                   |

## **5. Usage metering and basic cost management**

| Capability            | Description                                               |
| --------------------- | --------------------------------------------------------- |
| Token counting        | Measures input and output token consumption.              |
| Usage tracking        | Tracks request volume and model consumption.              |
| Cost estimation       | Estimates spending using model-specific pricing.          |
| Cost attribution      | Associates consumption with teams, keys, or applications. |
| Budget limits         | Enforces spending limits for defined consumers.           |
| Usage reporting       | Provides aggregated consumption statistics.               |
| Model pricing catalog | Stores pricing information for supported models.          |

## **6. Logging, monitoring, and administration**

| Capability               | Description                                              |
| ------------------------ | -------------------------------------------------------- |
| Request logging          | Records request metadata and optionally payloads.        |
| Response logging         | Records response metadata and optionally outputs.        |
| Error logging            | Tracks failures and provider error codes.                |
| Latency monitoring       | Measures response times.                                 |
| Token usage metrics      | Reports token consumption over time.                     |
| Throughput metrics       | Tracks requests per second/minute.                       |
| Administrative dashboard | Shows usage, costs, provider status, and configurations. |
| Configuration management | Manages routes, models, API keys, and policies.          |
| Audit logging            | Records administrative and security-relevant actions.    |
| Request IDs              | Provides identifiers for tracing individual requests.    |


# Prioritization

*This list may not include all capabilities. Source of truth is capabilities talbe*

### **Domain 1 — Provider integration**

| Capability | Priority |
| --- | --- |
| Native OpenAI adapter | P0  |
| Native Anthropic adapter | P0  |
| Native Google Gemini adapter | P0  |
| Canonical request/response mapping | P0  |
| Provider error normalization | P0  |
| Model registry | P0  |
| Model capability validation | P0  |
| Provider-specific configuration | P0  |
| Provider health and availability tracking | P1  |
| Dynamic model metadata updates | P2  |

A core principle is to avoid designing the entire gateway around OpenAI's request format.

We should have our own internal domain contracts, even if we later expose an OpenAI-compatible public endpoint.

### **Domain 2 — Inference capabilities**

| Capability | Priority |
| --- | --- |
| Text generation | P0  |
| Multi-message conversations | P0  |
| System instructions | P0  |
| Generation parameters | P0  |
| Streaming via SSE | P0  |
| Normalized stop reasons | P0  |
| Tool/function calling | P1  |
| Structured JSON outputs | P1  |
| Vision/image inputs | P1  |
| Extended reasoning controls | P1  |
| Audio input/output | P2  |
| Embeddings | P2  |
| Batch inference | P2  |
| Realtime interactions | P2  |

These features need capability checks because support, parameters, and semantics differ across providers and models.

### **Domain 3 — Execution and reliability**

| Capability | Priority |
| --- | --- |
| Request lifecycle management | P0  |
| Async upstream execution | P0  |
| Configurable timeouts | P0  |
| Request cancellation | P0  |
| Error taxonomy | P0  |
| Streaming interruption handling | P0  |
| Retry with backoff and jitter | P1  |
| Concurrency limits | P1  |
| Circuit breakers | P1  |
| Retry budgets | P1  |
| Admission control / load shedding | P1  |
| Advanced provider failover | P2  |

I would implement explicit execution semantics before introducing automated fallback. Retrying an operation after a timeout may carry both cost and duplicate-execution risks.

### **Domain 4 — Model selection and routing**

| Capability | Priority |
| --- | --- |
| Explicit provider selection | P0  |
| Explicit model selection | P0  |
| Model aliases | P1  |
| Configuration-based routing | P1  |
| Capability-based routing | P1  |
| Primary and fallback targets | P1  |
| Weighted traffic routing | P2  |
| Cost-aware routing | P2  |
| Latency-aware routing | P2  |
| Quality-aware routing | P2  |
| Intelligent/adaptive routing | P2  |

For the MVP, explicit provider and model selection are enough. Automatic routing should arrive only after we have reliable model metadata, telemetry, and evaluation data.

### **Domain 5 — Observability**

| Capability | Priority |
| --- | --- |
| Request IDs | P0  |
| Structured logging | P0  |
| Basic latency measurements | P0  |
| Provider/model attribution | P0  |
| OpenTelemetry tracing | P1  |
| Metrics and dashboards | P1  |
| TTFT measurements | P1  |
| Error classification dashboards | P1  |
| Provider performance analysis | P1  |
| Detailed cost dashboards | P2  |

### **Domain 6 — Usage, costs, and optimization**

| Capability | Priority |
| --- | --- |
| Provider-reported token usage | P0  |
| Normalized usage metadata | P0  |
| Cost estimation | P1  |
| Versioned model pricing | P1  |
| Tenant/project usage aggregation | P1  |
| Token quotas | P1  |
| Budget limits | P1  |
| Provider-native prompt caching | P1  |
| Gateway-level response caching | P2  |
| Advanced cost optimization | P2  |

### **Domain 7 — Security and access control**

| Capability | Priority |
| --- | --- |
| Provider credentials in secret storage | P0  |
| Secure configuration | P0  |
| Authentication at network/service boundary | P0  |
| Gateway API keys | P1  |
| Key rotation/revocation | P1  |
| Tenant/project identity | P1  |
| Model access policies | P1  |
| Rate limiting | P1  |
| Audit logs | P1  |
| Role-based administration | P2  |

**Roadmap note — authentication deferred:** Early milestones rely on a **trusted execution boundary** (local dev, private network, platform ingress, or mTLS at the edge) instead of gateway-issued API keys. Provider secrets still load from environment or a secret store from day one. **Consumer authentication** (virtual API keys, RBAC, per-tenant policies, audit) is scheduled in **Phase 9** at the end of the roadmap so core inference and normalization stabilize first.

### **Domain 8 — Configuration and administration**

| Capability | Priority |
| --- | --- |
| Environment-based configuration | P0  |
| Model registry configuration | P0  |
| Configuration validation | P0  |
| Provider credentials references | P0  |
| Persistent configuration | P1  |
| Per-client policies | P1  |
| Configuration versioning | P1  |
| Administrative API | P1  |
| Web dashboard | P2  |
| Dynamic configuration rollout | P2  |

### **Domain 9 — Evaluation and quality**

| Capability | Priority |
| --- | --- |
| Provider contract tests | P0  |
| Streaming integration tests | P0  |
| Failure simulation | P0  |
| Evaluation datasets | P1  |
| Cross-model quality benchmarking | P1  |
| Structured-output correctness | P1  |
| Model change regression tests | P1  |
| Quality-aware routing signals | P2  |
| Automated routing optimization | P2  |

---
