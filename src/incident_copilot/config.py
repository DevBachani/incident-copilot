"""Typed application settings.

Secrets are read only from the environment (loaded from `.env` in dev), never hard-coded.
Import `get_settings()` anywhere you need configuration.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider keys (free tiers) ---
    groq_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)
    openrouter_api_key: str | None = Field(default=None)

    # --- Model ids (override in .env if a provider renames a model) ---
    groq_model: str = "groq/openai/gpt-oss-20b"
    groq_model_large: str = "groq/openai/gpt-oss-120b"
    gemini_model: str = "gemini/gemini-3.8-flash"
    openrouter_model: str = "openrouter/nvidia/nemotron-3.5-lightning:free"

    # --- Observability (Phase 9) ---
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # --- Data stores (Phase 1+) ---
    database_url: str = "postgresql://postgres:postgres@localhost:5432/incident_copilot"
    redis_url: str = "redis://localhost:6379/0"

    # --- Observability backends (M2 tools) ---
    prometheus_url: str = "http://localhost:9090"
    jaeger_url: str = "http://localhost:16686"
    shop_namespace: str = "shop"
    tool_output_token_cap: int = 1500  # hard cap per tool output (free-tier budget)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
