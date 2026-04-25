"""
AI-HRMS — Application Configuration
All settings are read from environment variables (or .env file).
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "AI-HRMS"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    PORT: int = 8000  # Overridden by Railway / any PaaS via $PORT env var

    # ── URLs ─────────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000"
    ALLOWED_HOSTS: list[str] = ["*"]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ── Database (PostgreSQL) ─────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://hrms_user:hrms_password@localhost:5432/hrms_db"
    DATABASE_SYNC_URL: str = "postgresql://hrms_user:hrms_password@localhost:5432/hrms_db"

    POSTGRES_USER: str = "hrms_user"
    POSTGRES_PASSWORD: str = "hrms_password"
    POSTGRES_DB: str = "hrms_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ── Authentication / JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev_secret_CHANGE_IN_PRODUCTION_min_64_chars_long"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    COOKIE_SECURE: bool = False       # True in production (HTTPS only)
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "lax"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_must_be_long(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    # ── First Super-Admin ─────────────────────────────────────────────────────
    FIRST_SUPERADMIN_EMAIL: str = "admin@hrms.com"
    FIRST_SUPERADMIN_PASSWORD: str = "imran12345"
    FIRST_SUPERADMIN_FIRST_NAME: str = "System"
    FIRST_SUPERADMIN_LAST_NAME: str = "Admin"

    # ── Email (SendGrid) ──────────────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@hrms.local"
    SENDGRID_FROM_NAME: str = "AI-HRMS Notifications"

    # ── SMS (Twilio) ──────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # ── File Storage ──────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    @property
    def MAX_UPLOAD_SIZE_BYTES(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # S3 / S3-Compatible
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = "ai-hrms-uploads"
    AWS_S3_ENDPOINT_URL: str | None = None  # For MinIO or other S3-compatible

    # ── AI / OpenAI ───────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 1024

    # ── Sentry (optional) ─────────────────────────────────────────────────────
    SENTRY_DSN: str | None = None

    # ── Multi-Tenancy ─────────────────────────────────────────────────────────
    DEFAULT_TENANT_SLUG: str = "system"

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 25
    MAX_PAGE_SIZE: int = 100

    # ── Derived convenience flags ─────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @model_validator(mode="after")
    def production_safety_checks(self) -> "Settings":
        if self.is_production:
            if "dev_secret" in self.JWT_SECRET_KEY.lower():
                raise ValueError("JWT_SECRET_KEY must be changed in production")
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be True in production")
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached settings singleton.
    Use this everywhere instead of instantiating Settings directly:

        from app.core.config import settings
    """
    return Settings()


# Singleton instance — import this throughout the app
settings: Settings = get_settings()
