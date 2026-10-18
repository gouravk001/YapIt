from __future__ import annotations

from pydantic import BaseModel, PositiveFloat, PositiveInt


class DateChecks(BaseModel):
    max_years_ahead: PositiveInt
    max_days_past: int


class MoneyChecks(BaseModel):
    max_amount: dict[str, PositiveFloat]


class PlausibilityRules(BaseModel):
    date: DateChecks
    money: MoneyChecks
