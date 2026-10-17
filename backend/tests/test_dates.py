from __future__ import annotations

from app.resolvers.dates import resolve_date


def test_resolve_today_and_tomorrow():
    anchor = "2026-10-17T12:00:00"
    res_today = resolve_date("today", captured_at=anchor)
    assert res_today["resolved"] == "2026-10-17"

    res_tomorrow = resolve_date("tomorrow", captured_at=anchor)
    assert res_tomorrow["resolved"] == "2026-10-18"

    res_day_after = resolve_date("day after tomorrow", captured_at=anchor)
    assert res_day_after["resolved"] == "2026-10-19"


def test_resolve_bare_weekday():
    # 2026-10-17 is a Saturday (weekday 5)
    # Bare "Monday" should resolve to upcoming Monday (2026-10-19)
    anchor = "2026-10-17T10:00:00"
    res = resolve_date("Monday", captured_at=anchor)
    assert res["resolved"] == "2026-10-19"

    # Bare "Saturday" when today is Saturday should be next Saturday (+7 days, 2026-10-24)
    res_sat = resolve_date("Saturday", captured_at=anchor)
    assert res_sat["resolved"] == "2026-10-24"


def test_resolve_next_weekday():
    # 2026-10-17 is a Saturday
    # "next Monday" should resolve to Monday of the next week (2026-10-26)
    anchor = "2026-10-17T10:00:00"
    res = resolve_date("next Monday", captured_at=anchor)
    assert res["resolved"] == "2026-10-26"

    # "next Friday"
    res_fri = resolve_date("next Friday", captured_at=anchor)
    assert res_fri["resolved"] == "2026-10-30"


def test_resolve_in_n_days_and_weeks():
    anchor = "2026-10-17T10:00:00"
    res_days = resolve_date("in 3 days", captured_at=anchor)
    assert res_days["resolved"] == "2026-10-20"

    res_word_days = resolve_date("in five days", captured_at=anchor)
    assert res_word_days["resolved"] == "2026-10-22"

    res_weeks = resolve_date("in 2 weeks", captured_at=anchor)
    assert res_weeks["resolved"] == "2026-10-31"


def test_resolve_end_of_month():
    anchor = "2026-10-17T10:00:00"
    res = resolve_date("end of the month", captured_at=anchor)
    assert res["resolved"] == "2026-10-31"


def test_resolve_ordinal():
    anchor = "2026-10-17T10:00:00"
    res = resolve_date("the 25th", captured_at=anchor)
    assert res["resolved"] == "2026-10-25"

    # 10th is past today (17th), so rolls to next month (November)
    res_past = resolve_date("the 10th", captured_at=anchor)
    assert res_past["resolved"] == "2026-11-10"


def test_unresolvable_date():
    anchor = "2026-10-17T10:00:00"
    res = resolve_date("sometime around springtime maybe", captured_at=anchor)
    assert res["resolved"] is None
    assert res["spoken"] == "sometime around springtime maybe"
