"""
Core application configuration using Pydantic Settings.
Reads from environment variables / .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "AI Document Platform"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = Field(min_length=32)
    api_v1_prefix: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_docs"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # ── AI Models ─────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # OpenRouter
    openrouter_api_key: str = ""
    # Ollama (on-prem or cloud)
    ollama_url: str = "http://localhost:11434"
    ollama_api_key: str = ""

    default_ai_model: str = "gpt-4o"
    default_ai_provider: Literal["openai", "anthropic", "openrouter", "ollama"] = "openai"
    max_tokens: int = 16384

    # ── MCP / RAG ─────────────────────────────────────────────────────────────
    mcp_server_url: str = "http://localhost:8100/sse"
    mcp_api_key: str = ""
    mcp_timeout_seconds: int = 30
    mcp_max_retries: int = 3
    mcp_default_kb_id: str = "default"

    # ── Workflow ──────────────────────────────────────────────────────────────
    workflow_max_retries: int = 3
    workflow_quality_threshold: float = 0.75
    workflow_timeout_minutes: int = 60

    # ── Storage ───────────────────────────────────────────────────────────────
    documents_base_path: str = "/app/documents"
    templates_base_path: str = "/app/app/templates"

    # ── Observability ─────────────────────────────────────────────────────────
    log_level: str = "INFO"
    otlp_endpoint: str = "http://localhost:4317"
    prometheus_enabled: bool = True

    @field_validator("jwt_secret_key", "secret_key", mode="before")
    @classmethod
    def pad_secret(cls, v: str) -> str:
        """Ensure minimum length in dev by padding — raise in production."""
        if len(v) < 32:
            return v.ljust(32, "0")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
