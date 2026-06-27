from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./quantbot.db"
    fmp_api_key: str | None = None
    collect_cron_hour: int = Field(default=22, ge=0, le=23)
    collect_cron_minute: int = Field(default=0, ge=0, le=59)
    scheduler_collect_prices: bool = False
    scheduler_lookback_days: int = Field(default=365, ge=1)
    scheduler_catch_up_on_startup: bool = True
    scheduler_stale_after_days: int = Field(default=1, ge=0)
    holdings_http_timeout: float = Field(default=30.0, gt=0)
    signal_min_aum: float = Field(default=100_000_000, ge=0)
    signal_exchanges: str = (
        "NASDAQ,NasdaqGS,NasdaqGM,NasdaqCM,NMS,NGM,NCM,"
        "NYSE,NYQ,NYSEArca,NYSE Arca,PCX,"
        "Cboe US,Cboe BZX,BATS,BTS,NYSE American,ASE"
    )
    admin_token: str = "change-me"
    admin_allowed_emails: str = ""  # comma-separated
    admin_allowed_groups: str = ""  # comma-separated
    admin_rate_limit_per_minute: int = Field(default=30, ge=1)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    auto_create_tables: bool = True
    seed_universe_on_startup: bool = True
    scheduler_enabled: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot contain '*' while credentials are enabled")
        return origins

    @property
    def signal_exchange_list(self) -> list[str]:
        return [
            exchange.strip()
            for exchange in self.signal_exchanges.split(",")
            if exchange.strip()
        ]

    @property
    def allowed_email_set(self) -> set[str] | None:
        values = {email.strip().lower() for email in self.admin_allowed_emails.split(",") if email.strip()}
        return values if values else None

    @property
    def allowed_group_set(self) -> set[str] | None:
        values = {group.strip().lower() for group in self.admin_allowed_groups.split(",") if group.strip()}
        return values if values else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
