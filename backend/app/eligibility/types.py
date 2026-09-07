"""Data contract for eligibility verification.

These types are the stable boundary between the rest of the app and *whatever*
actually pulls eligibility — a human in v1, an EDI 270/271 clearinghouse in v2.
Keep them ORM-free and dependency-free so both sides can depend on them without
coupling to the database or a specific source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum


class VerificationStatus(StrEnum):
    """Lifecycle of a single patient's verification."""

    PENDING = "pending"          # submitted, not yet resolved
    NEEDS_INFO = "needs_info"    # missing identifiers block the pull
    ACTIVE = "active"            # coverage confirmed active
    INACTIVE = "inactive"        # coverage confirmed inactive
    ERROR = "error"              # source failed (payer down, bad data, etc.)


class SourceKind(StrEnum):
    MANUAL = "manual"
    EDI_270_271 = "edi_270_271"


@dataclass(frozen=True, slots=True)
class EligibilityRequest:
    """Everything a source might need to verify one patient.

    v1 only *requires* name + DOB + payer. The rest are optional because
    practices frequently omit them — missing fields become manual-chase items.
    But the full set is modeled now because an EDI 270 needs it in v2; this way
    the interface never changes.
    """

    # Required minimum (v1 contract).
    patient_name: str
    dob: date
    payer_name: str

    # Provider identity (from practice onboarding, not the per-day list).
    provider_npi: str
    provider_tax_id: str

    # Caller's handle to correlate the async result back to what was requested
    # (here, the appointment id). In v2 this maps to the EDI 270 TRN trace number,
    # which is how a 271 response is tied to its request.
    correlation_id: str | None = None

    # Optional patient/subscriber identifiers.
    subscriber_id: str | None = None
    subscriber_name: str | None = None      # when patient is a dependent
    subscriber_dob: date | None = None
    payer_id: str | None = None             # required by EDI 270 in v2
    group_number: str | None = None

    def missing_recommended_fields(self) -> list[str]:
        """Fields that are optional in v1 but needed for a clean EDI 270 later.

        The admin queue uses this to flag chase-work, and it doubles as a v2
        readiness signal.
        """
        missing: list[str] = []
        if not self.subscriber_id:
            missing.append("subscriber_id")
        if not self.payer_id:
            missing.append("payer_id")
        return missing


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    """Normalized result, identical no matter which source produced it."""

    status: VerificationStatus
    source: SourceKind

    payer: str | None = None
    plan: str | None = None
    effective_date: date | None = None
    annual_max: Decimal | None = None
    remaining_benefit: Decimal | None = None
    deductible_total: Decimal | None = None
    deductible_met: Decimal | None = None

    # v2: per-category coverage %, frequency limits, waiting periods, etc.
    detailed: dict | None = None
    # v2: parsed EDI 271 payload for audit/debug. Null in v1.
    raw_payload: dict | None = None

    # Free-text note from the human (v1) or an error/AAA reason (v2).
    note: str | None = None

    def is_resolved(self) -> bool:
        return self.status in {
            VerificationStatus.ACTIVE,
            VerificationStatus.INACTIVE,
        }


@dataclass(slots=True)
class PendingVerification:
    """A submitted-but-unresolved verification, as tracked by a VerificationStore."""

    verification_id: str
    request: EligibilityRequest | None
    status: VerificationStatus = VerificationStatus.PENDING
    result: EligibilityResult | None = None
    missing_fields: list[str] = field(default_factory=list)
