"""Appointment = one row from the normalized list. **This is PHI.**

Purged 7 days after delivery. `parse_confidence` / `needs_review` drive the admin
review gate: low-confidence or incomplete rows are flagged before any pull.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .batch import Batch
    from .verification import Verification


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointment"

    id: Mapped[uuid.UUID] = uuid_pk()
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batch.id", ondelete="CASCADE"), index=True
    )

    appt_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Required minimum (v1 contract).
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    payer_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional identifiers (missing -> chase-work; needed for EDI 270 in v2).
    subscriber_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subscriber_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscriber_dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    payer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    group_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Normalization metadata for the review gate.
    parse_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    batch: Mapped[Batch] = relationship(back_populates="appointments")
    verification: Mapped[Verification | None] = relationship(
        back_populates="appointment",
        uselist=False,
        cascade="all, delete-orphan",
    )
