"""Filesystem-backed ObjectStore for local dev and tests. Not for prod."""

from __future__ import annotations

from pathlib import Path


class LocalObjectStore:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Keep keys from escaping the root.
        safe = key.replace("..", "_").lstrip("/")
        p = self._root / safe
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._path(key).write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def presigned_url(self, key: str, expires_seconds: int) -> str:
        # No real signing locally; return a file URL for debugging only.
        return f"file://{self._path(key)}"
