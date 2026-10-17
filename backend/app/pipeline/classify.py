from __future__ import annotations

import logging
from typing import Any

from app.config.types_config import TypeDefinition
from app.pipeline.prompt_builder import classification_prompt
from app.pipeline.schema_builder import build_classification_schema
from app.providers.base import LLM

logger = logging.getLogger(__name__)

_FALLBACK_TYPE = "general"


def classify(
    transcript: str,
    type_definitions: list[TypeDefinition],
    llm: LLM,
) -> TypeDefinition:
    """Classify transcript into a TypeDefinition using the LLM."""
    type_names = [td.name for td in type_definitions]
    schema = build_classification_schema(type_names)
    prompt = classification_prompt(transcript, type_definitions)

    result: Any = llm.generate(prompt, json_schema=schema)

    if isinstance(result, dict):
        chosen_name = result.get("type_name", _FALLBACK_TYPE)
    else:
        logger.warning("Classification returned non-dict: %s — falling back to general", result)
        chosen_name = _FALLBACK_TYPE

    matched = next((td for td in type_definitions if td.name == chosen_name), None)
    if matched is None:
        logger.warning("LLM chose unknown type %r — falling back to general", chosen_name)
        matched = next(td for td in type_definitions if td.name == _FALLBACK_TYPE)

    logger.debug("Classified transcript as type=%r", matched.name)
    return matched
