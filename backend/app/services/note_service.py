from __future__ import annotations

from typing import Any

from app.api.models import NoteEnvelope
from app.storage import queries


class NoteService:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    async def save_note(self, envelope: NoteEnvelope) -> NoteEnvelope:
        return await queries.insert_note(envelope, db_path=self._db_path)

    async def get_notes(
        self,
        type_name: str | None = None,
        person: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NoteEnvelope]:
        return await queries.get_notes(
            db_path=self._db_path,
            type_name=type_name,
            person=person,
            date_from=date_from,
            date_to=date_to,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def get_note(self, note_id: str) -> NoteEnvelope | None:
        return await queries.get_note(note_id, db_path=self._db_path)

    async def update_note(self, note_id: str, updates: dict[str, Any]) -> NoteEnvelope | None:
        return await queries.update_note(note_id, updates, db_path=self._db_path)

    async def delete_note(self, note_id: str) -> bool:
        return await queries.delete_note(note_id, db_path=self._db_path)
