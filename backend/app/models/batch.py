"""A batch = one practice's appointment list for one day, tracked through the
workflow state machine, plus the raw uploaded file(s)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk
from .enums import BatchStatus

if TYPE_CHECKING:
    from .appointment import Appointment
    from .practice import Practice
    from .report import Report


class Batch(Base, TimestampMixin):
    __tablename__ = "batch"

    id: Mapped[uuid.UUID] = uuid_pk()
    practice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("practice.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus), default=BatchStatus.UPLOADED, nullable=False, index=True
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Set to delivered_at + retention window (7d). A scheduled job purges PHI
    # for batches whose purge_at has passed.
    purge_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    practice: Mapped[Practice] = relationship(back_populates="batches")
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    raw_uploads: Mapped[list[RawUpload]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    report: Mapped[Report | None] = relationship(back_populates="batch", uselist=False)


class RawUpload(Base, TimestampMixin):
    """Pointer to the original uploaded file in S3 (SSE-KMS). Bytes never live
    in the DB."""

    __tablename__ = "raw_upload"

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batch.id", ondelete="CASCADE"), index=True
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(127), nullable=False)

    batch: Mapped[Batch] = relationship(back_populates="raw_uploads")
