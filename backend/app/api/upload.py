"""Public, token-scoped upload endpoint — the account-less client surface.

A practice hits POST /upload/{token} with their appointment file. No login. The
token is single-use and scoped to one practice. The response carries only counts,
never PHI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.services.intake_service import IntakeError, ingest_upload
from app.storage import ObjectStore, get_object_store

router = APIRouter(tags=["upload"])

# Reject oversized uploads early (a day sheet is tiny; anything large is susp.).
_MAX_BYTES = 10 * 1024 * 1024


class UploadResponse(BaseModel):
    batch_id: str
    rows_parsed: int
    rows_needing_review: int


@router.post("/upload/{token}", response_model=UploadResponse)
def upload_appointment_list(
    token: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    store: ObjectStore = Depends(get_object_store),
) -> UploadResponse:
    data = file.file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="file too large")
    if not data:
        raise HTTPException(status_code=400, detail="empty file")

    try:
        result = ingest_upload(
            session=session,
            store=store,
            raw_token=token,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            data=data,
            settings=get_settings(),
        )
    except IntakeError as exc:
        # Do not leak which reason; a generic 400 is fine for the client surface.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        batch_id=str(result.batch_id),
        rows_parsed=result.rows_parsed,
        rows_needing_review=result.rows_needing_review,
    )
