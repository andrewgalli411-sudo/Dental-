"""The eligibility source protocol — the seam between v1 (manual) and v2 (EDI).

Design decision: resolution is **out-of-band**, not a blocking return.

A manual pull takes minutes-to-hours (a human on hold with a payer); an EDI
270/271 round-trip takes seconds. A synchronous `verify() -> result` signature
would fit EDI but not the human, and would force a rewrite at v2. So a source
only *submits* a request and hands back a verification id in `PENDING`. Something
else resolves it later:

  - v1: the founder, via the admin UI, calling `VerificationStore.resolve`.
  - v2: a 271 webhook/poller parsing the response into the same store.

Both write the *same* `EligibilityResult` into the *same* record. Nothing
downstream (report generation, status tracking) knows or cares which source ran.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .types import (
    EligibilityRequest,
    EligibilityResult,
    PendingVerification,
    SourceKind,
)


@runtime_checkable
class VerificationStore(Protocol):
    """Persistence seam for verifications.

    Kept separate from `EligibilitySource` so sources stay free of ORM/DB
    concerns and are trivially testable with an in-memory store. In the app this
    is backed by SQLAlchemy; in tests, by a dict.
    """

    def create_pending(
        self, request: EligibilityRequest, missing_fields: list[str]
    ) -> str:
        """Persist a new PENDING verification; return its id."""
        ...

    def resolve(self, verification_id: str, result: EligibilityResult) -> None:
        """Attach a result and move the verification to its final status."""
        ...

    def get(self, verification_id: str) -> PendingVerification:
        ...


@runtime_checkable
class EligibilitySource(Protocol):
    """Submits eligibility requests. Resolution happens out-of-band."""

    kind: SourceKind

    def submit(self, request: EligibilityRequest) -> str:
        """Submit one request; return the verification id (status PENDING)."""
        ...
