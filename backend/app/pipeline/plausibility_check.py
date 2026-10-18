from __future__ import annotations

from datetime import date

from app.pipeline.llm_json import generate_json
from app.pipeline.prompt_builder import plausibility_prompt
from app.pipeline.schema_builder import PLAUSIBLE_VERDICT, build_plausibility_schema
from app.providers.base import LLM


def check_plausibility(transcript: str, today: date, llm: LLM) -> str | None:
    """Ask the LLM whether the note contains something that cannot be right.

    Returns a one-sentence reason to show the user, or None for an ordinary note. Unusable
    output counts as ordinary: a missed warning is better than a false alarm.
    """
    prompt = plausibility_prompt(transcript, today.strftime("%A %-d %B %Y"))
    result = generate_json(llm, prompt, build_plausibility_schema(), step="plausibility") or {}
    if result.get("verdict", PLAUSIBLE_VERDICT) == PLAUSIBLE_VERDICT:
        return None
    reason = " ".join(str(result.get("reason") or "").split())
    return reason or "Something in this note looks unlikely. Please double-check it."
