# Configuration Guide

`model-gateway` can be configured using CLI options, environment variables, and configuration files.

Configuration is resolved once at startup and then passed into the application as typed settings.

## Configuration precedence

When the same setting is provided in multiple places, the following order is used:

```text
CLI option > environment variable > configuration file > default
```

Example:

```bash
CONTRACT_CHECK_OUTPUT_FORMAT=markdown \
model-gateway validate contract.yaml --format json
```

The final output format is `json` because the CLI option has higher priority than the environment variable.

______________________________________________________________________

## Configuration sources

### 1. CLI options

CLI options are explicit per-command overrides.

Example:

```bash
model-gateway validate contract.yaml \
  --profile prod \
  --format json \
  --strict
```

Use CLI options for one-off command behavior.

### 2. Environment variables

Environment variables are useful for CI, Docker, Kubernetes, and local shell configuration.

Example:

```bash
export CONTRACT_CHECK_PROFILE=dev
export CONTRACT_CHECK_OUTPUT_FORMAT=json
export CONTRACT_CHECK_LOG_LEVEL=debug
```

Then run:

```bash
model-gateway validate contract.yaml
```

### 3. Configuration file

Configuration files are useful for durable project or user settings.

By default, `model-gateway` looks for configuration in:

```text
./model-gateway.toml
./pyproject.toml
~/.config/model-gateway/config.toml
```

A specific config file can be provided with:

```bash
model-gateway --config ./config/prod.toml validate contract.yaml
```

### 4. Defaults

If no value is provided, the CLI uses safe defaults.

______________________________________________________________________

## Example configuration file

`model-gateway.toml`:

```toml
[default]
profile = "dev"
output_format = "table"
log_level = "warning"
strict = false
color = "auto"

[profiles.dev]
workspace_host = "https://dev-workspace.cloud.databricks.com"
catalog = "dev_catalog"
schema = "analytics"

[profiles.prod]
workspace_host = "https://prod-workspace.cloud.databricks.com"
catalog = "prod_catalog"
schema = "analytics"
strict = true
```

______________________________________________________________________

## `pyproject.toml` configuration

For project-local configuration, you can also use:

```toml
[tool.model-gateway]
profile = "dev"
output_format = "json"
log_level = "info"

[tool.model-gateway.profiles.dev]
workspace_host = "https://dev-workspace.cloud.databricks.com"
catalog = "dev_catalog"
schema = "analytics"
```

Use `pyproject.toml` when the configuration belongs to the repository.

Use `~/.config/model-gateway/config.toml` when the configuration belongs to the user.

______________________________________________________________________

## Supported settings

| Setting           | Type       |   Default | Description                            |
| ----------------- | ---------- | --------: | -------------------------------------- |
| `profile`         | string     |     unset | Active configuration profile.          |
| `workspace_host`  | URL string |     unset | Databricks workspace host.             |
| `catalog`         | string     |     unset | Default catalog.                       |
| `schema`          | string     |     unset | Default schema.                        |
| `output_format`   | enum       |   `table` | Default output format.                 |
| `log_level`       | enum       | `warning` | Diagnostic log level.                  |
| `strict`          | boolean    |   `false` | Treat warnings as failures.            |
| `color`           | enum       |    `auto` | Color mode: `auto`, `always`, `never`. |
| `timeout_seconds` | integer    |      `30` | External request timeout.              |

______________________________________________________________________

## Environment variables

All environment variables use the `CONTRACT_CHECK_` prefix.

| Environment variable             | Setting           | Example                                |
| -------------------------------- | ----------------- | -------------------------------------- |
| `CONTRACT_CHECK_PROFILE`         | `profile`         | `dev`                                  |
| `CONTRACT_CHECK_WORKSPACE_HOST`  | `workspace_host`  | `https://example.cloud.databricks.com` |
| `CONTRACT_CHECK_CATALOG`         | `catalog`         | `main`                                 |
| `CONTRACT_CHECK_SCHEMA`          | `schema`          | `analytics`                            |
| `CONTRACT_CHECK_OUTPUT_FORMAT`   | `output_format`   | `json`                                 |
| `CONTRACT_CHECK_LOG_LEVEL`       | `log_level`       | `debug`                                |
| `CONTRACT_CHECK_STRICT`          | `strict`          | `true`                                 |
| `CONTRACT_CHECK_COLOR`           | `color`           | `never`                                |
| `CONTRACT_CHECK_TIMEOUT_SECONDS` | `timeout_seconds` | `60`                                   |

Example:

```bash
CONTRACT_CHECK_PROFILE=prod \
CONTRACT_CHECK_OUTPUT_FORMAT=json \
model-gateway validate contract.yaml
```

______________________________________________________________________

## Secrets

Do not store long-lived secrets in committed configuration files.

Supported secret sources:

```text
environment variables
Databricks CLI profile
OS keychain / credential helper, if configured
CI secret manager
cloud secret manager
```

Example:

```bash
export DATABRICKS_TOKEN=...
model-gateway validate contract.yaml --profile prod
```

Secret values are redacted in diagnostics:

```text
DATABRICKS_TOKEN=********
```

They are also redacted in:

```bash
model-gateway config show
model-gateway doctor
```

unless explicitly requested.

⚠️ Avoid passing secrets directly as command-line arguments because they may appear in shell history or process listings.

______________________________________________________________________

## Inspecting resolved configuration

Use:

```bash
model-gateway config show
```

Show sources:

```bash
model-gateway config show --show-sources
```

Example output:

```text
profile           dev        env: CONTRACT_CHECK_PROFILE
output_format     json       cli: --format
log_level         warning    default
workspace_host    ********   config: profiles.dev.workspace_host
```

JSON output:

```bash
model-gateway config show --format json --show-sources
```

______________________________________________________________________

## Configuration errors

Invalid configuration fails before validation starts.

Example:

```text
Configuration error: CONTRACT_CHECK_TIMEOUT_SECONDS='abc' is invalid.
Expected a positive integer.
```

The command exits with code `3`.

______________________________________________________________________

## Best practices

Use project configuration for repository defaults:

```text
pyproject.toml
model-gateway.toml
```

Use environment variables for runtime/deployment-specific settings:

```text
CI
Docker
Kubernetes
local shell
```
