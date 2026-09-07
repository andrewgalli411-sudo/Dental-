"""Object storage abstraction.

Raw uploaded files (PHI) and generated report PDFs live in object storage, never
in the DB. In prod that's S3 with SSE-KMS; in dev/tests it's the local filesystem.
Callers depend only on this protocol, so swapping S3 in at Phase 0 changes nothing
upstream.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store bytes at key."""
        ...

    def get(self, key: str) -> bytes:
        ...

    def delete(self, key: str) -> None:
        """Delete the object. Idempotent — deleting a missing key is not an error."""
        ...

    def presigned_url(self, key: str, expires_seconds: int) -> str:
        """A time-boxed URL the client can use to fetch the object directly."""
        ...
