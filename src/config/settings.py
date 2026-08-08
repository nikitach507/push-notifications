"""Application settings and configuration."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Bot Configuration
    bot_token: str = Field(..., description="Telegram Bot API token")

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./bot_database.db",
        description="Database connection URL",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Web Server Configuration (for Render.com free tier)
    port: int = Field(
        default=10000,
        description="Port for web server (used for health checks on Render)",
        validation_alias="PORT",  # Render sets PORT env variable
    )


# Singleton instance
settings = Settings()
