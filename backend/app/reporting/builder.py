"""Build the report's view model from a batch. Pure data — no rendering, no I/O —
so the HTML and PDF renderers share one source of truth."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.eligibility.types import VerificationStatus
from app.models import Batch, Practice


@dataclass(slots=True)
class ReportRow:
    appt_time: str | None
    patient_name: str
    dob: date | None
    payer: str | None
    plan: str | None
    status: str
    annual_max: Decimal | None
    remaining_benefit: Decimal | None
    deductible_total: Decimal | None
    deductible_met: Decimal | None
    note: str | None
    verified: bool


@dataclass(slots=True)
class ReportData:
    practice_name: str
    batch_id: str
    generated_at: str
    rows: list[ReportRow] = field(default_factory=list)

    @property
    def verified_count(self) -> int:
        return sum(1 for r in self.rows if r.verified)

    @property
    def unverified_count(self) -> int:
        return len(self.rows) - self.verified_count


_RESOLVED = {VerificationStatus.ACTIVE, VerificationStatus.INACTIVE}


def build_report_data(session: Session, batch: Batch) -> ReportData:
    practice = session.get(Practice, batch.practice_id)
    rows: list[ReportRow] = []
    for appt in sorted(batch.appointments, key=lambda a: (a.appt_time is None, a.appt_time)):
        v = appt.verification
        status = v.status.value if v else "not_verified"
        rows.append(
            ReportRow(
                appt_time=appt.appt_time.strftime("%I:%M %p") if appt.appt_time else None,
                patient_name=appt.patient_name or "(unknown)",
                dob=appt.dob,
                payer=(v.payer if v else None) or appt.payer_name,
                plan=v.plan if v else None,
                status=status,
                annual_max=v.annual_max if v else None,
                remaining_benefit=v.remaining_benefit if v else None,
                deductible_total=v.deductible_total if v else None,
                deductible_met=v.deductible_met if v else None,
                note=v.note if v else "missing info - could not verify",
                verified=bool(v and v.status in _RESOLVED),
            )
        )
    return ReportData(
        practice_name=practice.name if practice else "?",
        batch_id=str(batch.id),
        generated_at=(batch.report_ready_at or batch.created_at).strftime("%A, %B %d, %Y"),
        rows=rows,
    )
