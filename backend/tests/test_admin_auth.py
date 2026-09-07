from __future__ import annotations

import pyotp

from app.security.auth import create_admin
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def _make_admin(session_factory) -> str:
    with session_factory() as s:
        admin, _ = create_admin(s, ADMIN_EMAIL, ADMIN_PASSWORD)
        return admin.totp_secret


def test_protected_route_requires_auth(client) -> None:
    assert client.get("/admin/batches").status_code == 401


def test_login_rejects_wrong_password(client, session_factory) -> None:
    secret = _make_admin(session_factory)
    resp = client.post(
        "/admin/login",
        json={"email": ADMIN_EMAIL, "password": "wrong", "totp": pyotp.TOTP(secret).now()},
    )
    assert resp.status_code == 401


def test_login_rejects_wrong_totp(client, session_factory) -> None:
    _make_admin(session_factory)
    resp = client.post(
        "/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "totp": "000000"},
    )
    assert resp.status_code == 401


def test_login_success_sets_cookie_and_grants_access(client, session_factory) -> None:
    secret = _make_admin(session_factory)
    resp = client.post(
        "/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "totp": pyotp.TOTP(secret).now()},
    )
    assert resp.status_code == 200
    assert "vd_session" in resp.cookies
    assert client.get("/admin/batches").status_code == 200
