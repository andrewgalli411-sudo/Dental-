"""Intake workflow: mint upload links, ingest uploads into staged appointments.

Link-minting is an internal (founder) action — it is NOT exposed as an
unauthenticated route; Phase 3 puts it behind admin auth. The upload endpoint
itself is token-scoped (the account-less client surface).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.intake import normalize
from app.models import AccessToken, Appointment, Batch, RawUpload
from app.models.enums import BatchStatus, TokenScope
from app.security import generate_token, hash_token
from app.storage import ObjectStore


class IntakeError(Exception):
    """Raised for invalid/expired tokens or bad uploads (maps to 4xx)."""


@dataclass(slots=True)
class UploadLink:
    raw_token: str
    expires_at: datetime


@dataclass(slots=True)
class IngestResult:
    batch_id: uuid.UUID
    rows_parsed: int
    rows_needing_review: int


def create_upload_link(
    session: Session, practice_id: uuid.UUID, settings: Settings
) -> UploadLink:
    raw, token_hash = generate_token()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.upload_token_ttl_hours)
    session.add(
        AccessToken(
            token_hash=token_hash,
            scope=TokenScope.UPLOAD,
            practice_id=practice_id,
            expires_at=expires_at,
        )
    )
    session.commit()
    return UploadLink(raw_token=raw, expires_at=expires_at)


def _consume_upload_token(session: Session, raw_token: str) -> AccessToken:
    token = session.scalar(
        select(AccessToken).where(AccessToken.token_hash == hash_token(raw_token))
    )
    if token is None or token.scope != TokenScope.UPLOAD:
        raise IntakeError("invalid upload token")
    if not token.is_usable(datetime.now(UTC)):
        raise IntakeError("upload token expired or already used")
    return token


def ingest_upload(
    session: Session,
    store: ObjectStore,
    raw_token: str,
    filename: str,
    content_type: str,
    data: bytes,
    settings: Settings,
) -> IngestResult:
    token = _consume_upload_token(session, raw_token)

    batch = Batch(
        practice_id=token.practice_id,
        status=BatchStatus.PARSING,
        submitted_at=datetime.now(UTC),
    )
    session.add(batch)
    session.flush()  # assign batch.id

    key = f"uploads/{batch.id}/{filename}"
    store.put(key, data, content_type)
    session.add(
        RawUpload(
            batch_id=batch.id,
            s3_key=key,
            original_filename=filename,
            content_type=content_type,
        )
    )

    rows = normalize(data, filename)
    needing_review = 0
    for r in rows:
        appt = Appointment(
            batch_id=batch.id,
            appt_time=r.appt_time,
            patient_name=r.patient_name,
            dob=r.dob,
            payer_name=r.payer_name,
            subscriber_id=r.subscriber_id,
            subscriber_name=r.subscriber_name,
            subscriber_dob=r.subscriber_dob,
            payer_id=r.payer_id,
            group_number=r.group_number,
            parse_confidence=r.confidence,
            needs_review=r.needs_review,
        )
        needing_review += int(r.needs_review)
        session.add(appt)

    batch.status = BatchStatus.REVIEW
    token.used_at = datetime.now(UTC)
    session.commit()

    return IngestResult(
        batch_id=batch.id,
        rows_parsed=len(rows),
        rows_needing_review=needing_review,
    )
