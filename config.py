from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_pin: str = "1234"
    secret_key: str = "dev-secret-change-in-production"
    production: bool = False

    mock_integrations: bool = True
    database_url: str = "sqlite:///./brain.db"
    portfolio_cache_minutes: int = 15

    snaptrade_client_id: str = ""
    snaptrade_consumer_key: str = ""
    snaptrade_user_id: str = ""
    snaptrade_user_secret: str = ""

    app_base_url: str = "http://localhost:8000"


settings = Settings()
