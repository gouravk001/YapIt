from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


def flatten_fields_text(fields_obj: Any) -> str:
    """Flatten dictionary values into space-separated string for FTS indexing."""
    if not isinstance(fields_obj, dict):
        return str(fields_obj or "")
    parts: list[str] = []
    for v in fields_obj.values():
        if isinstance(v, dict):
            parts.extend(str(sub_v) for sub_v in v.values() if sub_v is not None)
        elif isinstance(v, list):
            parts.extend(str(item) for item in v if item is not None)
        elif v is not None:
            parts.append(str(v))
    return " ".join(parts)


@asynccontextmanager
async def get_db_connection(db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db


async def init_db(db_path: str) -> None:
    logger.info("Initializing database at %s", db_path)

    async with get_db_connection(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                timezone TEXT NOT NULL,
                transcript TEXT NOT NULL,
                type_name TEXT NOT NULL,
                type_version INTEGER NOT NULL,
                summary TEXT NOT NULL,
                fields TEXT NOT NULL,
                status TEXT NOT NULL,
                missing_fields TEXT NOT NULL
            );
            """)

        await _drop_unversioned_note_types(db)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS note_types (
                name TEXT NOT NULL,
                version INTEGER NOT NULL,
                definition TEXT NOT NULL,
                PRIMARY KEY (name, version)
            );
            """)

        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                id UNINDEXED,
                summary,
                transcript,
                fields,
                content=notes,
                content_rowid=rowid
            );
            """)

        # Triggers to keep FTS index in sync with notes table
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, id, summary, transcript, fields)
                VALUES (new.rowid, new.id, new.summary, new.transcript, new.fields);
            END;
            """)

        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, id, summary, transcript, fields)
                VALUES ('delete', old.rowid, old.id, old.summary, old.transcript, old.fields);
            END;
            """)

        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, id, summary, transcript, fields)
                VALUES ('delete', old.rowid, old.id, old.summary, old.transcript, old.fields);
                INSERT INTO notes_fts(rowid, id, summary, transcript, fields)
                VALUES (new.rowid, new.id, new.summary, new.transcript, new.fields);
            END;
            """)

        await db.commit()
    logger.info("Database initialized successfully")


async def _drop_unversioned_note_types(db: aiosqlite.Connection) -> None:
    """Drop a note_types table from before versioning, where name alone was the key.

    It only ever held rows seeded from types.yaml, so startup seeding rebuilds it.
    """
    async with db.execute("PRAGMA table_info(note_types);") as cursor:
        key_columns = [row["name"] for row in await cursor.fetchall() if row["pk"]]
    if key_columns == ["name"]:
        logger.info("Migrating note_types to versioned schema")
        await db.execute("DROP TABLE note_types;")
