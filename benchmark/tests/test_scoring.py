from __future__ import annotations

import pytest

from harness.scoring import NOT_A_NOTE, Case, Outcome, field_matches, percentile, summarise


def _case(case_id, expected_type, fields=None, category="misc", expect_warning=False):
    return Case(
        id=case_id,
        category=category,
        transcript=f"transcript {case_id}",
        expected_type=expected_type,
        expected_fields=fields or {},
        expect_warning=expect_warning,
    )


def _outcome(case_id, actual_type, fields=None, warnings=(), latency=1.0, stages=None, error=None):
    return Outcome(
        case_id=case_id,
        actual_type=actual_type,
        fields=fields or {},
        warnings=list(warnings),
        latency_s=latency,
        stage_s=stages or {},
        error=error,
    )


class TestFieldMatches:
    def test_money_compares_amount_and_currency(self):
        expected = {"amount": 500.0, "currency": "INR"}
        assert field_matches(expected, {"amount": 500, "currency": "INR"})
        assert not field_matches(expected, {"amount": 500.0, "currency": "USD"})
        assert not field_matches(expected, {"amount": 50.0, "currency": "INR"})

    def test_dates_compare_the_resolved_day_only(self):
        expected = {"spoken": "next Friday", "resolved": "2026-10-30"}
        assert field_matches(expected, {"spoken": "friday next", "resolved": "2026-10-30"})
        assert not field_matches(expected, {"spoken": "next Friday", "resolved": None})

    def test_text_ignores_case_spacing_and_trailing_punctuation(self):
        assert field_matches("Ravi", " ravi ")
        assert field_matches("Office Wi-Fi password", "office wi-fi password.")
        assert not field_matches("Ravi", "Ravish")

    def test_lists_compare_as_sets_of_normalised_items(self):
        assert field_matches(["Sunita", "Tarun"], ["tarun", "Sunita"])
        assert not field_matches(["Sunita", "Tarun"], ["Sunita"])

    def test_clock_times_compare_by_time_not_spelling(self):
        assert field_matches("8 PM", "8:00 pm")
        assert field_matches("2:30 PM", "2.30 p.m.")
        assert not field_matches("8 PM", "8 AM")
        assert not field_matches("8 PM", "evening")

    def test_missing_actual_never_matches(self):
        assert not field_matches("Ravi", None)


def test_percentile_uses_nearest_rank():
    values = [1.0, 2.0, 3.0, 4.0, 10.0]
    assert percentile(values, 95) == 10.0
    assert percentile(values, 50) == 3.0
    assert percentile([], 95) is None


@pytest.fixture
def run():
    cases = [
        _case(
            "p1",
            "payment",
            {"direction": "they_owe_me", "amount": {"amount": 500.0, "currency": "INR"}},
            "direction",
        ),
        _case(
            "p2",
            "payment",
            {"direction": "i_owe_them", "due_date": {"spoken": "x", "resolved": "2026-10-30"}},
            "direction",
        ),
        _case("e1", "event", {"title": "Standup"}, "dates", expect_warning=True),
        _case("g1", "general", {}, "ordinary"),
        _case("n1", NOT_A_NOTE, {}, "non_note"),
        _case("n2", NOT_A_NOTE, {}, "non_note"),
    ]
    outcomes = [
        _outcome(
            "p1",
            "payment",
            {"direction": "they_owe_me", "amount": {"amount": 500.0, "currency": "INR"}},
            latency=2.0,
            stages={"classify": 0.5, "extract": 1.5},
        ),
        _outcome(
            "p2",
            "payment",
            {"direction": "they_owe_me", "due_date": {"spoken": "x", "resolved": "2026-10-30"}},
            latency=4.0,
            stages={"classify": 1.0, "extract": 3.0},
        ),
        _outcome("e1", "event", {"title": "standup"}, warnings=["far away"], latency=3.0),
        _outcome("g1", NOT_A_NOTE, latency=0.5),
        _outcome("n1", NOT_A_NOTE, latency=0.5),
        _outcome("n2", None, error="boom", latency=0.0),
    ]
    return cases, outcomes


def test_summary_scores(run):
    cases, outcomes = run
    s = summarise(cases, outcomes, llm_calls=20, malformed_replies=1, vram_peak_mb=4000)

    assert s["classification_accuracy"] == pytest.approx(4 / 6)
    assert s["per_type"] == {"payment": 1.0, "event": 1.0, "general": 0.0, NOT_A_NOTE: 0.5}
    assert s["per_category"]["direction"] == 1.0
    assert s["note_gate_recall"] == pytest.approx(1 / 2)
    assert s["notes_wrongly_rejected"] == pytest.approx(1 / 4)

    assert s["per_field"] == {
        "payment.direction": 0.5,
        "payment.amount": 1.0,
        "payment.due_date": 1.0,
        "event.title": 1.0,
    }
    assert s["field_accuracy"] == pytest.approx(4 / 5)
    assert s["direction_accuracy"] == 0.5
    assert s["amount_accuracy"] == 1.0
    assert s["date_accuracy"] == 1.0

    assert s["warning_recall"] == 1.0
    assert s["false_warning_rate"] == 0.0
    assert s["malformed_reply_rate"] == pytest.approx(1 / 20)
    assert s["errored_cases"] == ["n2"]

    assert s["mean_latency_s"] == pytest.approx((2 + 4 + 3 + 0.5 + 0.5) / 5)
    assert s["p95_latency_s"] == 4.0
    assert s["stage_mean_s"] == {"classify": 0.75, "extract": 2.25}
    assert s["vram_peak_mb"] == 4000


def test_rates_with_nothing_to_measure_are_none():
    s = summarise([_case("g1", "general")], [_outcome("g1", "general")], 3, 0, None)
    assert s["warning_recall"] is None
    assert s["note_gate_recall"] is None
    assert s["direction_accuracy"] is None
    assert s["vram_peak_mb"] is None


def test_free_text_fields_are_scored_separately():
    cases = [_case("i1", "info", {"topic": "Wi-Fi password", "details": "brew2026"})]
    outcomes = [_outcome("i1", "info", {"topic": "Office Wi-Fi password", "details": "brew2026"})]
    s = summarise(cases, outcomes, 4, 0, None, free_text_fields={"info.topic"})
    assert s["field_accuracy"] == 1.0
    assert s["free_text_exact"] == 0.0
    assert s["per_field"]["info.topic"] == 0.0
