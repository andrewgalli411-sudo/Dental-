"""Contract tests for the eligibility seam.

The point of these tests is not to exercise a database — it's to prove the
*shape* of the v1→v2 swap:

  1. `submit` records a PENDING verification; out-of-band `resolve` finalizes it.
  2. Missing recommended identifiers are flagged (admin chase-work / v2 readiness).
  3. A completely different source (a fake clearinghouse that resolves inline)
     drops in behind the same protocol with zero changes to calling code.

If test 3 ever needs to touch anything outside `app.eligibility`, the seam has
leaked and v2 will not be a clean swap.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.eligibility import (
    EligibilityRequest,
    EligibilityResult,
    EligibilitySource,
    ManualEligibilitySource,
    PendingVerification,
    SourceKind,
    VerificationStatus,
)
from app.eligibility.source import VerificationStore


class InMemoryStore(VerificationStore):
    """Dict-backed store standing in for the SQLAlchemy-backed one."""

    def __init__(self) -> None:
        self._rows: dict[str, PendingVerification] = {}

    def create_pending(
        self, request: EligibilityRequest, missing_fields: list[str]
    ) -> str:
        vid = str(uuid.uuid4())
        self._rows[vid] = PendingVerification(
            verification_id=vid,
            request=request,
            status=VerificationStatus.PENDING,
            missing_fields=list(missing_fields),
        )
        return vid

    def resolve(self, verification_id: str, result: EligibilityResult) -> None:
        row = self._rows[verification_id]
        row.result = result
        row.status = result.status

    def get(self, verification_id: str) -> PendingVerification:
        return self._rows[verification_id]


class FakeClearinghouseSource(EligibilitySource):
    """Stand-in for the future v2 EDI 270/271 source.

    Unlike the manual source, a real clearinghouse resolves in ~seconds, so this
    fake resolves inline right after submitting. Calling code cannot tell the
    difference — that's the whole point.
    """

    kind = SourceKind.EDI_270_271

    def __init__(self, store: VerificationStore, canned: EligibilityResult) -> None:
        self._store = store
        self._canned = canned

    def submit(self, request: EligibilityRequest) -> str:
        vid = self._store.create_pending(
            request, missing_fields=request.missing_recommended_fields()
        )
        self._store.resolve(vid, self._canned)
        return vid


def _request(**overrides: object) -> EligibilityRequest:
    base = dict(
        patient_name="Test Patient",
        dob=date(1990, 1, 1),
        payer_name="Delta Dental",
        provider_npi="1234567890",
        provider_tax_id="99-9999999",
    )
    base.update(overrides)
    return EligibilityRequest(**base)  # type: ignore[arg-type]


def test_manual_submit_creates_pending() -> None:
    store = InMemoryStore()
    source = ManualEligibilitySource(store)

    vid = source.submit(_request(subscriber_id="ABC123", payer_id="DDCA"))

    row = store.get(vid)
    assert row.status is VerificationStatus.PENDING
    assert row.result is None
    assert row.missing_fields == []


def test_manual_flags_missing_recommended_fields() -> None:
    store = InMemoryStore()
    source = ManualEligibilitySource(store)

    # Only the v1-required minimum is present.
    vid = source.submit(_request())

    row = store.get(vid)
    assert set(row.missing_fields) == {"subscriber_id", "payer_id"}


def test_out_of_band_resolution_finalizes_manual_verification() -> None:
    store = InMemoryStore()
    source = ManualEligibilitySource(store)
    vid = source.submit(_request(subscriber_id="ABC123", payer_id="DDCA"))

    # The founder enters eligibility later, via the admin UI.
    result = EligibilityResult(
        status=VerificationStatus.ACTIVE,
        source=SourceKind.MANUAL,
        payer="Delta Dental",
        plan="PPO",
        effective_date=date(2026, 1, 1),
        annual_max=Decimal("1500.00"),
        remaining_benefit=Decimal("1200.00"),
        deductible_total=Decimal("50.00"),
        deductible_met=Decimal("50.00"),
    )
    store.resolve(vid, result)

    row = store.get(vid)
    assert row.status is VerificationStatus.ACTIVE
    assert row.result is not None
    assert row.result.is_resolved()
    assert row.result.remaining_benefit == Decimal("1200.00")
    assert row.result.source is SourceKind.MANUAL


def test_v2_source_swaps_in_unchanged() -> None:
    """The seam proof: swap the source, calling code is byte-for-byte identical."""
    store = InMemoryStore()
    canned = EligibilityResult(
        status=VerificationStatus.ACTIVE,
        source=SourceKind.EDI_270_271,
        payer="Delta Dental",
        plan="PPO",
        annual_max=Decimal("2000.00"),
        remaining_benefit=Decimal("2000.00"),
        raw_payload={"271": "..."},
    )

    def run(source: EligibilitySource, req: EligibilityRequest) -> PendingVerification:
        # Identical for manual and clearinghouse — no source-specific branches.
        vid = source.submit(req)
        return store.get(vid)

    req = _request(subscriber_id="ABC123", payer_id="DDCA")
    row = run(FakeClearinghouseSource(store, canned), req)

    assert row.status is VerificationStatus.ACTIVE
    assert row.result is not None
    assert row.result.source is SourceKind.EDI_270_271
    assert row.result.raw_payload == {"271": "..."}


def test_result_immutability_keeps_audit_trail_honest() -> None:
    """Results are frozen; a correction is a new object, never a mutation."""
    original = EligibilityResult(
        status=VerificationStatus.ACTIVE, source=SourceKind.MANUAL,
        remaining_benefit=Decimal("1000.00"),
    )
    corrected = replace(original, remaining_benefit=Decimal("900.00"))
    assert original.remaining_benefit == Decimal("1000.00")
    assert corrected.remaining_benefit == Decimal("900.00")
