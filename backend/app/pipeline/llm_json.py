from __future__ import annotations

import logging
from typing import Any

from app.providers.base import LLM

logger = logging.getLogger(__name__)

# One retry: schema-constrained output is rarely malformed, and a second failure is not
# worth more latency.
_MAX_ATTEMPTS = 2


def generate_json(
    llm: LLM, prompt: str, schema: dict[str, Any], step: str
) -> dict[str, Any] | None:
    """Ask the LLM for schema-constrained JSON, retrying once if the output is not an object."""
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        result = llm.generate(prompt, json_schema=schema)
        if isinstance(result, dict):
            return result
        logger.warning("%s returned malformed output (attempt %d): %r", step, attempt, result)
    return None
