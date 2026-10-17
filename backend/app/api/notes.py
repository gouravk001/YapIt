from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from fastapi import Request as FastAPIRequest

from app.api.models import (
    ConfirmNoteRequest,
    NoteEnvelope,
    NoteUpdateRequest,
    ProcessTextRequest,
    RetypeRequest,
)
from app.services.note_service import NoteService
from app.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notes", tags=["notes"])


def _pipeline(request: FastAPIRequest) -> PipelineService:
    return request.app.state.pipeline_service


def _notes(request: FastAPIRequest) -> NoteService:
    return request.app.state.note_service


@router.post("/process", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def process_audio(
    request: FastAPIRequest,
    audio: UploadFile,
    captured_at: str = Form(...),
    timezone: str = Form(...),
    pipeline: PipelineService = Depends(_pipeline),
) -> NoteEnvelope:
    """Transcribe an audio file and run the full classification pipeline."""
    suffix = Path(audio.filename or "audio").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        return await pipeline.process_audio(tmp_path, captured_at, timezone, request)
    except Exception as exc:
        logger.exception("Audio processing failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/process-text", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def process_text(
    body: ProcessTextRequest,
    request: FastAPIRequest,
    pipeline: PipelineService = Depends(_pipeline),
) -> NoteEnvelope:
    """Run the classification pipeline on a raw transcript."""
    try:
        return await pipeline.process_text(
            body.transcript, body.captured_at, body.timezone, request
        )
    except Exception as exc:
        logger.exception("Text processing failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("", response_model=NoteEnvelope, status_code=status.HTTP_201_CREATED)
async def save_note(
    body: ConfirmNoteRequest,
    request: FastAPIRequest,
    note_svc: NoteService = Depends(_notes),
) -> NoteEnvelope:
    """Persist a confirmed note envelope."""
    envelope = NoteEnvelope(**body.model_dump())
    return await note_svc.save_note(envelope)


@router.get("", response_model=list[NoteEnvelope], status_code=status.HTTP_200_OK)
async def list_notes(
    request: FastAPIRequest,
    type_name: str | None = Query(default=None),
    person: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    note_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    note_svc: NoteService = Depends(_notes),
) -> list[NoteEnvelope]:
    """List notes with optional filters and full-text search."""
    return await note_svc.get_notes(
        type_name=type_name,
        person=person,
        date_from=date_from,
        date_to=date_to,
        status=note_status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.patch("/{note_id}", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def update_note(
    note_id: str,
    body: NoteUpdateRequest,
    request: FastAPIRequest,
    note_svc: NoteService = Depends(_notes),
) -> NoteEnvelope:
    """Partially update a note's fields, summary, or status."""
    updated = await note_svc.update_note(note_id, body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Note {note_id!r} not found.")
    return updated


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    request: FastAPIRequest,
    note_svc: NoteService = Depends(_notes),
) -> None:
    """Delete a note by ID."""
    deleted = await note_svc.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Note {note_id!r} not found.")


@router.post("/retype", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def retype_note(
    body: RetypeRequest,
    request: FastAPIRequest,
    pipeline: PipelineService = Depends(_pipeline),
) -> NoteEnvelope:
    """Re-run extract → resolve → validate with a user-specified type."""
    try:
        return await pipeline.retype(
            body.transcript, body.type_name, body.captured_at, body.timezone, request
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Retype failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
