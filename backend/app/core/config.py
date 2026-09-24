"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the API.

    Values are read from real environment variables first, then from the
    `.env` file located in the backend working directory.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    PROJECT_NAME: str = "FlipStore API"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/flipystore"

    # Auth (JWT implemented in Phase 2)
    SECRET_KEY: str = "change-me-generate-a-long-random-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # CORS (NoDecode: accept plain comma-separated values instead of JSON)
    # Deployed origins included so a fresh Vercel backend build (which has no
    # .env) accepts the live storefront without dashboard configuration.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4173",  # `vite preview`
        "https://flipstore-one.vercel.app",  # production storefront
    ]

    # Payments (Phase 7)
    PAYMENT_PROVIDER: str = "mock"  # mock gateway now; Stripe driver lands later
    STRIPE_SECRET_KEY: str = ""

    # Email (Phase 7) — "" auto-selects: memory in tests, file in development
    EMAIL_BACKEND: str = ""  # memory | file | console | smtp
    EMAIL_FROM: str = "FlipStore <no-reply@flipstore.example>"
    EMAIL_FILE_PATH: str = "emails.log"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    # Storefront base URL (used for links inside emails)
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept a comma-separated string from the environment."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (env is read once per process)."""
    return Settings()


settings = get_settings()
