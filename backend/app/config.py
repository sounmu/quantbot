from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./quantbot.db"
    fmp_api_key: str | None = None
    collect_cron_hour: int = Field(default=22, ge=0, le=23)
    collect_cron_minute: int = Field(default=0, ge=0, le=59)
    scheduler_collect_prices: bool = False
    scheduler_lookback_days: int = Field(default=365, ge=1)
    holdings_http_timeout: float = Field(default=30.0, gt=0)
    admin_token: str = "change-me"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    auto_create_tables: bool = True
    seed_universe_on_startup: bool = True
    scheduler_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
