"""Runtime settings loaded from the environment."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    """Supported application log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class HttpSettings(BaseModel):
    """HTTP server bind options."""

    model_config = ConfigDict(extra="forbid")

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)


class OpenAISettings(BaseModel):
    """OpenAI provider connection settings (credentials via environment only)."""

    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr | None = None
    base_url: str | None = None
    organization: str | None = None
    project: str | None = None
    timeout_seconds: float = Field(default=60.0, gt=0)


class GatewaySettings(BaseSettings):
    """Top-level gateway configuration resolved at process startup."""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_GATEWAY_",
        env_nested_delimiter="__",
        env_file=None,
        extra="forbid",
    )

    environment: str = "development"
    log_level: LogLevel = LogLevel.INFO
    http: HttpSettings = Field(default_factory=HttpSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)

    @field_validator("environment")
    @classmethod
    def environment_non_empty(cls, value: str) -> str:
        """Reject blank environment labels.

        Returns:
            The trimmed environment name.

        Raises:
            ValueError: If the value is empty or whitespace only.
        """
        if not value.strip():
            msg = "environment must not be empty"
            raise ValueError(msg)
        return value
