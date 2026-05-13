"""Application configuration via pydantic-settings.

Uses environment variables with a .env file fallback so the app works
with both Docker Compose and bare-metal local dev.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the FPA Copilot backend."""

    database_url: str = "postgresql+asyncpg://fpa:fpa@localhost:5432/fpa_copilot"
    anthropic_api_key: str = ""
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
