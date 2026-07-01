from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Connection settings for the RomM instance, loaded from ROMM_* env vars or .env."""

    model_config = SettingsConfigDict(env_prefix="ROMM_", env_file=".env", extra="ignore")

    base_url: str = "http://localhost:8080"
    api_token: str | None = None
    username: str | None = None
    password: str | None = None
    timeout: float = 30.0

    def auth_headers(self) -> dict[str, str]:
        """Client API Token / OAuth2 bearer header, if a token is configured."""
        if not self.api_token:
            return {}
        token = self.api_token
        if not token.lower().startswith("bearer "):
            token = f"Bearer {token}"
        return {"Authorization": token}


@lru_cache
def get_settings() -> Settings:
    return Settings()
