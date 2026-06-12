"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API, UI, local storage, and model provider."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="P2GL_",
        extra="ignore",
    )

    env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    data_dir: Path = Path("data")
    sqlite_path: Path = Path("data/metadata.sqlite3")

    model_provider: str | None = None
    model_name: str | None = None
    model_base_url: str | None = None
    embedding_model: str | None = None
    api_key: str | None = Field(default=None, repr=False)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for dependency injection and app startup."""

    return Settings()
