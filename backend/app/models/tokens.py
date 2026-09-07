"""Access tokens for the account-less client surface.

Practices never log in. They get single-purpose, short-expiry tokenized links:
one to upload a day's list, one to view/download a report. We store only a
**hash** of the token — the raw value lives only in the emailed URL, so a DB
read never yields a working link.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk
from .enums import TokenScope


class AccessToken(Base, TimestampMixin):
    __tablename__ = "access_token"

    id: Mapped[uuid.UUID] = uuid_pk()
    # SHA-256 hex of the raw token. Never store the raw token.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scope: Mapped[TokenScope] = mapped_column(Enum(TokenScope), nullable=False)

    practice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice.id", ondelete="CASCADE"), index=True
    )
    # Upload tokens are minted before a batch exists; report tokens bind to one.
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("batch.id", ondelete="CASCADE"), nullable=True, index=True
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def is_usable(self, now: datetime) -> bool:
        # Some DB backends (e.g. SQLite) return naive datetimes even for
        # timezone-aware columns. Treat a naive stored value as UTC so the
        # comparison never mixes aware/naive.
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.used_at is None and now < expires
