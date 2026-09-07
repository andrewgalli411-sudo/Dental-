from __future__ import annotations

import uuid

from app.config import get_settings
from app.models import Batch, Practice
from app.models.enums import BatchStatus
from app.services.intake_service import create_upload_link

_CSV = (
    b"Patient Name,DOB,Insurance,Member ID\n"
    b"Jane Doe,01/15/1990,Delta Dental,ABC123\n"
    b"John Roe,03/02/1978,,\n"  # missing payer -> needs review, can't verify yet
)


def _seed_batch(client, session_factory) -> str:
    with session_factory() as s:
        practice = Practice(
            name="Test Dental", npi="1234567890", tax_id="99-9", contact_email="x@y.com"
        )
        s.add(practice)
        s.commit()
        link = create_upload_link(s, practice.id, get_settings())
    resp = client.post(f"/upload/{link.raw_token}", files={"file": ("a.csv", _CSV, "text/csv")})
    assert resp.status_code == 200
    return resp.json()["batch_id"]


def test_full_verification_flow(auth_client, session_factory) -> None:
    batch_id = _seed_batch(auth_client, session_factory)

    detail = auth_client.get(f"/admin/batches/{batch_id}").json()
    assert detail["status"] == "review"
    incomplete = next(a for a in detail["appointments"] if not a["has_required_identity"])

    # Correct the incomplete row by supplying the payer.
    patch = auth_client.patch(
        f"/admin/appointments/{incomplete['id']}", json={"payer_name": "Cigna"}
    )
    assert patch.status_code == 200 and patch.json()["needs_review"] is False

    started = auth_client.post(f"/admin/batches/{batch_id}/start-verification").json()
    assert started["submitted"] == 2
    assert started["skipped_missing_identity"] == 0

    detail = auth_client.get(f"/admin/batches/{batch_id}").json()
    assert detail["status"] == "verifying"

    # Resolve every verification as active.
    for appt in detail["appointments"]:
        r = auth_client.post(
            f"/admin/verifications/{appt['verification_id']}/resolve",
            json={
                "status": "active",
                "payer": appt["payer_name"],
                "plan": "PPO",
                "annual_max": "1500.00",
                "remaining_benefit": "1200.00",
                "deductible_total": "50.00",
                "deductible_met": "50.00",
            },
        )
        assert r.status_code == 200

    approve = auth_client.post(f"/admin/batches/{batch_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["report_id"]

    with session_factory() as s:
        batch = s.get(Batch, uuid.UUID(batch_id))
        assert batch.status is BatchStatus.READY
        assert batch.report is not None
        assert batch.report_ready_at is not None


def test_approve_blocked_while_pending(auth_client, session_factory) -> None:
    batch_id = _seed_batch(auth_client, session_factory)
    # Fix the incomplete row so both get submitted.
    detail = auth_client.get(f"/admin/batches/{batch_id}").json()
    incomplete = next(a for a in detail["appointments"] if not a["has_required_identity"])
    auth_client.patch(f"/admin/appointments/{incomplete['id']}", json={"payer_name": "Cigna"})
    auth_client.post(f"/admin/batches/{batch_id}/start-verification")

    # Approve without resolving -> 409.
    resp = auth_client.post(f"/admin/batches/{batch_id}/approve")
    assert resp.status_code == 409


def test_start_verification_skips_missing_identity(auth_client, session_factory) -> None:
    batch_id = _seed_batch(auth_client, session_factory)
    # Do NOT fix the incomplete row; it must be skipped, not submitted.
    started = auth_client.post(f"/admin/batches/{batch_id}/start-verification").json()
    assert started["submitted"] == 1
    assert started["skipped_missing_identity"] == 1
