from __future__ import annotations

from app.config.loader import load_checks, load_types
from app.pipeline.plausibility import Concern, find_concerns

TYPES = {t.name: t for t in load_types()}
RULES = load_checks()
CAPTURED_AT = "2026-10-17T10:00:00+05:30"
TZ = "Asia/Kolkata"


def _concerns(type_name, fields):
    return find_concerns(fields, TYPES[type_name], RULES, CAPTURED_AT, TZ)


def _date(resolved):
    return {"spoken": "x", "resolved": resolved}


def test_ordinary_note_has_no_concerns():
    fields = {
        "person": "Ravi",
        "direction": "they_owe_me",
        "amount": {"amount": 150000.0, "currency": "INR"},
        "due_date": _date("2026-10-30"),
    }
    assert _concerns("payment", fields) == []


def test_date_decades_away_is_flagged():
    concerns = _concerns("event", {"title": "Wedding", "date": _date("2066-10-17")})
    assert concerns == [Concern("date", "Date is about 40 years away (Sun 17 Oct 2066).")]


def test_date_within_limit_is_fine():
    assert _concerns("event", {"title": "Trip", "date": _date("2028-06-01")}) == []


def test_past_due_date_is_flagged():
    concerns = _concerns(
        "promise", {"person": "Mom", "commitment": "Call", "due_date": _date("2026-10-01")}
    )
    assert concerns == [Concern("due_date", "Due date (Thu 1 Oct 2026) is already in the past.")]


def test_yesterday_is_within_tolerance():
    assert _concerns("event", {"title": "Dinner", "date": _date("2026-10-16")}) == []


def test_huge_and_zero_amounts_are_flagged():
    huge = _concerns("payment", {"amount": {"amount": 5e9, "currency": "INR"}})
    zero = _concerns("payment", {"amount": {"amount": 0.0, "currency": "USD"}})
    assert huge == [Concern("amount", "₹5,00,00,00,000 is unusually large for a note.")]
    assert zero == [Concern("amount", "Amount is $0.")]


def test_unresolvable_spoken_date_is_flagged():
    fields = {"title": "Party", "date": {"spoken": "the 30th of February", "resolved": None}}
    assert _concerns("event", fields) == [
        Concern(
            "date",
            "Couldn't work out a date from “the 30th of February”. Pick one or leave it empty.",
        )
    ]
