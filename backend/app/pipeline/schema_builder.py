from __future__ import annotations

from typing import Any

from app.config.types_config import TypeDefinition


def build_extraction_schema(type_def: TypeDefinition) -> dict[str, Any]:
    """Build a JSON Schema object for structured field extraction of a given note type."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in type_def.fields:
        prop: dict[str, Any] = {"description": field.description}

        if field.field_type == "enum" and field.allowed_values:
            prop["type"] = "string"
            prop["enum"] = field.llm_choices()
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


NOTE_KIND = "note"
NOT_A_NOTE_KINDS = (
    "greeting_or_test",
    "question_or_command",
    "background_media",
    "lyrics_or_gibberish",
)


def build_classification_schema(type_names: list[str]) -> dict[str, Any]:
    """Build a JSON Schema that names the kind of recording first, then picks one note type."""
    return {
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "enum": [NOTE_KIND, *NOT_A_NOTE_KINDS],
                "description": "What kind of recording this is.",
            },
            "type_name": {
                "type": "string",
                "enum": type_names,
                "description": "The best-matching note type for the transcript.",
            },
        },
        "required": ["kind", "type_name"],
    }


def build_refine_schema(type_def: TypeDefinition) -> dict[str, Any]:
    """Extraction schema with every field required, plus a one-line summary.

    A restatement comes first because the model writes properties in order, and saying the
    note in plain words before filling fields makes small models get directions right.
    """
    extraction = build_extraction_schema(type_def)
    properties = {
        "restatement": {
            "type": "string",
            "description": "One plain sentence: who does what and when, from the speaker's view.",
        },
        **extraction["properties"],
        "summary": {
            "type": "string",
            "description": "One scannable line of at most 10 words.",
        },
    }
    return {"type": "object", "properties": properties, "required": [*properties.keys()]}


PLAUSIBLE_VERDICT = "ordinary"


def build_plausibility_schema() -> dict[str, Any]:
    """Build a JSON Schema for a verdict on whether a note can be right, with a reason."""
    return {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": [PLAUSIBLE_VERDICT, "unlikely"]},
            "reason": {"type": "string", "description": "One short sentence, or empty."},
        },
        "required": ["verdict", "reason"],
    }
