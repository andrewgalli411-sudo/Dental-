"""Structured logging with a PHI-field scrubber.

"No PHI in logs" is a headline compliance claim, so it can't rest on developer
discipline alone. The rule here: log structured context via `extra={...}`, and a
filter redacts any field whose name is a known PHI identifier — at any depth in
nested dicts/lists. Free-text messages should never interpolate PHI in the first
place; the scrubber is the backstop for structured context.
"""

from __future__ import annotations

import json
import logging
from typing import Any

# Field names that carry PHI (or direct identifiers). Redacted wherever they
# appear in structured log context.
PHI_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "patient_name",
        "name",
        "dob",
        "date_of_birth",
        "subscriber_id",
        "subscriber_name",
        "subscriber_dob",
        "member_id",
        "payer_id",
        "group_number",
        "ssn",
        "address",
        "phone",
        "email",
        "contact_email",
    }
)

_REDACTED = "[REDACTED]"

# Standard LogRecord attributes we never treat as structured extras.
_RESERVED = frozenset(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (_REDACTED if k.lower() in PHI_FIELD_NAMES else _scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    return value


class PHIScrubbingFilter(logging.Filter):
    """Redacts PHI-named fields from a record's structured extras."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in list(record.__dict__.items()):
            if key in _RESERVED:
                continue
            if key.lower() in PHI_FIELD_NAMES:
                record.__dict__[key] = _REDACTED
            else:
                record.__dict__[key] = _scrub(value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PHIScrubbingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
