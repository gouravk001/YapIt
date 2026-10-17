from __future__ import annotations

import logging
from typing import Any

from app.config.types_config import TypeDefinition
from app.resolvers.dates import resolve_date
from app.resolvers.money import resolve_money
from app.resolvers.people import resolve_person

logger = logging.getLogger(__name__)

_RESOLVER_MAP = {
    "date": resolve_date,
    "money": resolve_money,
    "person": resolve_person,
}


def resolve(
    fields: dict[str, Any],
    type_def: TypeDefinition,
    timezone: str,
    captured_at: str,
) -> dict[str, Any]:
    """Run field-type resolvers over the extracted fields to normalise values."""
    resolved: dict[str, Any] = {}

    for field_def in type_def.fields:
        raw = fields.get(field_def.name)
        if raw is None:
            continue

        resolver = _RESOLVER_MAP.get(field_def.field_type)
        if resolver is not None:
            try:
                resolved[field_def.name] = resolver(raw, timezone=timezone, captured_at=captured_at)
            except Exception as exc:
                logger.warning(
                    "Resolver for %r failed on value %r: %s — keeping raw value",
                    field_def.name,
                    raw,
                    exc,
                )
                resolved[field_def.name] = raw
        elif field_def.field_type == "list" and isinstance(raw, list):
            item_resolver = _RESOLVER_MAP.get(field_def.item_type or "")
            if item_resolver is not None:
                resolved[field_def.name] = [
                    _try_resolve(item_resolver, item, timezone, captured_at) for item in raw
                ]
            else:
                resolved[field_def.name] = raw
        else:
            resolved[field_def.name] = raw

    return resolved


def _try_resolve(resolver: Any, value: Any, timezone: str, captured_at: str) -> Any:
    try:
        return resolver(value, timezone=timezone, captured_at=captured_at)
    except Exception:
        return value
