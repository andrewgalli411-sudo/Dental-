"""Email sending abstraction. SES in prod, a local recorder in dev/tests.

Rule: email bodies carry only a secure link, never PHI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(slots=True)
class SentEmail:
    to: str
    subject: str
    body: str


@runtime_checkable
class EmailSender(Protocol):
    def send(self, to: str, subject: str, body: str) -> None:
        ...
