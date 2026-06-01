# Author: Sarala Biswal
"""Environment-backed settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RuntimeMode = Literal["mock", "real", "local_sync"]


class RuntimeConfigUpdate(BaseModel):
    """Process-local runtime settings accepted by the config API."""
    model_config = ConfigDict(extra="forbid")

    app_mode: RuntimeMode | None = None
    llm_provider: str | None = None
    llm_model: str | None = None


class RuntimeConfigState(BaseModel):
    """Public runtime settings returned to the UI without secrets."""
    overrides: dict[str, str] = Field(default_factory=dict)


class Settings(BaseSettings):
    """Application settings with environment defaults and process-local overrides."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: str = Field("local_sync", alias="APP_MODE")
    redis_url: str | None = Field("redis://localhost:6379", alias="REDIS_URL")
    database_url: str = Field(
        "sqlite:///.local/regulated_decisioning.db",
        alias="DATABASE_URL",
    )
    mlflow_tracking_uri: str = Field("http://localhost:5001", alias="MLFLOW_TRACKING_URI")
    jaeger_endpoint: str = Field("http://localhost:4317", alias="JAEGER_ENDPOINT")
    llm_provider: str = Field("ollama", alias="LLM_PROVIDER")
    llm_model: str = Field("", alias="LLM_MODEL")
    llm_api_key: str = Field("", alias="LLM_API_KEY")
    llm_base_url: str = Field("", alias="LLM_BASE_URL")
    llm_timeout_seconds: float = Field(2.0, alias="LLM_TIMEOUT_SECONDS")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("llama3.1", alias="OLLAMA_MODEL")
    openai_model: str = Field("openai/gpt-4o-mini", alias="OPENAI_MODEL")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    anthropic_model: str = Field("anthropic/claude-sonnet-4-6", alias="ANTHROPIC_MODEL")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")
    default_domain: str = Field("insurance", alias="DEFAULT_DOMAIN")
    default_jurisdiction: str = Field("US_CA", alias="DEFAULT_JURISDICTION")
    cors_origins: str = Field("", alias="CORS_ORIGINS")

    def public_dict(self) -> dict[str, str | None]:
        """Expose non-secret runtime settings to the UI and settings API."""
        data = self.model_dump()
        data.pop("llm_api_key", None)
        data.pop("openai_api_key", None)
        data.pop("anthropic_api_key", None)
        data["llm_provider_status"] = {
            "selected": self.llm_provider,
            "openai_configured": bool(self.openai_api_key),
            "anthropic_configured": bool(self.anthropic_api_key),
            "custom_configured": bool(self.llm_model and self.llm_api_key),
            "ollama_configured": bool(self.ollama_base_url),
        }
        return data


_RUNTIME_OVERRIDES: dict[str, str] = {}


def runtime_config_state() -> RuntimeConfigState:
    """Build the public runtime config snapshot from current settings."""
    return RuntimeConfigState(overrides=_RUNTIME_OVERRIDES.copy())


def update_runtime_config(update: RuntimeConfigUpdate) -> RuntimeConfigState:
    """Apply process-local overrides without writing secrets or editing env files."""
    updates = update.model_dump(exclude_none=True)
    if updates.get("llm_provider") == "mock":
        updates["llm_model"] = "mock"
    _RUNTIME_OVERRIDES.update({key: str(value) for key, value in updates.items()})
    get_settings.cache_clear()
    return runtime_config_state()


def reset_runtime_config() -> RuntimeConfigState:
    """Clear process-local runtime overrides and refresh cached settings."""
    _RUNTIME_OVERRIDES.clear()
    get_settings.cache_clear()
    return runtime_config_state()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings, merging runtime overrides when present."""
    settings = Settings()
    if not _RUNTIME_OVERRIDES:
        return settings
    return settings.model_copy(update=_RUNTIME_OVERRIDES)
