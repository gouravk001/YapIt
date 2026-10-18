from __future__ import annotations

from typing import Any

from app.config.types_config import TypeDefinition
from app.pipeline.llm_json import generate_json
from app.pipeline.prompt_builder import extraction_prompt
from app.pipeline.schema_builder import build_extraction_schema
from app.providers.base import LLM


def extract(
    transcript: str,
    type_def: TypeDefinition,
    llm: LLM,
) -> dict[str, Any]:
    """Extract structured fields from the transcript for the given type.

    Unusable LLM output yields no fields, which the validator then reports as missing.
    """
    schema = build_extraction_schema(type_def)
    prompt = extraction_prompt(transcript, type_def)
    return generate_json(llm, prompt, schema, step="extract") or {}
