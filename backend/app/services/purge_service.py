"""PHI retention enforcement.

Deletes PHI for delivered batches whose purge_at has passed: appointment +
verification rows, the raw uploaded file(s), AND the generated report PDF (which
contains patient data). Non-PHI metadata is intentionally KEPT — batch record,
report record (timestamps, who approved), and the audit trail — so we retain
proof of what happened without retaining the health information.

Run on a schedule (EventBridge -> Lambda, or cron): see scripts/purge_phi.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Batch
from app.models.enums import BatchStatus
from app.services import audit
from app.storage import ObjectStore


def purge_expired_phi(
    session: Session,
    store: ObjectStore,
    now: datetime | None = None,
    actor: str = "system",
) -> list[uuid.UUID]:
    """Purge all batches due for it. Returns the ids purged."""
    now = now or datetime.now(UTC)
    due = session.scalars(
        select(Batch)
        .where(Batch.status == BatchStatus.DELIVERED)
        .where(Batch.purge_at.is_not(None))
        .where(Batch.purge_at <= now)
    ).all()

    purged: list[uuid.UUID] = []
    for batch in due:
        _purge_one(session, store, batch)
        purged.append(batch.id)
        audit.record(session, actor, "purge_phi", "batch", str(batch.id))
    return purged


def _purge_one(session: Session, store: ObjectStore, batch: Batch) -> None:
    # Raw uploads (bytes + rows).
    for raw in list(batch.raw_uploads):
        store.delete(raw.s3_key)
        session.delete(raw)

    # Report PDF contains PHI — delete the object, keep the metadata row.
    if batch.report and batch.report.pdf_s3_key:
        store.delete(batch.report.pdf_s3_key)
        batch.report.pdf_s3_key = None

    # Appointments (cascades to their verifications).
    for appt in list(batch.appointments):
        session.delete(appt)

    batch.status = BatchStatus.PURGED
    session.commit()
