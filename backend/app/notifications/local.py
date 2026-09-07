"""Dev/test email sender: records messages in memory instead of sending."""

from __future__ import annotations

from .base import SentEmail


class LocalEmailSender:
    def __init__(self) -> None:
        self.outbox: list[SentEmail] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.outbox.append(SentEmail(to=to, subject=subject, body=body))
