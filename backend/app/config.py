from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["gemini", "claude", "mock"] = Field(default="mock")
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    claude_model: str = "claude-haiku-4-5-20251001"

    database_url: str = "postgresql+psycopg://aivizor:aivizor@db:5432/aivizor"

    backend_cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


settings = Settings()
