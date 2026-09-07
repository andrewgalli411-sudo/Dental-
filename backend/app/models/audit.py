"""Immutable audit log for every PHI access/mutation.

HIPAA requires an audit trail. Critically, **the log row itself holds no PHI** —
it references entities by type + id only, never patient names/DOBs/etc. Append-only
by convention (no update/delete paths in the app)."""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor: Mapped[str] = mapped_column(String(255), nullable=False)  # admin user or "system"
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
