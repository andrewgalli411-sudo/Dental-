"""Admin authentication: argon2 passwords, mandatory TOTP MFA, signed session
cookies. This login is the highest-value target in the system (it reaches all
PHI), so MFA is not optional and there is no password-only path.
"""

from __future__ import annotations

import uuid

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.models import AdminUser

SESSION_COOKIE = "vd_session"
_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def verify_totp(secret: str, code: str) -> bool:
    # valid_window=1 tolerates ~30s clock skew either side.
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="admin-session")


def issue_session(admin_id: uuid.UUID, settings: Settings) -> str:
    return _serializer(settings).dumps({"admin_id": str(admin_id)})


def read_session(value: str, settings: Settings) -> uuid.UUID | None:
    max_age = settings.session_ttl_hours * 3600
    try:
        data = _serializer(settings).loads(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return uuid.UUID(data["admin_id"])
    except (KeyError, ValueError):
        return None


def require_admin(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminUser:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    admin_id = read_session(raw, settings)
    if admin_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    admin = session.get(AdminUser, admin_id)
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive account")
    return admin


def create_admin(
    session: Session, email: str, password: str
) -> tuple[AdminUser, str]:
    """Provision an admin. Returns (admin, otpauth_uri) — show the URI/QR once so
    the founder can add it to an authenticator app; the secret is never shown again.
    """
    secret = pyotp.random_base32()
    admin = AdminUser(
        email=email,
        password_hash=hash_password(password),
        totp_secret=secret,
    )
    session.add(admin)
    session.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="verifi-dental")
    return admin, uri
