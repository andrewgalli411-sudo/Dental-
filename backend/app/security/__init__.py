"""Security primitives: link tokens (Phase 2); admin auth/MFA arrives in Phase 3."""

from .tokens import generate_token, hash_token

__all__ = ["generate_token", "hash_token"]
