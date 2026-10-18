from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi import Request as FastAPIRequest
from fastapi.responses import StreamingResponse

from app.api.models import (
    ConfirmNoteRequest,
    NoteEnvelope,
    NoteUpdateRequest,
    ProcessTextRequest,
    RetypeRequest,
)
from app.api.streaming import stream_pipeline
from app.config.settings import get_settings
from app.errors import NotFoundError, RecordingTooLargeError
from app.services.note_service import NoteService
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/notes", tags=["notes"])

_UPLOAD_CHUNK_BYTES = 1024 * 1024


def _pipeline(request: FastAPIRequest) -> PipelineService:
    return request.app.state.pipeline_service


def _notes(request: FastAPIRequest) -> NoteService:
    return request.app.state.note_service


async def _save_upload(audio: UploadFile) -> str:
    """Copy the upload to a temporary file in chunks, refusing anything over the size limit.

    The caller must delete the returned file; on refusal it is deleted here.
    """
    max_bytes = get_settings().max_upload_bytes
    suffix = Path(audio.filename or "audio").suffix or ".wav"
    written = 0
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        try:
            while chunk := await audio.read(_UPLOAD_CHUNK_BYTES):
                written += len(chunk)
                if written > max_bytes:
                    raise RecordingTooLargeError(
                        f"That recording is too large (over {max_bytes // (1024 * 1024)} MB). "
                        "Please record a shorter note."
                    )
                tmp.write(chunk)
        except BaseException:
            Path(tmp.name).unlink(missing_ok=True)
            raise
    return tmp.name


@router.post("/process", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def process_audio(
    audio: UploadFile,
    captured_at: str = Form(...),
    timezone: str = Form(...),
    pipeline: PipelineService = Depends(_pipeline),
) -> NoteEnvelope:
    """Transcribe an audio file and run the full classification pipeline."""
    tmp_path = await _save_upload(audio)
    try:
        return await pipeline.process_audio(tmp_path, captured_at, timezone)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/process/stream", response_class=StreamingResponse)
async def process_audio_stream(
    audio: UploadFile,
    captured_at: str = Form(...),
    timezone: str = Form(...),
    pipeline: PipelineService = Depends(_pipeline),
) -> StreamingResponse:
    """Like /notes/process, but streams progress as NDJSON: {"stage": ...} lines, then a
    final {"draft": ...} or {"error": ...} line."""
    tmp_path = await _save_upload(audio)
    return stream_pipeline(
        lambda on_stage: pipeline.process_audio(tmp_path, captured_at, timezone, on_stage),
        on_finish=lambda: Path(tmp_path).unlink(missing_ok=True),
    )


@router.post("/process-text/stream", response_class=StreamingResponse)
async def process_text_stream(
    body: ProcessTextRequest,
    pipeline: PipelineService = Depends(_pipeline),
) -> StreamingResponse:
    """Like /notes/process-text, but streams progress as NDJSON (see /notes/process/stream)."""
    return stream_pipeline(
        lambda on_stage: pipeline.process_text(
            body.transcript, body.captured_at, body.timezone, on_stage
        )
    )


@router.post("/process-text", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def process_text(
    body: ProcessTextRequest,
    pipeline: PipelineService = Depends(_pipeline),
) -> NoteEnvelope:
    """Run the classification pipeline on a raw transcript."""
    return await pipeline.process_text(body.transcript, body.captured_at, body.timezone)


@router.post("", response_model=NoteEnvelope, status_code=status.HTTP_201_CREATED)
async def save_note(
    body: ConfirmNoteRequest,
    note_svc: NoteService = Depends(_notes),
) -> NoteEnvelope:
    """Persist a confirmed note envelope."""
    envelope = NoteEnvelope(**body.model_dump())
    return await note_svc.save_note(envelope)


@router.get("", response_model=list[NoteEnvelope], status_code=status.HTTP_200_OK)
async def list_notes(
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
    note_svc: NoteService = Depends(_notes),
) -> NoteEnvelope:
    """Partially update a note's fields, summary, or status."""
    updated = await note_svc.update_note(note_id, body.model_dump(exclude_none=True))
    if updated is None:
        raise NotFoundError(f"Note {note_id!r} not found.")
    return updated


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    note_svc: NoteService = Depends(_notes),
) -> None:
    """Delete a note by ID."""
    deleted = await note_svc.delete_note(note_id)
    if not deleted:
        raise NotFoundError(f"Note {note_id!r} not found.")


@router.post("/retype", response_model=NoteEnvelope, status_code=status.HTTP_200_OK)
async def retype_note(
    body: RetypeRequest,
    pipeline: PipelineService = Depends(_pipeline),
) -> NoteEnvelope:
    """Re-run extract → resolve → validate with a user-specified type."""
    return await pipeline.retype(body.transcript, body.type_name, body.captured_at, body.timezone)
