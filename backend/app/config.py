from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: Literal["gemini", "claude", "mock"] = Field(default="mock")
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    claude_model: str = "claude-haiku-4-5-20251001"

    database_url: str = "postgresql+psycopg://aivizor:aivizor@db:5432/aivizor"

    backend_cors_origins: str = "http://localhost:3000"

    # --- Auth (Fase 7.2) ---
    # JWT firmado HS256 y servido en cookie httpOnly. El secreto DEBE cambiarse en
    # cualquier despliegue real; el default solo sirve para desarrollo local.
    jwt_secret: str = "dev-insecure-secret-change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 1 día

    # Cookie de sesión. `secure=True` solo bajo HTTPS; en localhost se deja False.
    cookie_name: str = "access_token"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Admin inicial: si ambos están definidos, se siembra al arrancar (idempotente).
    admin_email: str = ""
    admin_password: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


settings = Settings()
