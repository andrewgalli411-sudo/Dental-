from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.models import Appointment, Batch, Practice, RawUpload, Verification
from app.models.enums import BatchStatus
from app.services.intake_service import create_upload_link
from app.services.purge_service import purge_expired_phi

_CSV = b"Patient Name,DOB,Insurance,Member ID\nJane Doe,01/15/1990,Delta Dental,ABC123\n"


def _deliver_batch(auth_client, session_factory) -> str:
    with session_factory() as s:
        practice = Practice(name="P", npi="1", tax_id="9", contact_email="a@b.co")
        s.add(practice)
        s.commit()
        link = create_upload_link(s, practice.id, get_settings())
    batch_id = auth_client.post(
        f"/upload/{link.raw_token}", files={"file": ("a.csv", _CSV, "text/csv")}
    ).json()["batch_id"]
    auth_client.post(f"/admin/batches/{batch_id}/start-verification")
    detail = auth_client.get(f"/admin/batches/{batch_id}").json()
    for appt in detail["appointments"]:
        auth_client.post(
            f"/admin/verifications/{appt['verification_id']}/resolve",
            json={"status": "active", "payer": "Delta Dental"},
        )
    auth_client.post(f"/admin/batches/{batch_id}/approve")
    auth_client.post(f"/admin/batches/{batch_id}/send")
    return batch_id


def test_purge_removes_phi_keeps_metadata(auth_client, session_factory) -> None:
    batch_id = _deliver_batch(auth_client, session_factory)
    bid = uuid.UUID(batch_id)

    # Record object keys before purge; confirm the PDF + raw exist.
    with session_factory() as s:
        batch = s.get(Batch, bid)
        raw_keys = [r.s3_key for r in batch.raw_uploads]
        pdf_key = batch.report.pdf_s3_key
    store = auth_client.object_store
    assert pdf_key and store.get(pdf_key)
    for k in raw_keys:
        assert store.get(k)

    # Force retention to have elapsed.
    with session_factory() as s:
        s.get(Batch, bid).purge_at = datetime.now(UTC) - timedelta(days=1)
        s.commit()

    with session_factory() as s:
        purged = purge_expired_phi(s, store, now=datetime.now(UTC))
    assert purged == [bid]

    with session_factory() as s:
        batch = s.get(Batch, bid)
        # PHI gone.
        assert s.query(Appointment).filter_by(batch_id=bid).count() == 0
        remaining_verifs = (
            s.query(Verification).join(Appointment).filter(Appointment.batch_id == bid).count()
        )
        assert remaining_verifs == 0
        assert s.query(RawUpload).filter_by(batch_id=bid).count() == 0
        # Metadata kept.
        assert batch.status is BatchStatus.PURGED
        assert batch.report is not None
        assert batch.report.pdf_s3_key is None
        assert batch.report.approved_at is not None

    # Object bytes gone too (PDF contained PHI).
    import pytest

    for k in [pdf_key, *raw_keys]:
        with pytest.raises(FileNotFoundError):
            store.get(k)


def test_purge_ignores_batches_before_retention(auth_client, session_factory) -> None:
    batch_id = _deliver_batch(auth_client, session_factory)
    # purge_at is ~7 days out; nothing should purge now.
    with session_factory() as s:
        purged = purge_expired_phi(s, auth_client.object_store, now=datetime.now(UTC))
    assert uuid.UUID(batch_id) not in purged
    with session_factory() as s:
        assert s.get(Batch, uuid.UUID(batch_id)).status is BatchStatus.DELIVERED
