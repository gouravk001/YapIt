from __future__ import annotations

import logging
from typing import Any

from app.config.types_config import TypeDefinition

logger = logging.getLogger(__name__)


def validate(
    fields: dict[str, Any],
    type_def: TypeDefinition,
) -> list[str]:
    """
    Validate fields against the type definition.

    Returns:
        List of field names that are required and missing, or invalid.
    """
    missing: list[str] = []

    for field_def in type_def.fields:
        val = fields.get(field_def.name)

        # Check required presence
        is_empty = val is None or (isinstance(val, (str, list)) and len(val) == 0)
        if field_def.required and is_empty:
            missing.append(field_def.name)
            continue

        if val is None:
            continue

        # Type-specific validation
        if field_def.field_type == "enum" and field_def.allowed_values:
            if str(val) not in field_def.allowed_values:
                missing.append(field_def.name)
                logger.debug("Enum %s has invalid value %r", field_def.name, val)

        elif field_def.field_type == "number":
            if not isinstance(val, (int, float)):
                missing.append(field_def.name)

        elif field_def.field_type == "money":
            if not isinstance(val, dict) or "amount" not in val or val.get("amount") is None:
                if field_def.required:
                    missing.append(field_def.name)

        elif field_def.field_type == "date":
            # For date, value is {"spoken": ..., "resolved": ...}
            if isinstance(val, dict):
                if field_def.required and not val.get("resolved"):
                    missing.append(field_def.name)
            elif field_def.required and not val:
                missing.append(field_def.name)

    return missing
