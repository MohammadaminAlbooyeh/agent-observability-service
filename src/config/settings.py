"""Application settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agent-observability-service"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./observability.db"
    admin_api_keys_raw: str = Field(default="", alias="ADMIN_API_KEYS")
    jwt_secret: str = Field(..., description="JWT signing secret (required, no weak default)")
    jwt_expire_minutes: int = 60
    cookie_secure: bool = False
    rate_limit_calls: int = 100
    rate_limit_period_seconds: float = 60.0
    alert_eval_interval_seconds: int = 60
    alert_cooldown_seconds: int = 900
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4"

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True, extra="ignore")

    @property
    def admin_api_keys(self) -> list[str]:
        """Comma-separated ADMIN_API_KEYS env var, as a list."""
        return [key.strip() for key in self.admin_api_keys_raw.split(",") if key.strip()]


settings = Settings()
