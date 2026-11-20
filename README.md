# Model Gateway

Internal gateway for routing, policy, and observability around LLM and embedding provider APIs.

## Overview

Model Gateway centralizes how backend services call external model APIs. It provides a single integration surface (library and CLI), consistent configuration, and documentation aligned with the rest of our Python services.

- **Library** (`model_gateway`) — programmatic validation and gateway hooks.
- **CLI** — Typer-based tooling for local workflows and smoke tests.
- **Docs** — MkDocs site published from `docs/`.

## Table of Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Development](#development)
- [Project structure](#project-structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- Python 3.12+ package layout (`src/model_gateway`)
- Typer CLI with generated reference in MkDocs
- Configuration via env vars and TOML (`model_gateway.toml`)
- Pre-commit, Ruff, mypy, and pytest in CI
- Semantic versioning and release workflows

## Tech stack

- **Language:** Python 3.12+
- **CLI:** Typer
- **Config:** Pydantic Settings (scaffold)
- **Docs:** MkDocs Material
- **CI/CD:** GitHub Actions
- **Tooling:** `uv`, Ruff, mypy, pytest

## Getting started

This project is managed with `uv` and `pyproject.toml`. Dependencies are locked in `uv.lock`.

### Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)

### Install

```bash
uv sync --dev
```

### Run tests and checks

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src/model_gateway
```

### CLI (development)

```bash
uv run python -m model_gateway_cli
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full quality gate and docs workflow.

## Configuration

Configuration is loaded from environment variables, `model_gateway.toml` in the project tree, and user config under `~/.config/model_gateway/`. Details live in [docs/guides/configuration.md](docs/guides/configuration.md).

## Development

- Conventional Commits (see [`.cursor/rules/conventional_commits.mdc`](.cursor/rules/conventional_commits.mdc))
- `main` is the default branch; use feature branches for changes
- Run `uv run prek run --all-files` before opening a PR

## Project structure

```text
model-gateway/
├── src/
│   ├── model_gateway/              # Library (hexagonal layout)
│   │   ├── bootstrap.py            # Composition root
│   │   ├── domain/                 # Models, errors, ports
│   │   ├── application/            # Use cases and routing
│   │   ├── adapters/
│   │   │   ├── inbound/http/       # FastAPI and SSE (later phases)
│   │   │   └── outbound/config/    # Env and registry loading
│   │   └── hello.py                # Quickstart doctest helper
│   └── model_gateway_cli/          # CLI entrypoints and adapter
├── docs/                           # MkDocs source
├── scripts/                        # Doc generation and repo policy
├── tests/
└── pyproject.toml
```

## Documentation

Build locally:

```bash
uv sync --group docs
uv run python scripts/generate_cli_reference.py model_gateway
uv run mkdocs serve
```

Published site: [https://barto-official.github.io/model-gateway/](https://barto-official.github.io/model-gateway/)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).
