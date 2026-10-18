from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.config.checks_config import PlausibilityRules
from app.config.types_config import FieldDefinition, TypeDefinition
from app.resolvers.dates import capture_day
from app.resolvers.money import format_money

_DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Concern:
    """Something about a draft the user should double-check before saving."""

    field: str | None
    message: str


def _label(field: FieldDefinition) -> str:
    return field.name.replace("_", " ").capitalize()


def _check_date(
    field: FieldDefinition, value: Any, today: date, rules: PlausibilityRules
) -> Concern | None:
    if not isinstance(value, dict):
        return None
    if not value.get("resolved"):
        spoken = value.get("spoken")
        return (
            Concern(
                field.name, f"Couldn't work out a date from “{spoken}”. Pick one or leave it empty."
            )
            if spoken
            else None
        )
    day = date.fromisoformat(value["resolved"])
    shown = day.strftime("%a %-d %b %Y")
    days_ahead = (day - today).days
    years_ahead = days_ahead / _DAYS_PER_YEAR
    if years_ahead > rules.date.max_years_ahead:
        return Concern(
            field.name, f"{_label(field)} is about {round(years_ahead)} years away ({shown})."
        )
    if -days_ahead > rules.date.max_days_past:
        return Concern(field.name, f"{_label(field)} ({shown}) is already in the past.")
    return None


def _check_money(field: FieldDefinition, value: Any, rules: PlausibilityRules) -> Concern | None:
    if not isinstance(value, dict) or value.get("amount") is None:
        return None
    amount = float(value["amount"])
    limit = rules.money.max_amount.get(value.get("currency", "INR"))
    if amount <= 0:
        return Concern(field.name, f"{_label(field)} is {format_money(value)}.")
    if limit is not None and amount > limit:
        return Concern(field.name, f"{format_money(value)} is unusually large for a note.")
    return None


def find_concerns(
    fields: dict[str, Any],
    type_def: TypeDefinition,
    rules: PlausibilityRules,
    captured_at: str,
    timezone: str,
) -> list[Concern]:
    """Deterministic checks for values that are possible but unlikely to be what was meant."""
    today = capture_day(captured_at, timezone)
    concerns: list[Concern] = []
    for field in type_def.fields:
        value = fields.get(field.name)
        if field.field_type == "date":
            concern = _check_date(field, value, today, rules)
        elif field.field_type == "money":
            concern = _check_money(field, value, rules)
        else:
            concern = None
        if concern is not None:
            concerns.append(concern)
    return concerns
