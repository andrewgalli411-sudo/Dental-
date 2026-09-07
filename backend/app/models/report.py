"""Report = the approved, deliverable artifact for a batch.

A report row exists only after the founder approves — the human sign-off gate.
The web view token is stored hashed (same rule as AccessToken); the PDF lives in
S3 (SSE-KMS)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .batch import Batch


class Report(Base, TimestampMixin):
    __tablename__ = "report"

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batch.id", ondelete="CASCADE"), unique=True, index=True
    )

    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    pdf_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    batch: Mapped[Batch] = relationship(back_populates="report")
