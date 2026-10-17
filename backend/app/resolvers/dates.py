from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
}

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _parse_anchor(captured_at: str | None, timezone: str) -> datetime:
    tz = ZoneInfo("UTC")
    try:
        if timezone:
            tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("UTC")

    if captured_at:
        try:
            # Handle ISO format
            clean_ts = captured_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            else:
                dt = dt.astimezone(tz)
            return dt
        except Exception:
            pass

    return datetime.now(tz)


def resolve_date(
    raw: Any,
    timezone: str = "UTC",
    captured_at: str | None = None,
    **kwargs: Any,
) -> dict[str, str | None]:
    """
    Deterministically resolve spoken date phrases into YYYY-MM-DD.

    Returns:
        {"spoken": original_phrase, "resolved": "YYYY-MM-DD" | None}

    Weekday interpretation rules:
    - Bare weekday (e.g. 'Friday'): The closest upcoming occurrence from tomorrow
      (1 to 7 days in the future). If anchor is Friday, 'Friday' means next Friday (7 days).
    - 'Next <weekday>' (e.g. 'next Friday'): The occurrence in the following week
      (7 to 13 days in the future, skipping the immediately upcoming occurrence).
    """
    if isinstance(raw, dict):
        spoken = str(raw.get("spoken") or raw.get("raw") or raw.get("resolved") or "")
    else:
        spoken = str(raw or "").strip()

    if not spoken:
        return {"spoken": "", "resolved": None}

    anchor_dt = _parse_anchor(captured_at, timezone)
    anchor_date = anchor_dt.date()

    resolved_date = _resolve_phrase(spoken, anchor_date)

    return {
        "spoken": spoken,
        "resolved": resolved_date.isoformat() if resolved_date else None,
    }


def _resolve_phrase(phrase: str, anchor: date) -> date | None:
    text = phrase.strip().lower()

    # Direct keywords
    if text == "today":
        return anchor
    if text == "tomorrow":
        return anchor + timedelta(days=1)
    if text in ("day after tomorrow", "the day after tomorrow"):
        return anchor + timedelta(days=2)

    # End of month
    if text in ("end of month", "end of the month", "month end"):
        last_day = calendar.monthrange(anchor.year, anchor.month)[1]
        return date(anchor.year, anchor.month, last_day)

    # Next week (defaults to Monday of next week)
    if text == "next week":
        days_ahead = (0 - anchor.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return anchor + timedelta(days=days_ahead)

    # Weekday parsing: 'next <weekday>' vs bare '<weekday>'
    for day_name, day_idx in WEEKDAYS.items():
        if f"next {day_name}" in text:
            # Occurrence in the following week (7 to 13 days ahead)
            days_ahead = (day_idx - anchor.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            else:
                days_ahead += 7
            return anchor + timedelta(days=days_ahead)

        # Bare weekday (e.g. 'this Friday' or 'on Friday' or 'Friday')
        if re.search(rf"\b(this\s+)?{day_name}\b", text):
            days_ahead = (day_idx - anchor.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # Always next upcoming, not today
            return anchor + timedelta(days=days_ahead)

    # In N days / weeks
    match = re.search(r"in\s+(\d+|[a-z]+)\s+(day|days|week|weeks)", text)
    if match:
        num_str = match.group(1)
        unit = match.group(2)
        count = int(num_str) if num_str.isdigit() else NUMBER_WORDS.get(num_str, 0)
        if count > 0:
            if "week" in unit:
                return anchor + timedelta(weeks=count)
            return anchor + timedelta(days=count)

    # Ordinal dates: e.g. "the 25th", "25th", "1st of next month"
    ord_match = re.search(r"\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\b", text)
    if ord_match:
        target_day = int(ord_match.group(1))
        month = anchor.month
        year = anchor.year
        if "next month" in text or target_day < anchor.day:
            month += 1
            if month > 12:
                month = 1
                year += 1
        max_days = calendar.monthrange(year, month)[1]
        target_day = min(target_day, max_days)
        return date(year, month, target_day)

    # Standard ISO format: YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    # DD/MM/YYYY or DD-MM-YYYY
    dmy_match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
    if dmy_match:
        try:
            return date(int(dmy_match.group(3)), int(dmy_match.group(2)), int(dmy_match.group(1)))
        except ValueError:
            pass

    return None

