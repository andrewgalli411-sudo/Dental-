from __future__ import annotations

import pyotp

from app.security.auth import create_admin
from app.security.ratelimit import LoginRateLimiter, TooManyAttempts
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def test_locks_out_after_max_failures() -> None:
    lim = LoginRateLimiter(max_failures=3, window_seconds=300, lockout_seconds=900)
    for _ in range(3):
        lim.check("k")  # not locked yet
        lim.record_failure("k")
    try:
        lim.check("k")
        raise AssertionError("expected lockout")
    except TooManyAttempts as e:
        assert e.retry_after > 0


def test_success_clears_failures() -> None:
    lim = LoginRateLimiter(max_failures=3)
    lim.record_failure("k")
    lim.record_failure("k")
    lim.record_success("k")
    lim.check("k")  # cleared — no raise
    lim.record_failure("k")  # counter restarted
    lim.check("k")


def test_window_expiry_forgets_old_failures() -> None:
    t = {"now": 1000.0}
    lim = LoginRateLimiter(max_failures=3, window_seconds=60, clock=lambda: t["now"])
    lim.record_failure("k")
    lim.record_failure("k")
    t["now"] += 120  # both failures now outside the window
    lim.record_failure("k")
    lim.check("k")  # only 1 failure in-window → not locked


def test_login_endpoint_locks_out(client, session_factory) -> None:
    with session_factory() as s:
        admin, _ = create_admin(s, ADMIN_EMAIL, ADMIN_PASSWORD)
        secret = admin.totp_secret

    # 5 wrong attempts (default max) then a correct one — still blocked with 429.
    for _ in range(5):
        r = client.post(
            "/admin/login",
            json={"email": ADMIN_EMAIL, "password": "wrong", "totp": "000000"},
        )
        assert r.status_code == 401
    blocked = client.post(
        "/admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "totp": pyotp.TOTP(secret).now()},
    )
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
