from __future__ import annotations

import logging
from typing import Any

from app.config.types_config import TypeDefinition
from app.pipeline.prompt_builder import extraction_prompt
from app.pipeline.schema_builder import build_extraction_schema
from app.providers.base import LLM

logger = logging.getLogger(__name__)


def extract(
    transcript: str,
    type_def: TypeDefinition,
    llm: LLM,
) -> dict[str, Any]:
    """Extract structured fields from the transcript for the given type."""
    schema = build_extraction_schema(type_def)
    prompt = extraction_prompt(transcript, type_def)

    result: Any = llm.generate(prompt, json_schema=schema)

    if isinstance(result, dict):
        return result

    logger.warning(
        "Extraction returned non-dict for type=%r — returning empty fields", type_def.name
    )
    return {}
