from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

NUMBER_WORDS = {
    "a": 1,
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
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

SATURDAY = 5

MONTHS = {
    name: number
    for number, names in enumerate(
        [
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ],
        start=1,
    )
    for name in names
}
_MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")"
_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_YEAR = r"(?:,?\s+(\d{4}))?"
_LEAP_YEAR_CYCLE = 4

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


def capture_day(captured_at: str | None, timezone: str) -> date:
    """The calendar day the note was captured on, in the capture timezone."""
    return _parse_anchor(captured_at, timezone).date()


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
    - 'This weekend' / 'the weekend': the coming Saturday, or today if it is already the weekend.
    - 'Next weekend': the Saturday after that, following the same rule as 'next <weekday>'.
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


def _add_months(anchor: date, months: int) -> date:
    """Same day-of-month N months later, clamped to the month's last day (31 Jan + 1 = 28 Feb)."""
    month_index = anchor.month - 1 + months
    year, month = anchor.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(anchor.day, calendar.monthrange(year, month)[1]))


def _resolve_named_month(text: str, anchor: date) -> date | bool | None:
    """Dates with a month name: "3 March", "the 30th of February", "March 3rd 2027", "December 2028".

    Returns None when no month is named, False when the date does not exist (30 February), so
    later patterns do not reinterpret the day number against the current month.
    """
    day_first = re.search(rf"\b{_DAY}\s+(?:of\s+)?{_MONTH}\b{_YEAR}", text)
    month_first = re.search(rf"\b{_MONTH}\s+{_DAY}\b(?!\d){_YEAR}", text)
    month_year = re.search(rf"\b{_MONTH}\s+(\d{{4}})\b", text)
    if day_first:
        day, month, year = day_first.group(1), day_first.group(2), day_first.group(3)
    elif month_year:
        day, month, year = "1", month_year.group(1), month_year.group(2)
    elif month_first:
        day, month, year = month_first.group(2), month_first.group(1), month_first.group(3)
    else:
        return None

    month_number = MONTHS[month]
    if year:
        try:
            return date(int(year), month_number, int(day))
        except ValueError:
            return False
    # Without a year, take the next time that day comes round (29 Feb may be years away).
    for candidate_year in range(anchor.year, anchor.year + _LEAP_YEAR_CYCLE + 1):
        try:
            target = date(candidate_year, month_number, int(day))
        except ValueError:
            continue
        if target >= anchor:
            return target
    return False


def _resolve_phrase(phrase: str, anchor: date) -> date | None:
    text = phrase.strip().lower()

    # Direct keywords, also inside longer phrases like "by tomorrow evening"
    if re.search(r"\byesterday\b", text):
        return anchor - timedelta(days=1)
    if re.search(r"\bday after tomorrow\b", text):
        return anchor + timedelta(days=2)
    if re.search(r"\btomorrow\b", text):
        return anchor + timedelta(days=1)
    if re.search(r"\b(today|tonight|this (morning|afternoon|evening))\b", text):
        return anchor

    # End of month
    if re.search(r"\b(end of (the |this )?month|month end)\b", text):
        last_day = calendar.monthrange(anchor.year, anchor.month)[1]
        return date(anchor.year, anchor.month, last_day)

    if re.search(r"\bnext weekend\b", text):
        days_ahead = (SATURDAY - anchor.weekday()) % 7
        return anchor + timedelta(days=days_ahead + 7 if days_ahead else 7)
    if re.search(r"\bweekend\b", text):
        if anchor.weekday() >= SATURDAY:
            return anchor
        return anchor + timedelta(days=SATURDAY - anchor.weekday())

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

    # (In / after) N days, weeks, months or years
    match = re.search(r"\b(\d+|[a-z]+)\s+(day|week|month|year)s?\b", text)
    if match:
        num_str = match.group(1)
        unit = match.group(2)
        count = int(num_str) if num_str.isdigit() else NUMBER_WORDS.get(num_str, 0)
        if count > 0:
            if unit == "year":
                return _add_months(anchor, 12 * count)
            if unit == "month":
                return _add_months(anchor, count)
            if unit == "week":
                return anchor + timedelta(weeks=count)
            return anchor + timedelta(days=count)

    named = _resolve_named_month(text, anchor)
    if named is not None:
        return named or None

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
