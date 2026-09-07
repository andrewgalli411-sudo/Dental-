"""Bootstrap the first admin user.

Usage:
    python -m scripts.create_admin founder@example.com

Prompts for a password, creates the admin, and prints the otpauth:// URI to add
to an authenticator app (Google Authenticator, 1Password, etc.). The TOTP secret
is shown ONCE and never again — scan/save it immediately.
"""

from __future__ import annotations

import getpass
import sys

from app.db import SessionLocal
from app.security.auth import create_admin


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m scripts.create_admin <email>", file=sys.stderr)
        return 2
    email = sys.argv[1]
    password = getpass.getpass("Password: ")
    if getpass.getpass("Confirm password: ") != password:
        print("passwords do not match", file=sys.stderr)
        return 1
    if len(password) < 12:
        print("use at least 12 characters", file=sys.stderr)
        return 1

    with SessionLocal() as session:
        _admin, uri = create_admin(session, email, password)

    print("\nAdmin created. Add this to your authenticator app NOW (shown once):")
    print(uri)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
