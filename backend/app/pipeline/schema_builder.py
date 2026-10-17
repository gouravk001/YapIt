from __future__ import annotations

import logging
from typing import Any

from app.config.types_config import TypeDefinition

logger = logging.getLogger(__name__)


def build_extraction_schema(type_def: TypeDefinition) -> dict[str, Any]:
    """Build a JSON Schema object for structured field extraction of a given note type."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in type_def.fields:
        prop: dict[str, Any] = {"description": field.description}

        if field.field_type == "enum" and field.allowed_values:
            prop["type"] = "string"
            prop["enum"] = field.allowed_values
        elif field.field_type in ("text", "date", "person", "money"):
            prop["type"] = "string"
        elif field.field_type == "number":
            prop["type"] = "number"
        elif field.field_type == "list":
            prop["type"] = "array"
            prop["items"] = {"type": "string"}
        else:
            prop["type"] = "string"

        properties[field.name] = prop
        if field.required:
            required.append(field.name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


def build_classification_schema(type_names: list[str]) -> dict[str, Any]:
    """Build a JSON Schema for the classification step that picks one type."""
    return {
        "type": "object",
        "properties": {
            "type_name": {
                "type": "string",
                "enum": type_names,
                "description": "The best-matching note type for the transcript.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0.0 and 1.0.",
            },
        },
        "required": ["type_name", "confidence"],
    }
