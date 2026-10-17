from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    name: str
    field_type: Literal["text", "number", "money", "date", "person", "enum", "list"]
    required: bool
    description: str
    allowed_values: list[str] | None = None
    item_type: str | None = None


class TypeExample(BaseModel):
    transcript: str
    expected_fields: dict[str, Any]


class TypeDefinition(BaseModel):
    name: str
    version: int
    description: str
    fields: list[FieldDefinition]
    examples: list[TypeExample] = Field(default_factory=list)
