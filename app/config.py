"""
Application configuration.

All settings are read from environment variables (or a .env file).
No hard-coded credentials. No defaults that are safe for production.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration object.

    Loaded once at startup via get_settings().
    All values come from environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_NAME: str = "traffic-analytics"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # -----------------------------------------------------------------------
    # API
    # -----------------------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"
    # Accept comma-separated string: "http://a.com,http://b.com"
    # Stored as raw string; use the cors_origins property for the parsed list.
    CORS_ORIGINS: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS as a list, splitting on commas."""
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # -----------------------------------------------------------------------
    # Database (async DSN for application use)
    # -----------------------------------------------------------------------
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="Async PostgreSQL DSN (postgresql+asyncpg://...)",
    )

    # Sync DSN used only by Alembic CLI — never loaded inside the app process.
    ALEMBIC_DATABASE_URL: str = Field(
        ...,
        description="Sync PostgreSQL DSN for Alembic (postgresql+psycopg2://...)",
    )

    DB_POOL_SIZE: int = Field(default=20, ge=1, le=200)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60)

    # -----------------------------------------------------------------------
    # Redis
    # -----------------------------------------------------------------------
    REDIS_URL: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis DSN — included in infrastructure, not yet used in business logic.",
    )

    # -----------------------------------------------------------------------
    # Matching (Phase 2 — values defined now for config completeness)
    # -----------------------------------------------------------------------
    MATCH_SEARCH_WINDOW_MINUTES: int = Field(default=60, ge=1)
    MATCH_CONFIDENCE_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)

    # -----------------------------------------------------------------------
    # Blacklist (Phase 1)
    # -----------------------------------------------------------------------
    BLACKLIST_FUZZY_THRESHOLD: float = Field(default=0.85, ge=0.0, le=1.0)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.

    Cached after the first call. Use dependency injection in FastAPI
    (Depends(get_settings)) for testability — the cache can be cleared
    in tests via get_settings.cache_clear().
    """
    return Settings()
