"""
Application configuration.

Reads environment variables via pydantic-settings. Every value has a sensible
default so the backend can start without a .env file during development.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "VeriTrace AI"
    app_env: str = "development"
    app_debug: bool = True
    app_version: str = "0.1.0"
    enable_api_docs: bool = True

    # ── Server ───────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Input Limits ─────────────────────────────────────────────────────
    max_input_length: int = 10_000

    # ── AI / LLM (Phase 3) ──────────────────────────────────────────────
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # ── Web Search (Phase 3) ─────────────────────────────────────────────
    search_provider: str | None = None
    search_api_key: str | None = None

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./veritrace_dev.db"

    # ── ML Model ─────────────────────────────────────────────────────────
    model_name: str = "FacebookAI/xlm-roberta-base"
    model_device: str = "auto"
    model_max_length: int = 256
    model_load_on_startup: bool = False  # Set True when fine-tuned model ready
    model_backend: str = "local"  # "local" | "hosted" | "mock"
    model_endpoint_url: str | None = None
    model_api_key: str | None = None

    # ── Evidence Retrieval (Google Fact Check & Local) ───────────────────
    google_factcheck_api_key: str | None = None
    evidence_provider: str = "google_factcheck"  # "google_factcheck" | "local" | "hybrid"
    evidence_cache_ttl_seconds: int = 3600
    evidence_timeout_seconds: float = 10.0
    evidence_max_retries: int = 2
    evidence_max_results: int = 10
    evidence_enable_offline_fallback: bool = False

    # ── STEP 7: Evidence Ranking & NLI Verification ──────────────────────
    nli_model_name: str = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
    nli_backend: str = "deterministic"  # "local" | "hosted" | "deterministic"
    nli_endpoint_url: str | None = None
    nli_api_key: str | None = None
    nli_entailment_threshold: float = 0.65
    nli_contradiction_threshold: float = 0.65
    nli_neutral_threshold: float = 0.50
    evidence_min_relevance_threshold: float = 0.30
    evidence_top_k: int = 5
    ranking_weight_similarity: float = 0.50
    ranking_weight_entity: float = 0.35
    ranking_weight_recency: float = 0.15

    # ── Step 8: Decision Fusion, Calibration & Uncertainty ───────────
    calibration_temperature: float = 1.25
    calibration_data_path: str | None = None
    confidence_threshold_high: float = 0.75
    confidence_threshold_moderate: float = 0.50
    conflict_penalty_weight: float = 0.35
    decision_min_independent_sources_for_strong: int = 2

    # ── Step 10: Security, Privacy & Observability ──────────────────────
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    persist_user_input_text: bool = False  # Privacy-first: hash/redact text in DB by default
    data_retention_days: int = 7           # Configurable retention window
    log_format: str = "standard"           # "standard" | "json"



    @property
    def sync_database_url(self) -> str:
        """Convert async URL to sync for Alembic migrations."""
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


# Module-level singleton — import this from anywhere.
settings = Settings()
