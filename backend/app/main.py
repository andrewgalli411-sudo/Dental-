"""FastAPI entrypoint.

Phase 1 is deliberately thin: a health check and wiring only. No PHI-handling
endpoints exist yet — intake (Phase 2), admin/verification (Phase 3), and
report delivery (Phase 4) are added behind auth and the review gate later.
"""

from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .logging_config import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("verifi")

app = FastAPI(
    title="verifi-dental",
    version="0.1.0",
    description="Dental eligibility verification (wizard-of-oz v1).",
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
