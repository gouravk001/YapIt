from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config.types_config import TypeDefinition
from app.pipeline.llm_json import generate_json
from app.pipeline.prompt_builder import classification_prompt
from app.pipeline.schema_builder import NOT_A_NOTE_KINDS, build_classification_schema
from app.providers.base import LLM

logger = logging.getLogger(__name__)

_FALLBACK_TYPE = "general"


@dataclass(frozen=True)
class Classification:
    is_note: bool
    type_def: TypeDefinition


def classify(
    transcript: str,
    type_definitions: list[TypeDefinition],
    llm: LLM,
) -> Classification:
    """Decide whether the transcript is a note and, if so, which type fits it."""
    schema = build_classification_schema([td.name for td in type_definitions])
    prompt = classification_prompt(transcript, type_definitions)
    result = generate_json(llm, prompt, schema, step="classify") or {}

    by_name = {td.name: td for td in type_definitions}
    chosen = by_name.get(result.get("type_name", ""))
    if chosen is None:
        logger.warning("Classifier chose %r — falling back to general", result.get("type_name"))
        chosen = by_name[_FALLBACK_TYPE]

    # A malformed answer must not discard the user's note, so only a named non-note kind rejects.
    return Classification(is_note=result.get("kind") not in NOT_A_NOTE_KINDS, type_def=chosen)
