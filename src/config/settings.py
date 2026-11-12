"""Application settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "agent-observability-service"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./observability.db"
    valid_api_keys: list[str] = []
    jwt_secret: str = Field(..., description="JWT signing secret (required, no weak default)")
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
