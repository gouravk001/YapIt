from __future__ import annotations

from app.config.types_config import TypeDefinition


def classification_prompt(transcript: str, type_definitions: list[TypeDefinition]) -> str:
    """Build the prompt for the classification step."""
    type_descriptions = "\n".join(
        f"- **{td.name}**: {td.description.strip()}" for td in type_definitions
    )
    return (
        "You are a note classification assistant. Given a transcript, select the single best "
        "matching note type from the list below.\n\n"
        "## Available note types\n"
        f"{type_descriptions}\n\n"
        "## Transcript\n"
        f"{transcript}\n\n"
        "Respond with JSON containing 'type_name' and a 'confidence' score (0.0–1.0)."
    )


def extraction_prompt(transcript: str, type_def: TypeDefinition) -> str:
    """Build the prompt for the field extraction step."""
    field_lines = "\n".join(
        f"- {f.name} ({f.field_type}, {'required' if f.required else 'optional'}): {f.description}"
        + (f" Allowed: {f.allowed_values}" if f.allowed_values else "")
        for f in type_def.fields
    )

    examples_block = ""
    if type_def.examples:
        example_parts = []
        for ex in type_def.examples[:2]:
            example_parts.append(f'  Transcript: "{ex.transcript}"\n  Fields: {ex.expected_fields}')
        examples_block = "\n\n## Examples\n" + "\n\n".join(example_parts)

    return (
        f"You are extracting structured fields from a voice note classified as **{type_def.name}**.\n\n"
        "## Fields to extract\n"
        f"{field_lines}"
        f"{examples_block}\n\n"
        "## Transcript\n"
        f"{transcript}\n\n"
        "Extract all fields you can from the transcript and respond with valid JSON."
    )


def summary_prompt(transcript: str, type_name: str, fields: dict) -> str:
    """Build the prompt for generating a human-readable one-line summary."""
    return (
        f"Write a concise one-sentence summary (max 15 words) for a '{type_name}' note.\n\n"
        f"Transcript: {transcript}\nExtracted fields: {fields}\n\n"
        "Respond with just the summary sentence, no quotes, no punctuation at the end."
    )
