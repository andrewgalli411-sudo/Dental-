"""Verification workflow: submit pending verifications through the eligibility
source, resolve them (the human, in v1), and approve a batch (human sign-off).

Everything eligibility-related goes through app.eligibility so the v2 EDI source
swaps in unchanged.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.eligibility import EligibilityRequest, EligibilityResult, ManualEligibilitySource
from app.eligibility.types import SourceKind, VerificationStatus
from app.models import Appointment, Batch, Practice, Report, Verification
from app.models.enums import BatchStatus
from app.persistence import SqlVerificationStore
from app.services import audit


class WorkflowError(Exception):
    """Invalid workflow transition (maps to 4xx)."""


@dataclass(slots=True)
class StartResult:
    submitted: int
    skipped_missing_identity: int


def start_verification(session: Session, batch_id: uuid.UUID, actor: str) -> StartResult:
    batch = _get_batch(session, batch_id)
    if batch.status not in (BatchStatus.REVIEW, BatchStatus.VERIFYING):
        raise WorkflowError(f"cannot start verification from status {batch.status}")
    practice = session.get(Practice, batch.practice_id)
    if practice is None:
        raise WorkflowError("practice not found")

    store = SqlVerificationStore(session, actor=actor, source=SourceKind.MANUAL)
    source = ManualEligibilitySource(store)

    appts = session.scalars(
        select(Appointment).where(Appointment.batch_id == batch_id)
    ).all()

    submitted = skipped = 0
    for appt in appts:
        if appt.verification is not None:
            continue  # already submitted
        if not appt.has_required_identity:
            skipped += 1
            continue
        assert appt.patient_name and appt.dob and appt.payer_name  # guarded above
        req = EligibilityRequest(
            patient_name=appt.patient_name,
            dob=appt.dob,
            payer_name=appt.payer_name,
            provider_npi=practice.npi,
            provider_tax_id=practice.tax_id or "",
            subscriber_id=appt.subscriber_id,
            subscriber_name=appt.subscriber_name,
            subscriber_dob=appt.subscriber_dob,
            payer_id=appt.payer_id,
            group_number=appt.group_number,
            correlation_id=str(appt.id),
        )
        source.submit(req)
        submitted += 1

    batch.status = BatchStatus.VERIFYING
    session.commit()
    audit.record(session, actor, "start_verification", "batch", str(batch_id))
    return StartResult(submitted=submitted, skipped_missing_identity=skipped)


def resolve_verification(
    session: Session,
    verification_id: uuid.UUID,
    actor: str,
    *,
    status: VerificationStatus,
    payer: str | None = None,
    plan: str | None = None,
    effective_date: date | None = None,
    annual_max: Decimal | None = None,
    remaining_benefit: Decimal | None = None,
    deductible_total: Decimal | None = None,
    deductible_met: Decimal | None = None,
    note: str | None = None,
) -> None:
    result = EligibilityResult(
        status=status,
        source=SourceKind.MANUAL,
        payer=payer,
        plan=plan,
        effective_date=effective_date,
        annual_max=annual_max,
        remaining_benefit=remaining_benefit,
        deductible_total=deductible_total,
        deductible_met=deductible_met,
        note=note,
    )
    store = SqlVerificationStore(session, actor=actor, source=SourceKind.MANUAL)
    store.resolve(str(verification_id), result)
    audit.record(session, actor, "resolve_verification", "verification", str(verification_id))


def approve_batch(session: Session, batch_id: uuid.UUID, actor: str) -> uuid.UUID:
    """Human sign-off. Requires every submitted verification resolved (no PENDING).
    Creates the Report record and moves the batch to READY."""
    batch = _get_batch(session, batch_id)
    if batch.status != BatchStatus.VERIFYING:
        raise WorkflowError(f"cannot approve from status {batch.status}")

    pending = session.scalars(
        select(Verification)
        .join(Appointment, Verification.appointment_id == Appointment.id)
        .where(Appointment.batch_id == batch_id)
        .where(Verification.status == VerificationStatus.PENDING)
    ).first()
    if pending is not None:
        raise WorkflowError("cannot approve: unresolved verifications remain")

    if batch.report is not None:
        raise WorkflowError("batch already has a report")

    now = datetime.now(UTC)
    report = Report(
        batch_id=batch_id,
        generated_at=now,
        approved_by=actor,
        approved_at=now,
    )
    session.add(report)
    batch.status = BatchStatus.READY
    batch.report_ready_at = now
    session.commit()
    audit.record(session, actor, "approve_batch", "batch", str(batch_id))
    return report.id


def _get_batch(session: Session, batch_id: uuid.UUID) -> Batch:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise WorkflowError("batch not found")
    return batch
