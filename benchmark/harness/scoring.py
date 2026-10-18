"""Turn per-case outcomes into the scores the comparison reports.

All rates are fractions between 0 and 1, or None when there was nothing to measure (for
example a warning recall with no unreasonable cases in the run).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from statistics import mean
from typing import Any

NOT_A_NOTE = "not_a_note"
DEFAULT_CURRENCY = "INR"
P95 = 95
# "8 PM", "8:00 pm", "2.30 p.m." -> hour, minute, am/pm
_CLOCK_TIME = re.compile(r"^(\d{1,2})(?:[:.](\d{2}))?\s*([ap])\.?\s*m\.?$")


@dataclass(frozen=True)
class Case:
    """One test case: a transcript and what a correct pipeline produces for it."""

    id: str
    category: str
    transcript: str
    expected_type: str
    expected_fields: dict[str, Any]
    expect_warning: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Case:
        return cls(
            id=raw["id"],
            category=raw["category"],
            transcript=raw["transcript"],
            expected_type=raw["expected_type"],
            expected_fields=raw.get("expected_fields", {}),
            expect_warning=raw.get("expect_warning", False),
        )


@dataclass(frozen=True)
class Outcome:
    """What a model run produced for one case. actual_type is None when the case errored."""

    case_id: str
    actual_type: str | None
    fields: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    latency_s: float = 0.0
    stage_s: dict[str, float] = field(default_factory=dict)
    error: str | None = None


def _normalise_text(value: Any) -> str:
    return " ".join(str(value).lower().split()).rstrip(".!,;")


def _clock_time(value: Any) -> tuple[int, int, str] | None:
    match = _CLOCK_TIME.match(str(value).strip().lower())
    if not match:
        return None
    hour, minute, half = match.groups()
    return int(hour), int(minute or 0), half


def _is_money(value: Any) -> bool:
    return isinstance(value, dict) and "amount" in value


def _is_date(value: Any) -> bool:
    return isinstance(value, dict) and "resolved" in value


def field_matches(expected: Any, actual: Any) -> bool:
    """Whether a produced field value counts as correct for the expected one."""
    if actual is None:
        return False
    if _is_money(expected):
        return (
            _is_money(actual)
            and actual.get("amount") is not None
            and float(actual["amount"]) == float(expected["amount"])
            and actual.get("currency", DEFAULT_CURRENCY)
            == expected.get("currency", DEFAULT_CURRENCY)
        )
    if _is_date(expected):
        return _is_date(actual) and actual.get("resolved") == expected.get("resolved")
    if isinstance(expected, list):
        return isinstance(actual, list) and {_normalise_text(v) for v in expected} == {
            _normalise_text(v) for v in actual
        }
    expected_time = _clock_time(expected)
    if expected_time is not None:
        return expected_time == _clock_time(actual)
    return _normalise_text(expected) == _normalise_text(actual)


def percentile(values: Iterable[float], pct: float) -> float | None:
    """Nearest-rank percentile: the smallest value with at least pct% of values at or below it."""
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _rates(tallies: dict[str, list[bool]]) -> dict[str, float]:
    return {key: sum(results) / len(results) for key, results in tallies.items()}


def _field_kind(name: str, expected: Any) -> str | None:
    if name == "direction":
        return "direction"
    if _is_money(expected):
        return "amount"
    if _is_date(expected):
        return "date"
    return None


def summarise(
    cases: list[Case],
    outcomes: list[Outcome],
    llm_calls: int,
    malformed_replies: int,
    vram_peak_mb: int | None,
    free_text_fields: frozenset[str] | set[str] = frozenset(),
) -> dict[str, Any]:
    """Score one model's run over the test set.

    free_text_fields ("type.field") hold wording the model may legitimately phrase differently;
    they are kept out of field_accuracy and reported as free_text_exact instead.
    """
    by_id = {o.case_id: o for o in outcomes}
    by_type: dict[str, list[bool]] = defaultdict(list)
    by_category: dict[str, list[bool]] = defaultdict(list)
    by_field: dict[str, list[bool]] = defaultdict(list)
    by_kind: dict[str, list[bool]] = defaultdict(list)
    non_notes_rejected: list[bool] = []
    notes_rejected: list[bool] = []
    warnings_caught: list[bool] = []
    false_warnings: list[bool] = []

    for case in cases:
        outcome = by_id[case.id]
        correct = outcome.actual_type == case.expected_type
        by_type[case.expected_type].append(correct)
        by_category[case.category].append(correct)

        if case.expected_type == NOT_A_NOTE:
            non_notes_rejected.append(outcome.actual_type == NOT_A_NOTE)
            continue
        notes_rejected.append(outcome.actual_type == NOT_A_NOTE)

        has_draft = outcome.actual_type not in (None, NOT_A_NOTE)
        if case.expect_warning:
            warnings_caught.append(has_draft and bool(outcome.warnings))
        elif has_draft:
            false_warnings.append(bool(outcome.warnings))

        for name, expected in case.expected_fields.items():
            matched = field_matches(expected, outcome.fields.get(name))
            by_field[f"{case.expected_type}.{name}"].append(matched)
            kind = _field_kind(name, expected)
            if kind:
                by_kind[kind].append(matched)

    answered = [o for o in outcomes if o.error is None]
    stage_times: dict[str, list[float]] = defaultdict(list)
    for outcome in answered:
        for stage, seconds in outcome.stage_s.items():
            stage_times[stage].append(seconds)
    structured = [hit for f, res in by_field.items() if f not in free_text_fields for hit in res]
    free_text = [hit for f, res in by_field.items() if f in free_text_fields for hit in res]

    return {
        "classification_accuracy": _rate(sum(sum(r) for r in by_type.values()), len(cases)),
        "per_type": _rates(by_type),
        "per_category": _rates(by_category),
        "note_gate_recall": _rate(sum(non_notes_rejected), len(non_notes_rejected)),
        "notes_wrongly_rejected": _rate(sum(notes_rejected), len(notes_rejected)),
        "field_accuracy": _rate(sum(structured), len(structured)),
        "free_text_exact": _rate(sum(free_text), len(free_text)),
        "per_field": _rates(by_field),
        "direction_accuracy": _rate(sum(by_kind["direction"]), len(by_kind["direction"])),
        "amount_accuracy": _rate(sum(by_kind["amount"]), len(by_kind["amount"])),
        "date_accuracy": _rate(sum(by_kind["date"]), len(by_kind["date"])),
        "warning_recall": _rate(sum(warnings_caught), len(warnings_caught)),
        "false_warning_rate": _rate(sum(false_warnings), len(false_warnings)),
        "malformed_reply_rate": _rate(malformed_replies, llm_calls),
        "errored_cases": [o.case_id for o in outcomes if o.error is not None],
        "mean_latency_s": mean(o.latency_s for o in answered) if answered else None,
        "p95_latency_s": percentile((o.latency_s for o in answered), P95),
        "stage_mean_s": {stage: mean(times) for stage, times in stage_times.items()},
        "vram_peak_mb": vram_peak_mb,
    }
