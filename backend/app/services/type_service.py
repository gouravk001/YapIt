from __future__ import annotations

from app.config.types_config import TypeDefinition
from app.errors import TypeVersionConflictError
from app.storage import queries


async def seed_types(type_definitions: list[TypeDefinition], db_path: str) -> None:
    """Store each type definition under its (name, version), keeping earlier versions.

    Description and example edits are stored in place because they only steer the LLM.
    Field edits change the shape of saved notes, so they require a new version number.
    """
    for type_def in type_definitions:
        definition = type_def.model_dump()
        stored = await queries.get_type_definition(type_def.name, type_def.version, db_path)
        if stored is not None and stored["fields"] != definition["fields"]:
            raise TypeVersionConflictError(
                f"The fields of type {type_def.name!r} changed but its version is still "
                f"{type_def.version}. Bump the version in types.yaml so existing notes keep "
                "their original definition."
            )
        await queries.upsert_type(type_def.name, type_def.version, definition, db_path=db_path)
