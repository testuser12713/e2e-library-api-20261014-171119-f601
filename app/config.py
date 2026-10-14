"""Application configuration read lazily from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    ``LIBRARY_API_KEY`` is optional: when it is unset the app still starts and
    every write endpoint answers 401 (implemented by the API-key ticket).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    library_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance, reading the environment on first use."""
    return Settings()
