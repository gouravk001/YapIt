from __future__ import annotations

import json
import logging
from typing import Any

from app.api.models import NoteEnvelope
from app.storage.database import get_db_connection

logger = logging.getLogger(__name__)


def _row_to_envelope(row: Any) -> NoteEnvelope:
    fields_raw = row["fields"]
    fields_dict = json.loads(fields_raw) if isinstance(fields_raw, str) else fields_raw

    missing_raw = row["missing_fields"]
    missing_list = json.loads(missing_raw) if isinstance(missing_raw, str) else missing_raw

    return NoteEnvelope(
        id=row["id"],
        created_at=row["created_at"],
        timezone=row["timezone"],
        transcript=row["transcript"],
        type_name=row["type_name"],
        type_version=row["type_version"],
        summary=row["summary"],
        fields=fields_dict or {},
        status=row["status"],
        missing_fields=missing_list or [],
    )


async def insert_note(envelope: NoteEnvelope, db_path: str | None = None) -> NoteEnvelope:
    query = """
        INSERT INTO notes (
            id, created_at, timezone, transcript, type_name,
            type_version, summary, fields, status, missing_fields
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    params = (
        envelope.id,
        envelope.created_at,
        envelope.timezone,
        envelope.transcript,
        envelope.type_name,
        envelope.type_version,
        envelope.summary,
        json.dumps(envelope.fields),
        envelope.status,
        json.dumps(envelope.missing_fields),
    )

    async with get_db_connection(db_path) as db:
        await db.execute(query, params)
        await db.commit()

    logger.info("Saved note %s (type=%s)", envelope.id, envelope.type_name)
    return envelope


async def get_notes(
    db_path: str | None = None,
    type_name: str | None = None,
    person: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[NoteEnvelope]:
    where_clauses: list[str] = []
    params: list[Any] = []

    base_query = "SELECT n.* FROM notes n"

    if search and search.strip():
        base_query += " JOIN notes_fts fts ON n.id = fts.id"
        # Sanitize simple search string for FTS
        clean_search = "".join(c for c in search if c.isalnum() or c in " *_-").strip()
        if clean_search:
            where_clauses.append("fts.notes_fts MATCH ?")
            params.append(f"{clean_search}*")

    if type_name:
        where_clauses.append("n.type_name = ?")
        params.append(type_name)

    if person:
        where_clauses.append("LOWER(n.fields) LIKE ?")
        params.append(f"%{person.lower()}%")

    if date_from:
        where_clauses.append("n.created_at >= ?")
        params.append(date_from)

    if date_to:
        where_clauses.append("n.created_at <= ?")
        params.append(date_to)

    if status:
        where_clauses.append("n.status = ?")
        params.append(status)

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    order_sql = " ORDER BY n.created_at DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])

    full_query = f"{base_query}{where_sql}{order_sql}"

    async with get_db_connection(db_path) as db:
        async with db.execute(full_query, params) as cursor:
            rows = await cursor.fetchall()
            return [_row_to_envelope(r) for r in rows]


async def get_note(note_id: str, db_path: str | None = None) -> NoteEnvelope | None:
    async with get_db_connection(db_path) as db:
        async with db.execute("SELECT * FROM notes WHERE id = ?;", (note_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_envelope(row)


async def update_note(
    note_id: str, updates: dict[str, Any], db_path: str | None = None
) -> NoteEnvelope | None:
    existing = await get_note(note_id, db_path)
    if not existing:
        return None

    set_clauses: list[str] = []
    params: list[Any] = []

    if "summary" in updates and updates["summary"] is not None:
        set_clauses.append("summary = ?")
        params.append(updates["summary"])
    if "status" in updates and updates["status"] is not None:
        set_clauses.append("status = ?")
        params.append(updates["status"])
    if "fields" in updates and updates["fields"] is not None:
        set_clauses.append("fields = ?")
        params.append(json.dumps(updates["fields"]))
    if "missing_fields" in updates and updates["missing_fields"] is not None:
        set_clauses.append("missing_fields = ?")
        params.append(json.dumps(updates["missing_fields"]))

    if not set_clauses:
        return existing

    params.append(note_id)
    query = f"UPDATE notes SET {', '.join(set_clauses)} WHERE id = ?;"

    async with get_db_connection(db_path) as db:
        await db.execute(query, params)
        await db.commit()

    return await get_note(note_id, db_path)


async def delete_note(note_id: str, db_path: str | None = None) -> bool:
    async with get_db_connection(db_path) as db:
        cursor = await db.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_type_definition(
    name: str, version: int, db_path: str | None = None
) -> dict[str, Any] | None:
    query = "SELECT definition FROM note_types WHERE name = ? AND version = ?;"
    async with get_db_connection(db_path) as db:
        async with db.execute(query, (name, version)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row["definition"]) if row else None


async def upsert_type(
    name: str, version: int, definition: dict[str, Any], db_path: str | None = None
) -> None:
    query = """
        INSERT INTO note_types (name, version, definition)
        VALUES (?, ?, ?)
        ON CONFLICT(name, version) DO UPDATE SET definition = excluded.definition;
    """
    async with get_db_connection(db_path) as db:
        await db.execute(query, (name, version, json.dumps(definition)))
        await db.commit()
