"""Verification = the eligibility result for one appointment.

Persists the `EligibilityResult` shape from app.eligibility. In v1 a row is
created PENDING by the manual source and resolved by the founder; in v2 the same
row is resolved by the 271 parser. Core fields now; `detailed`/`raw_payload`
are JSON columns held for v2 (per-category coverage, frequency limits, the parsed
271) so no schema change is needed to light up detailed reports.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eligibility.types import SourceKind, VerificationStatus

from .base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .appointment import Appointment

_MONEY = Numeric(10, 2)


class Verification(Base, TimestampMixin):
    __tablename__ = "verification"

    id: Mapped[uuid.UUID] = uuid_pk()
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("appointment.id", ondelete="CASCADE"), unique=True, index=True
    )

    source: Mapped[SourceKind] = mapped_column(Enum(SourceKind), nullable=False)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Core fields (populated in v1).
    payer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    annual_max: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    remaining_benefit: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    deductible_total: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    deductible_met: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)

    # v2 holding fields.
    detailed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Who/when resolved (audit).
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    appointment: Mapped[Appointment] = relationship(back_populates="verification")
