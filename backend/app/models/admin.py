"""Admin user (the founder). Single user in v1, but modeled as a table so adding
staff later needs no migration rework. This login guards ALL PHI, so it carries a
password hash AND a TOTP secret — MFA is mandatory, not optional."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_user"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # argon2 hash. Never a plaintext or reversible form.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # TOTP shared secret (base32). Sensitive; encrypted at rest via DB KMS.
    totp_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
