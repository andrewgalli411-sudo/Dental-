"""Scheduled PHI purge. Run daily (EventBridge -> Lambda, or cron):

    python -m scripts.purge_phi

Deletes PHI for delivered batches past their retention window; keeps non-PHI
metadata and the audit trail.
"""

from __future__ import annotations

from app.db import SessionLocal
from app.services.purge_service import purge_expired_phi
from app.storage import get_object_store


def main() -> int:
    with SessionLocal() as session:
        purged = purge_expired_phi(session, get_object_store())
    print(f"purged {len(purged)} batch(es)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
