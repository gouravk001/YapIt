from __future__ import annotations

from fastapi import APIRouter
from fastapi import Request as FastAPIRequest

from app.config.types_config import TypeDefinition

router = APIRouter(prefix="/types", tags=["types"])


@router.get("", response_model=list[TypeDefinition])
async def list_types(request: FastAPIRequest) -> list[TypeDefinition]:
    """Return all loaded note type definitions."""
    return request.app.state.type_definitions
