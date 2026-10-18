from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class NoteWarning(BaseModel):
    """Something in a draft the user should double-check; never stored with the note."""

    field: str | None = None
    message: str


class NoteEnvelope(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str
    timezone: str
    transcript: str
    type_name: str
    type_version: int
    summary: str
    fields: dict[str, Any]
    status: Literal["needs_review", "confirmed"] = "needs_review"
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[NoteWarning] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    fields: dict[str, Any] | None = None
    summary: str | None = None
    status: Literal["needs_review", "confirmed"] | None = None


class ProcessTextRequest(BaseModel):
    transcript: str
    captured_at: str
    timezone: str


class RetypeRequest(BaseModel):
    transcript: str
    type_name: str
    captured_at: str
    timezone: str


class ConfirmNoteRequest(BaseModel):
    """Full NoteEnvelope submitted by the client to persist a confirmed note."""

    id: str
    created_at: str
    timezone: str
    transcript: str
    type_name: str
    type_version: int
    summary: str
    fields: dict[str, Any]
    status: Literal["needs_review", "confirmed"]
    missing_fields: list[str]
