from __future__ import annotations

from app.config import get_settings
from app.models import Appointment, Batch, Practice
from app.models.enums import BatchStatus
from app.services.intake_service import create_upload_link


def _make_practice(session) -> Practice:
    p = Practice(name="Test Dental", npi="1234567890", contact_email="x@y.com")
    session.add(p)
    session.commit()
    return p


_CSV = (
    b"Patient Name,DOB,Insurance,Member ID\n"
    b"Jane Doe,01/15/1990,Delta Dental,ABC123\n"
    b"John Roe,03/02/1978,,\n"  # missing payer + id -> needs review
)


def test_upload_end_to_end(client, session_factory) -> None:
    with session_factory() as s:
        practice = _make_practice(s)
        link = create_upload_link(s, practice.id, get_settings())

    resp = client.post(
        f"/upload/{link.raw_token}",
        files={"file": ("appts.csv", _CSV, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rows_parsed"] == 2
    assert body["rows_needing_review"] == 1
    # Response must carry no PHI.
    assert "Jane" not in resp.text and "Doe" not in resp.text

    with session_factory() as s:
        batch = s.get(Batch, __import__("uuid").UUID(body["batch_id"]))
        assert batch.status is BatchStatus.REVIEW
        appts = s.query(Appointment).filter_by(batch_id=batch.id).all()
        assert len(appts) == 2
        jane = next(a for a in appts if a.patient_name == "Jane Doe")
        assert jane.has_required_identity is True
        assert jane.needs_review is False
        john = next(a for a in appts if a.patient_name == "John Roe")
        assert john.payer_name is None
        assert john.needs_review is True


def test_token_is_single_use(client, session_factory) -> None:
    with session_factory() as s:
        practice = _make_practice(s)
        link = create_upload_link(s, practice.id, get_settings())

    first = client.post(
        f"/upload/{link.raw_token}", files={"file": ("a.csv", _CSV, "text/csv")}
    )
    assert first.status_code == 200
    second = client.post(
        f"/upload/{link.raw_token}", files={"file": ("a.csv", _CSV, "text/csv")}
    )
    assert second.status_code == 400


def test_invalid_token_rejected(client) -> None:
    resp = client.post(
        "/upload/not-a-real-token", files={"file": ("a.csv", _CSV, "text/csv")}
    )
    assert resp.status_code == 400


def test_empty_file_rejected(client, session_factory) -> None:
    with session_factory() as s:
        practice = _make_practice(s)
        link = create_upload_link(s, practice.id, get_settings())
    resp = client.post(
        f"/upload/{link.raw_token}", files={"file": ("a.csv", b"", "text/csv")}
    )
    assert resp.status_code == 400
