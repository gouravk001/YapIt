from __future__ import annotations

import aiosqlite
import pytest

from app.config.types_config import FieldDefinition, TypeDefinition
from app.errors import TypeVersionConflictError
from app.services.type_service import seed_types
from app.storage.database import init_db
from app.storage.queries import get_type_definition


def _type(
    version: int,
    field_names: list[str],
    description: str = "A test type.",
    field_note: str = "",
) -> TypeDefinition:
    fields = [
        FieldDefinition(name=n, field_type="text", required=False, description=n + field_note)
        for n in field_names
    ]
    return TypeDefinition(name="todo", version=version, description=description, fields=fields)


@pytest.fixture
async def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


async def test_new_version_keeps_the_old_one(db_path):
    await seed_types([_type(1, ["task"])], db_path)
    await seed_types([_type(2, ["task", "owner"])], db_path)

    v1 = await get_type_definition("todo", 1, db_path)
    v2 = await get_type_definition("todo", 2, db_path)
    assert [f["name"] for f in v1["fields"]] == ["task"]
    assert [f["name"] for f in v2["fields"]] == ["task", "owner"]


async def test_description_change_updates_in_place(db_path):
    await seed_types([_type(1, ["task"])], db_path)
    await seed_types([_type(1, ["task"], description="Reworded.")], db_path)

    stored = await get_type_definition("todo", 1, db_path)
    assert stored["description"] == "Reworded."


async def test_field_description_change_needs_no_version_bump(db_path):
    await seed_types([_type(1, ["task"])], db_path)
    await seed_types([_type(1, ["task"], field_note=" (clearer wording)")], db_path)

    stored = await get_type_definition("todo", 1, db_path)
    assert stored["fields"][0]["description"] == "task (clearer wording)"


async def test_field_change_without_version_bump_is_rejected(db_path):
    await seed_types([_type(1, ["task"])], db_path)
    with pytest.raises(TypeVersionConflictError, match="Bump the version"):
        await seed_types([_type(1, ["task", "owner"])], db_path)


async def test_unversioned_table_is_migrated(tmp_path):
    path = str(tmp_path / "old.db")
    async with aiosqlite.connect(path) as db:
        await db.execute(
            "CREATE TABLE note_types (name TEXT PRIMARY KEY, version INTEGER, definition TEXT);"
        )
        await db.commit()

    await init_db(path)
    await seed_types([_type(1, ["task"]), _type(2, ["task", "owner"])], path)
    assert await get_type_definition("todo", 1, path) is not None
    assert await get_type_definition("todo", 2, path) is not None
