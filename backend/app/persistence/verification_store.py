"""SQLAlchemy-backed VerificationStore — the bridge from the eligibility
abstraction to the DB. The manual source and (later) the EDI source both write
through this, so persisted verifications look identical regardless of origin.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.eligibility.source import VerificationStore
from app.eligibility.types import (
    EligibilityRequest,
    EligibilityResult,
    PendingVerification,
    SourceKind,
    VerificationStatus,
)
from app.models import Verification


class SqlVerificationStore(VerificationStore):
    def __init__(self, session: Session, actor: str, source: SourceKind) -> None:
        self._session = session
        self._actor = actor
        self._source = source

    def create_pending(
        self, request: EligibilityRequest, missing_fields: list[str]
    ) -> str:
        if not request.correlation_id:
            raise ValueError("correlation_id (appointment id) is required")
        note = None
        if missing_fields:
            note = "missing for clean v2 EDI: " + ", ".join(missing_fields)
        v = Verification(
            appointment_id=uuid.UUID(request.correlation_id),
            source=self._source,
            status=VerificationStatus.PENDING,
            note=note,
        )
        self._session.add(v)
        self._session.commit()
        return str(v.id)

    def resolve(self, verification_id: str, result: EligibilityResult) -> None:
        v = self._session.get(Verification, uuid.UUID(verification_id))
        if v is None:
            raise KeyError(verification_id)
        v.status = result.status
        v.payer = result.payer
        v.plan = result.plan
        v.effective_date = result.effective_date
        v.annual_max = result.annual_max
        v.remaining_benefit = result.remaining_benefit
        v.deductible_total = result.deductible_total
        v.deductible_met = result.deductible_met
        v.detailed = result.detailed
        v.raw_payload = result.raw_payload
        if result.note:
            v.note = result.note
        v.verified_by = self._actor
        v.verified_at = datetime.now(UTC)
        self._session.commit()

    def get(self, verification_id: str) -> PendingVerification:
        v = self._session.get(Verification, uuid.UUID(verification_id))
        if v is None:
            raise KeyError(verification_id)
        result: EligibilityResult | None = None
        if v.status != VerificationStatus.PENDING:
            result = EligibilityResult(
                status=v.status,
                source=v.source,
                payer=v.payer,
                plan=v.plan,
                effective_date=v.effective_date,
                annual_max=v.annual_max,
                remaining_benefit=v.remaining_benefit,
                deductible_total=v.deductible_total,
                deductible_met=v.deductible_met,
                detailed=v.detailed,
                raw_payload=v.raw_payload,
                note=v.note,
            )
        # request is not reconstructed from storage here (not needed by callers);
        # the appointment row holds the identifiers.
        return PendingVerification(
            verification_id=str(v.id),
            request=None,
            status=v.status,
            result=result,
        )
