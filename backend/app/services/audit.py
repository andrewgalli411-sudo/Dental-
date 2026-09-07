"""Append-only audit trail. The row references entities by type+id only — it
never contains PHI (see app.models.audit)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    session: Session, actor: str, action: str, entity_type: str, entity_id: str
) -> None:
    session.add(
        AuditLog(actor=actor, action=action, entity_type=entity_type, entity_id=str(entity_id))
    )
    session.commit()
