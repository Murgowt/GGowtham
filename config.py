import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ephemeral SQLite paths that are wiped on every Railway deploy.
_EPHEMERAL_SQLITE_PATHS = {
    "sqlite:///./brain.db",
    "sqlite:////app/brain.db",
}


def _is_railway() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))


def resolve_database_url(url: str) -> str:
    """Normalize DATABASE_URL and use a persistent path on Railway."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if _is_railway() and url in _EPHEMERAL_SQLITE_PATHS:
        return "sqlite:////data/brain.db"

    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_pin: str = "1234"
    secret_key: str = "dev-secret-change-in-production"
    production: bool = False

    mock_integrations: bool = False
    database_url: str = "sqlite:///./brain.db"
    portfolio_cache_minutes: int = 15

    snaptrade_client_id: str = ""
    snaptrade_consumer_key: str = ""
    snaptrade_user_id: str = ""
    snaptrade_user_secret: str = ""

    app_base_url: str = "http://localhost:8000"

    notifications_enabled: bool = False
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""

    cron_secret: str = ""

    spending_cache_minutes: int = 15
    spending_period_start_day: int = 6

    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"

    splitwise_api_key: str = ""

    @model_validator(mode="after")
    def configure_runtime(self) -> "Settings":
        self.database_url = resolve_database_url(self.database_url)

        if (
            self.mock_integrations
            and self.snaptrade_client_id
            and self.snaptrade_consumer_key
        ):
            self.mock_integrations = False
        return self


settings = Settings()
