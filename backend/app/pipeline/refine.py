from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.config.types_config import FieldDefinition, TypeDefinition
from app.pipeline.llm_json import generate_json
from app.pipeline.prompt_builder import refine_prompt
from app.pipeline.schema_builder import build_refine_schema
from app.providers.base import LLM
from app.resolvers.money import format_money

logger = logging.getLogger(__name__)

_FALLBACK_SUMMARY_CHARS = 70


@dataclass(frozen=True)
class RefinedDraft:
    fields: dict[str, Any]
    summary: str


def _prompt_value(field: FieldDefinition, value: Any) -> Any:
    """Turn resolved values back into the spoken-style strings the LLM reads and writes."""
    if field.field_type == "enum":
        return field.to_llm_value(value)
    if isinstance(value, dict) and "amount" in value:
        return format_money(value)
    if isinstance(value, dict) and "resolved" in value:
        return value.get("spoken") or value.get("resolved") or ""
    return value


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _merge(
    current: dict[str, Any], refined: dict[str, Any], type_def: TypeDefinition
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for field in type_def.fields:
        before = current.get(field.name)
        after = refined.get(field.name)
        # Refining may clear invented optional values, but a required value it drops is more
        # likely a refine mistake than a correction, so the user gets to judge it in review.
        if _is_empty(after) and field.required and not _is_empty(before):
            merged[field.name] = before
        else:
            merged[field.name] = after
    return merged


def fallback_summary(transcript: str) -> str:
    clean = " ".join(transcript.split())
    if len(clean) <= _FALLBACK_SUMMARY_CHARS:
        return clean
    return clean[:_FALLBACK_SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"


def refine(
    transcript: str,
    type_def: TypeDefinition,
    resolved_fields: dict[str, Any],
    llm: LLM,
) -> RefinedDraft | None:
    """Have the LLM check the draft against the transcript, tidy it, and write the summary.

    Returns fields in spoken form, to be resolved again, or None if the LLM output was unusable.
    """
    current = {f.name: _prompt_value(f, resolved_fields.get(f.name, "")) for f in type_def.fields}
    prompt = refine_prompt(transcript, type_def, current)
    result = generate_json(llm, prompt, build_refine_schema(type_def), step="refine")
    if result is None:
        return None

    summary = " ".join(str(result.get("summary") or "").split()).rstrip(".")
    return RefinedDraft(
        fields=_merge(current, result, type_def),
        summary=summary or fallback_summary(transcript),
    )
