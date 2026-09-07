"""Email delivery (SES in prod, local recorder in dev/tests). Links only, no PHI."""

from functools import lru_cache

from app.config import get_settings

from .base import EmailSender, SentEmail
from .local import LocalEmailSender

__all__ = ["EmailSender", "SentEmail", "LocalEmailSender", "get_email_sender"]

_local_singleton = LocalEmailSender()


@lru_cache
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.environment == "local":
        return _local_singleton
    from .ses import SesEmailSender

    return SesEmailSender(
        region=settings.aws_region,
        from_address=f"no-reply@{settings.public_base_url.split('//')[-1]}",
    )
