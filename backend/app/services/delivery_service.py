"""Deliver an approved report: render PDF, mint a report-view link, email it
(link only), move the batch to DELIVERED, and schedule PHI purge."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AccessToken, Practice
from app.models.enums import BatchStatus, TokenScope
from app.notifications import EmailSender
from app.reporting import build_report_data, render_pdf
from app.security import generate_token
from app.services import audit
from app.services.verification_service import WorkflowError, _get_batch
from app.storage import ObjectStore


@dataclass(slots=True)
class DeliveryResult:
    report_url: str
    purge_at: datetime


def _report_pdf_key(batch_id: uuid.UUID) -> str:
    return f"reports/{batch_id}/report.pdf"


def send_report(
    session: Session,
    batch_id: uuid.UUID,
    store: ObjectStore,
    email_sender: EmailSender,
    settings: Settings,
    actor: str,
) -> DeliveryResult:
    batch = _get_batch(session, batch_id)
    if batch.status != BatchStatus.READY or batch.report is None:
        raise WorkflowError("batch must be approved (READY) before sending")
    practice = session.get(Practice, batch.practice_id)
    if practice is None:
        raise WorkflowError("practice not found")

    # Render + store the PDF.
    data = build_report_data(session, batch)
    key = _report_pdf_key(batch_id)
    store.put(key, render_pdf(data), "application/pdf")
    batch.report.pdf_s3_key = key

    # Mint a multi-use, expiring report-view link (raw token only in the URL).
    raw, token_hash = generate_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.report_token_ttl_days)
    session.add(
        AccessToken(
            token_hash=token_hash,
            scope=TokenScope.REPORT_VIEW,
            practice_id=practice.id,
            batch_id=batch_id,
            expires_at=expires_at,
        )
    )

    report_url = f"{settings.public_base_url.rstrip('/')}/report/{raw}"
    email_sender.send(
        to=practice.contact_email,
        subject="Your patient eligibility report is ready",
        body=(
            "Your eligibility report for the upcoming schedule is ready.\n\n"
            f"View it securely here (link expires in {settings.report_token_ttl_days} days):\n"
            f"{report_url}\n\n"
            "For your patients' privacy, no health information is included in this email."
        ),
    )

    now = datetime.now(UTC)
    batch.status = BatchStatus.DELIVERED
    batch.delivered_at = now
    batch.purge_at = now + timedelta(days=settings.phi_retention_days)
    session.commit()
    audit.record(session, actor, "send_report", "batch", str(batch_id))

    return DeliveryResult(report_url=report_url, purge_at=batch.purge_at)
