"""Login throttling. The admin login is the single door to all PHI, so repeated
failures lock the account key for a cool-off window.

v1 is in-memory: correct and sufficient while App Runner runs a single backend
instance (the default min). If you scale to multiple instances, move this to a
shared store (Redis/DB) so the counter is global — noted in CLAUDE.md.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("too many attempts")


class LoginRateLimiter:
    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: int = 300,
        lockout_seconds: int = 900,
        clock=time.monotonic,
    ) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._lockout = lockout_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Raise TooManyAttempts if this key is currently locked out."""
        now = self._clock()
        with self._lock:
            until = self._locked_until.get(key)
            if until is not None and now < until:
                raise TooManyAttempts(retry_after=int(until - now) + 1)

    def record_failure(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            recent = [t for t in self._failures[key] if now - t < self._window]
            recent.append(now)
            self._failures[key] = recent
            if len(recent) >= self._max:
                self._locked_until[key] = now + self._lockout
                self._failures[key] = []

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()


# Module singleton used by the login endpoint.
login_limiter = LoginRateLimiter()
