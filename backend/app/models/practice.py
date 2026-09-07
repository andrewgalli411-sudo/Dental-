"""Practice (client). Provider identity lives here — collected once at onboarding,
not on every appointment list."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .batch import Batch


class Practice(Base, TimestampMixin):
    __tablename__ = "practice"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    npi: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)

    # BAA must be signed before any PHI is accepted for this practice.
    baa_signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    batches: Mapped[list[Batch]] = relationship(back_populates="practice")

    @property
    def baa_active(self) -> bool:
        return self.baa_signed_at is not None
