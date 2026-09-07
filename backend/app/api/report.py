"""Public, token-scoped report surface. A practice opens the secure link from
their email; no login. The link is multi-use until it expires, so they can view
and print it repeatedly. This is the one public route that renders PHI — only to
the holder of the unguessable, expiring token."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AccessToken, Batch
from app.models.enums import TokenScope
from app.reporting import build_report_data, render_html, render_pdf
from app.security import hash_token
from app.storage import ObjectStore, get_object_store

router = APIRouter(tags=["report"])


def _batch_for_report_token(session: Session, token: str) -> Batch:
    at = session.scalar(
        select(AccessToken).where(AccessToken.token_hash == hash_token(token))
    )
    if at is None or at.scope != TokenScope.REPORT_VIEW or at.batch_id is None:
        raise HTTPException(status_code=404, detail="not found")
    if not at.is_usable(datetime.now(UTC)):  # report tokens: never marked used, so this is expiry
        raise HTTPException(status_code=404, detail="not found")
    batch = session.get(Batch, at.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="not found")
    return batch


@router.get("/report/{token}", response_class=HTMLResponse)
def view_report(
    token: str,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    batch = _batch_for_report_token(session, token)
    data = build_report_data(session, batch)
    return HTMLResponse(render_html(data))


@router.get("/report/{token}/pdf")
def download_report_pdf(
    token: str,
    session: Session = Depends(get_session),
    store: ObjectStore = Depends(get_object_store),
) -> Response:
    batch = _batch_for_report_token(session, token)
    pdf: bytes | None = None
    if batch.report and batch.report.pdf_s3_key:
        try:
            pdf = store.get(batch.report.pdf_s3_key)
        except Exception:  # noqa: BLE001 — fall back to on-the-fly render
            pdf = None
    if pdf is None:
        pdf = render_pdf(build_report_data(session, batch))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=eligibility-report.pdf"},
    )
