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


def test_resolve_weekend_phrases():
    wednesday = "2026-10-14T10:00:00"
    saturday = "2026-10-17T10:00:00"
    sunday = "2026-10-18T10:00:00"

    assert resolve_date("this weekend", captured_at=wednesday)["resolved"] == "2026-10-17"
    assert resolve_date("over the weekend", captured_at=wednesday)["resolved"] == "2026-10-17"
    assert resolve_date("this weekend", captured_at=saturday)["resolved"] == "2026-10-17"
    assert resolve_date("this weekend", captured_at=sunday)["resolved"] == "2026-10-18"
    assert resolve_date("next weekend", captured_at=wednesday)["resolved"] == "2026-10-24"
    assert resolve_date("next weekend", captured_at=saturday)["resolved"] == "2026-10-24"


def test_resolve_keywords_inside_longer_phrases():
    anchor = "2026-10-17T10:00:00"
    assert resolve_date("tonight", captured_at=anchor)["resolved"] == "2026-10-17"
    assert resolve_date("by tonight", captured_at=anchor)["resolved"] == "2026-10-17"
    assert resolve_date("this evening", captured_at=anchor)["resolved"] == "2026-10-17"
    assert resolve_date("tomorrow evening", captured_at=anchor)["resolved"] == "2026-10-18"
    assert resolve_date("by tomorrow", captured_at=anchor)["resolved"] == "2026-10-18"
    assert resolve_date("the day after tomorrow", captured_at=anchor)["resolved"] == "2026-10-19"


def test_resolve_durations_without_in():
    anchor = "2026-10-17T10:00:00"
    assert resolve_date("2 weeks", captured_at=anchor)["resolved"] == "2026-10-31"
    assert resolve_date("in a week", captured_at=anchor)["resolved"] == "2026-10-24"
    assert resolve_date("within three days", captured_at=anchor)["resolved"] == "2026-10-20"


def test_resolve_end_of_month_inside_longer_phrase():
    anchor = "2026-10-17T10:00:00"
    for phrase in ("the end of the month", "by end of this month", "month end"):
        assert resolve_date(phrase, captured_at=anchor)["resolved"] == "2026-10-31"


def test_resolve_months_and_years():
    anchor = "2026-10-17T10:00:00"
    assert resolve_date("in 3 months", captured_at=anchor)["resolved"] == "2027-01-17"
    assert resolve_date("after 40 years", captured_at=anchor)["resolved"] == "2066-10-17"
    assert resolve_date("in a year", captured_at=anchor)["resolved"] == "2027-10-17"
    assert resolve_date("in forty years", captured_at=anchor)["resolved"] == "2066-10-17"
    assert (
        resolve_date("in one month", captured_at="2027-01-31T10:00:00")["resolved"] == "2027-02-28"
    )


def test_resolve_named_months():
    anchor = "2026-10-17T10:00:00"
    assert resolve_date("3 March", captured_at=anchor)["resolved"] == "2027-03-03"
    assert resolve_date("on the 25th of December", captured_at=anchor)["resolved"] == "2026-12-25"
    assert resolve_date("Nov 2nd", captured_at=anchor)["resolved"] == "2026-11-02"
    assert resolve_date("March 3rd 2028", captured_at=anchor)["resolved"] == "2028-03-03"
    assert resolve_date("December 2028", captured_at=anchor)["resolved"] == "2028-12-01"
    assert resolve_date("29 feb", captured_at=anchor)["resolved"] == "2028-02-29"


def test_impossible_named_date_stays_unresolved():
    anchor = "2026-10-17T10:00:00"
    result = resolve_date("the 30th of February", captured_at=anchor)
    assert result == {"spoken": "the 30th of February", "resolved": None}


def test_resolve_yesterday():
    assert resolve_date("yesterday", captured_at="2026-10-17T10:00:00")["resolved"] == "2026-10-16"
