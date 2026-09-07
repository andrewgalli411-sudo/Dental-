"""Workflow enums (persisted). Eligibility enums live in app.eligibility.types."""

from __future__ import annotations

from enum import StrEnum


class BatchStatus(StrEnum):
    UPLOADED = "uploaded"      # raw file stored, not yet parsed
    PARSING = "parsing"        # normalizer running
    REVIEW = "review"          # parsed; awaiting founder review/correction
    VERIFYING = "verifying"    # eligibility being pulled per patient
    READY = "ready"            # approved; report generated, not yet delivered
    DELIVERED = "delivered"    # secure link emailed to practice
    PURGED = "purged"          # PHI removed (>=7d after delivery)
    ERROR = "error"


class TokenScope(StrEnum):
    UPLOAD = "upload"          # practice uploads a day's list
    REPORT_VIEW = "report_view"  # practice views/downloads a report
