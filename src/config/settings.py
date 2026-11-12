"""Application settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agent-observability-service"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./observability.db"
    valid_api_keys_raw: str = Field(default="", alias="VALID_API_KEYS")
    jwt_secret: str = Field(..., description="JWT signing secret (required, no weak default)")
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4"

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)

    @property
    def valid_api_keys(self) -> list[str]:
        """Comma-separated VALID_API_KEYS env var, as a list."""
        return [key.strip() for key in self.valid_api_keys_raw.split(",") if key.strip()]


settings = Settings()
