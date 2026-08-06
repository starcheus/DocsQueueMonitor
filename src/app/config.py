"""Application configuration via environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    admin_telegram_ids: Annotated[list[int], NoDecode] = Field(
        default_factory=list,
        alias="ADMIN_TELEGRAM_IDS",
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///data/bot.db",
        alias="DATABASE_URL",
    )
    default_language: str = Field(default="uk", alias="DEFAULT_LANGUAGE")
    monitoring_enabled: bool = Field(default=True, alias="MONITORING_ENABLED")
    monitoring_interval_seconds: int = Field(default=90, alias="MONITORING_INTERVAL_SECONDS", ge=15)
    monitoring_jitter_seconds: int = Field(default=30, alias="MONITORING_JITTER_SECONDS", ge=0)
    availability_confirmations: int = Field(default=2, alias="AVAILABILITY_CONFIRMATIONS", ge=1)
    request_timeout_seconds: float = Field(default=45.0, alias="REQUEST_TIMEOUT_SECONDS", gt=0)
    max_concurrent_checks: int = Field(default=2, alias="MAX_CONCURRENT_CHECKS", ge=1)
    notification_cooldown_seconds: int = Field(
        default=600,
        alias="NOTIFICATION_COOLDOWN_SECONDS",
        ge=0,
    )
    telegram_send_concurrency: int = Field(default=5, alias="TELEGRAM_SEND_CONCURRENCY", ge=1)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    data_retention_days: int = Field(default=90, alias="DATA_RETENTION_DAYS", ge=1)
    healthcheck_port: int = Field(default=8080, alias="HEALTHCHECK_PORT", ge=1, le=65535)
    playwright_enabled: bool = Field(default=True, alias="PLAYWRIGHT_ENABLED")
    user_agent: str = Field(
        default=(
            "DocsQueueMonitor/0.1 (+https://github.com/docsqueuemonitor/DocsQueueMonitor; "
            "monitoring-only; no-booking)"
        ),
        alias="USER_AGENT",
    )

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, int):
            return [value]
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",") if part.strip()]
            return [int(part) for part in parts]
        raise TypeError("ADMIN_TELEGRAM_IDS must be a comma-separated string or list of ints")

    @field_validator("default_language")
    @classmethod
    def _normalize_language(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"uk", "ru", "en"}:
            return "uk"
        return normalized

    @field_validator("log_format")
    @classmethod
    def _normalize_log_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"json", "console"}:
            return "json"
        return normalized

    @property
    def has_bot_token(self) -> bool:
        return bool(self.telegram_bot_token.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
