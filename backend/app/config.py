"""Environment-driven config. No secrets in code — everything comes from env
(AWS Secrets Manager injects them in deployed environments)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "local"  # local | staging | prod
    log_level: str = "INFO"

    # Postgres. In deployed environments this is an RDS instance with KMS at-rest.
    database_url: str = "postgresql+psycopg://verifi:verifi@localhost:5432/verifi"

    # AWS (used from Phase 2 onward). BAA-covered services only.
    aws_region: str = "us-east-1"
    s3_bucket_uploads: str = ""
    s3_bucket_reports: str = ""

    # Token link lifetimes.
    upload_token_ttl_hours: int = 36     # covers a 5pm cutoff -> next morning
    report_token_ttl_days: int = 7       # matches PHI retention window

    # PHI retention.
    phi_retention_days: int = 7

    # Admin session. MUST be overridden in every deployed env (from Secrets
    # Manager). The default exists only so local dev runs.
    session_secret: str = "dev-only-insecure-change-me"
    session_ttl_hours: int = 12
    # Cookie Secure flag off locally (http); on everywhere else.
    cookie_secure: bool = False

    # Public base URL, used to build secure links in emails.
    public_base_url: str = "http://localhost:8000"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
