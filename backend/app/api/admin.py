"""Admin API — the founder's PHI-handling surface. Every route except /login is
behind require_admin (session cookie + the account was MFA-verified at login).

This is where PHI is read and written, so it is the one place we accept the cost
of returning identifiers in responses — only to an authenticated admin.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.eligibility.types import VerificationStatus
from app.models import AdminUser, Appointment, Batch, Practice
from app.models.enums import BatchStatus
from app.notifications import EmailSender, get_email_sender
from app.security.auth import (
    SESSION_COOKIE,
    issue_session,
    require_admin,
    verify_password,
    verify_totp,
)
from app.security.ratelimit import TooManyAttempts, login_limiter
from app.services import delivery_service, verification_service
from app.services.verification_service import WorkflowError
from app.storage import ObjectStore, get_object_store

router = APIRouter(prefix="/admin", tags=["admin"])

_ACTIVE_STATUSES = (BatchStatus.REVIEW, BatchStatus.VERIFYING, BatchStatus.READY)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp: str


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    key = body.email.lower()
    try:
        login_limiter.check(key)
    except TooManyAttempts as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many attempts — try again later",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    admin = session.scalar(select(AdminUser).where(AdminUser.email == body.email))
    # Same generic error whether the email is unknown or the secret is wrong.
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if (
        admin is None
        or not admin.is_active
        or not verify_password(admin.password_hash, body.password)
        or not verify_totp(admin.totp_secret, body.totp)
    ):
        login_limiter.record_failure(key)
        raise invalid
    login_limiter.record_success(key)

    response.set_cookie(
        key=SESSION_COOKIE,
        value=issue_session(admin.id, settings),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_hours * 3600,
    )
    return {"status": "ok"}


@router.post("/logout")
def logout(response: Response, _: AdminUser = Depends(require_admin)) -> dict[str, str]:
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


class BatchSummary(BaseModel):
    id: str
    practice_name: str
    status: str
    appointments: int
    needing_review: int


@router.get("/batches", response_model=list[BatchSummary])
def list_batches(
    session: Session = Depends(get_session),
    _: AdminUser = Depends(require_admin),
) -> list[BatchSummary]:
    batches = session.scalars(
        select(Batch).where(Batch.status.in_(_ACTIVE_STATUSES)).order_by(Batch.created_at)
    ).all()
    out: list[BatchSummary] = []
    for b in batches:
        practice = session.get(Practice, b.practice_id)
        appts = b.appointments
        out.append(
            BatchSummary(
                id=str(b.id),
                practice_name=practice.name if practice else "?",
                status=b.status.value,
                appointments=len(appts),
                needing_review=sum(1 for a in appts if a.needs_review),
            )
        )
    return out


class AppointmentOut(BaseModel):
    id: str
    appt_time: str | None
    patient_name: str | None
    dob: date | None
    payer_name: str | None
    subscriber_id: str | None
    payer_id: str | None
    needs_review: bool
    has_required_identity: bool
    verification_status: str | None
    verification_id: str | None


class BatchDetail(BaseModel):
    id: str
    status: str
    appointments: list[AppointmentOut]


@router.get("/batches/{batch_id}", response_model=BatchDetail)
def get_batch(
    batch_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(require_admin),
) -> BatchDetail:
    batch = session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    rows = [
        AppointmentOut(
            id=str(a.id),
            appt_time=a.appt_time.isoformat() if a.appt_time else None,
            patient_name=a.patient_name,
            dob=a.dob,
            payer_name=a.payer_name,
            subscriber_id=a.subscriber_id,
            payer_id=a.payer_id,
            needs_review=a.needs_review,
            has_required_identity=a.has_required_identity,
            verification_status=a.verification.status.value if a.verification else None,
            verification_id=str(a.verification.id) if a.verification else None,
        )
        for a in batch.appointments
    ]
    return BatchDetail(id=str(batch.id), status=batch.status.value, appointments=rows)


class AppointmentPatch(BaseModel):
    patient_name: str | None = None
    dob: date | None = None
    payer_name: str | None = None
    subscriber_id: str | None = None
    subscriber_name: str | None = None
    subscriber_dob: date | None = None
    payer_id: str | None = None
    group_number: str | None = None


@router.patch("/appointments/{appointment_id}")
def patch_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentPatch,
    session: Session = Depends(get_session),
    _: AdminUser = Depends(require_admin),
) -> dict[str, bool]:
    appt = session.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(appt, field_name, value)
    # Corrected rows that now have the required identity are no longer flagged.
    appt.needs_review = not appt.has_required_identity
    session.commit()
    return {"needs_review": appt.needs_review}


class StartResponse(BaseModel):
    submitted: int
    skipped_missing_identity: int


@router.post("/batches/{batch_id}/start-verification", response_model=StartResponse)
def start_verification(
    batch_id: uuid.UUID,
    session: Session = Depends(get_session),
    admin: AdminUser = Depends(require_admin),
) -> StartResponse:
    try:
        res = verification_service.start_verification(session, batch_id, admin.email)
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return StartResponse(
        submitted=res.submitted,
        skipped_missing_identity=res.skipped_missing_identity,
    )


class ResolveRequest(BaseModel):
    status: VerificationStatus
    payer: str | None = None
    plan: str | None = None
    effective_date: date | None = None
    annual_max: Decimal | None = None
    remaining_benefit: Decimal | None = None
    deductible_total: Decimal | None = None
    deductible_met: Decimal | None = None
    note: str | None = None


@router.post("/verifications/{verification_id}/resolve")
def resolve_verification(
    verification_id: uuid.UUID,
    body: ResolveRequest,
    session: Session = Depends(get_session),
    admin: AdminUser = Depends(require_admin),
) -> dict[str, str]:
    try:
        verification_service.resolve_verification(
            session,
            verification_id,
            admin.email,
            status=body.status,
            payer=body.payer,
            plan=body.plan,
            effective_date=body.effective_date,
            annual_max=body.annual_max,
            remaining_benefit=body.remaining_benefit,
            deductible_total=body.deductible_total,
            deductible_met=body.deductible_met,
            note=body.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="verification not found") from exc
    return {"status": "ok"}


class ApproveResponse(BaseModel):
    report_id: str


@router.post("/batches/{batch_id}/approve", response_model=ApproveResponse)
def approve_batch(
    batch_id: uuid.UUID,
    session: Session = Depends(get_session),
    admin: AdminUser = Depends(require_admin),
) -> ApproveResponse:
    try:
        report_id = verification_service.approve_batch(session, batch_id, admin.email)
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApproveResponse(report_id=str(report_id))


class SendResponse(BaseModel):
    report_url: str
    purge_at: str


@router.post("/batches/{batch_id}/send", response_model=SendResponse)
def send_report(
    batch_id: uuid.UUID,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    admin: AdminUser = Depends(require_admin),
    store: ObjectStore = Depends(get_object_store),
    email_sender: EmailSender = Depends(get_email_sender),
) -> SendResponse:
    try:
        result = delivery_service.send_report(
            session, batch_id, store, email_sender, settings, admin.email
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SendResponse(report_url=result.report_url, purge_at=result.purge_at.isoformat())
