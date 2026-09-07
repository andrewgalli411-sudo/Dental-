from __future__ import annotations

import uuid

from app.config import get_settings
from app.models import Batch, Practice
from app.models.enums import BatchStatus
from app.services.intake_service import create_upload_link

_CSV = (
    b"Patient Name,DOB,Insurance,Member ID\n"
    b"Jane Doe,01/15/1990,Delta Dental,ABC123\n"
)


def _approved_batch(auth_client, session_factory) -> str:
    """Drive a batch all the way to READY (approved)."""
    with session_factory() as s:
        practice = Practice(
            name="Bright Smiles", npi="1234567890", tax_id="99-9",
            contact_email="frontdesk@brightsmiles.example",
        )
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
            json={
                "status": "active", "payer": "Delta Dental", "plan": "PPO",
                "annual_max": "1500.00", "remaining_benefit": "1200.00",
                "deductible_total": "50.00", "deductible_met": "50.00",
            },
        )
    auth_client.post(f"/admin/batches/{batch_id}/approve")
    return batch_id


def test_send_delivers_link_without_phi(auth_client, session_factory) -> None:
    batch_id = _approved_batch(auth_client, session_factory)
    resp = auth_client.post(f"/admin/batches/{batch_id}/send")
    assert resp.status_code == 200
    body = resp.json()
    assert "/report/" in body["report_url"]
    assert body["purge_at"]

    # Email captured, link present, NO PHI in the body.
    outbox = auth_client.email_sender.outbox
    assert len(outbox) == 1
    msg = outbox[0]
    assert msg.to == "frontdesk@brightsmiles.example"
    assert "/report/" in msg.body
    assert "Jane" not in msg.body and "Doe" not in msg.body

    with session_factory() as s:
        batch = s.get(Batch, uuid.UUID(batch_id))
        assert batch.status is BatchStatus.DELIVERED
        assert batch.delivered_at is not None
        assert batch.purge_at is not None


def test_report_web_view_and_pdf(auth_client, session_factory) -> None:
    batch_id = _approved_batch(auth_client, session_factory)
    url = auth_client.post(f"/admin/batches/{batch_id}/send").json()["report_url"]
    token = url.rsplit("/report/", 1)[1]

    html = auth_client.get(f"/report/{token}")
    assert html.status_code == 200
    assert "Eligibility Report" in html.text
    assert "Jane Doe" in html.text  # PHI is intended here — behind the token
    assert "Delta Dental" in html.text

    pdf = auth_client.get(f"/report/{token}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


def test_send_requires_approval(auth_client, session_factory) -> None:
    with session_factory() as s:
        practice = Practice(name="X", npi="1", contact_email="a@b.co")
        s.add(practice)
        s.commit()
        link = create_upload_link(s, practice.id, get_settings())
    batch_id = auth_client.post(
        f"/upload/{link.raw_token}", files={"file": ("a.csv", _CSV, "text/csv")}
    ).json()["batch_id"]
    # Not approved yet -> 409.
    assert auth_client.post(f"/admin/batches/{batch_id}/send").status_code == 409


def test_invalid_report_token_404(client) -> None:
    assert client.get("/report/nope").status_code == 404
    assert client.get("/report/nope/pdf").status_code == 404
