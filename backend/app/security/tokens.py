"""Secure link tokens for the account-less client surface.

A raw token goes out in exactly one place — the emailed URL. Only its SHA-256
hash is stored, so a DB compromise never yields a working link. Lookups are by
hash (indexed); we never need to reverse it.
"""

from __future__ import annotations

import hashlib
import secrets

# 32 bytes -> 43-char urlsafe string. Ample entropy against guessing.
_TOKEN_BYTES = 32


def generate_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Store the hash; put the raw in the link."""
    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
