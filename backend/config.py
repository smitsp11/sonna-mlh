
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Any

# Get project root directory (parent of backend/)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Also try loading .env manually with python-dotenv as fallback
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_FILE)
except ImportError:
    pass  # python-dotenv not installed, rely on pydantic-settings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Sonna Backend"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # API
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Gemini (LLM) - Required for MVP
    GEMINI_API_KEY: str | None = None

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Database (PostgreSQL / Supabase) - Required for conversation context
    # This default is overridden by DATABASE_URL in .env file
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/sonna"

    class Config:
        case_sensitive = True
        env_file = str(ENV_FILE)  # Use absolute path to project root .env
        env_file_encoding = "utf-8"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        """Parse CORS origins from environment variables."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


# Initialize global settings instance
settings = Settings()

# Logging configuration
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

