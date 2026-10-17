from __future__ import annotations

from typing import Any


def resolve_person(raw: Any, **kwargs: Any) -> str | list[str] | None:
    """Normalize names: strip whitespace, title-case, deduplicate lists."""
    if raw is None:
        return None

    if isinstance(raw, list):
        seen: set[str] = set()
        deduped: list[str] = []
        for item in raw:
            norm = _normalize_single_name(str(item))
            if norm and norm.lower() not in seen:
                seen.add(norm.lower())
                deduped.append(norm)
        return deduped

    text = str(raw).strip()
    if not text:
        return None

    # If comma-separated in a single string, normalize each
    if "," in text and kwargs.get("is_list", False):
        parts = [_normalize_single_name(p) for p in text.split(",")]
        return [p for p in parts if p]

    return _normalize_single_name(text)


def _normalize_single_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    # Capitalize each word properly
    return cleaned.title()

