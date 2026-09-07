"""The eligibility verification seam (v1 manual → v2 EDI 270/271)."""

from .manual import ManualEligibilitySource
from .source import EligibilitySource, VerificationStore
from .types import (
    EligibilityRequest,
    EligibilityResult,
    PendingVerification,
    SourceKind,
    VerificationStatus,
)

__all__ = [
    "EligibilityRequest",
    "EligibilityResult",
    "EligibilitySource",
    "ManualEligibilitySource",
    "PendingVerification",
    "SourceKind",
    "VerificationStatus",
    "VerificationStore",
]
