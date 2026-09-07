"""Persistence adapters that back domain abstractions with SQLAlchemy."""

from .verification_store import SqlVerificationStore

__all__ = ["SqlVerificationStore"]
