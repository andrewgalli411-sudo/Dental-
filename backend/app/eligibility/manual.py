"""v1 eligibility source: the human.

`submit` just records a PENDING verification (flagging any missing identifiers so
the admin queue can surface chase-work). The founder resolves it later through
the admin UI, which calls `VerificationStore.resolve`. There is no
auto-completion here by design — a report must never go out on data no human
entered.
"""

from __future__ import annotations

from .source import EligibilitySource, VerificationStore
from .types import EligibilityRequest, SourceKind


class ManualEligibilitySource(EligibilitySource):
    kind = SourceKind.MANUAL

    def __init__(self, store: VerificationStore) -> None:
        self._store = store

    def submit(self, request: EligibilityRequest) -> str:
        missing = request.missing_recommended_fields()
        return self._store.create_pending(request, missing_fields=missing)
