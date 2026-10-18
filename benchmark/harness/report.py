"""Markdown comparison of model runs: one column per model, best value per row in bold."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

MISSING = "—"

# (summary key, row label, higher is better, unit)
METRICS: list[tuple[str, str, bool, str]] = [
    ("classification_accuracy", "Classification accuracy", True, "pct"),
    ("note_gate_recall", "Non-notes rejected", True, "pct"),
    ("notes_wrongly_rejected", "Real notes wrongly rejected", False, "pct"),
    ("field_accuracy", "Field accuracy", True, "pct"),
    ("free_text_exact", "Free-text fields, exact wording", True, "pct"),
    ("direction_accuracy", "Payment direction", True, "pct"),
    ("amount_accuracy", "Amounts", True, "pct"),
    ("date_accuracy", "Dates", True, "pct"),
    ("warning_recall", "Warnings caught", True, "pct"),
    ("false_warning_rate", "False warnings", False, "pct"),
    ("malformed_reply_rate", "Malformed LLM replies", False, "pct"),
    ("errored_cases", "Errored cases", False, "count"),
    ("mean_latency_s", "Mean time per note", False, "seconds"),
    ("p95_latency_s", "p95 time per note", False, "seconds"),
    ("vram_peak_mb", "Peak VRAM", False, "mb"),
]

FORMATTERS: dict[str, Callable[[float], str]] = {
    "pct": lambda v: f"{v * 100:.1f}%",
    "seconds": lambda v: f"{v:.2f} s",
    "mb": lambda v: f"{v:,.0f} MB",
    "count": lambda v: f"{v:.0f}",
}


def _numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, list):
        return float(len(value))
    return float(value)


def _row(label: str, values: list[float | None], higher_is_better: bool, unit: str) -> str:
    present = [v for v in values if v is not None]
    best = (max if higher_is_better else min)(present) if present else None
    cells = []
    for value in values:
        if value is None:
            cells.append(MISSING)
            continue
        text = FORMATTERS[unit](value)
        cells.append(f"**{text}**" if value == best else text)
    return f"| {label} | " + " | ".join(cells) + " |"


def _table(title: str, models: list[str], rows: list[str]) -> list[str]:
    return [
        f"## {title}",
        "",
        "| Metric | " + " | ".join(models) + " |",
        "|---|" + "---|" * len(models),
        *rows,
        "",
    ]


def comparison_markdown(runs: dict[str, dict[str, Any]]) -> str:
    """Build the comparison report for runs keyed by model id, in the given order."""
    models = list(runs)
    summaries = list(runs.values())

    score_rows = [
        _row(label, [_numeric(s.get(key)) for s in summaries], higher, unit)
        for key, label, higher, unit in METRICS
    ]
    categories = sorted({c for s in summaries for c in s.get("per_category", {})})
    category_rows = [
        _row(c, [s.get("per_category", {}).get(c) for s in summaries], True, "pct")
        for c in categories
    ]
    stages = list(dict.fromkeys(st for s in summaries for st in s.get("stage_mean_s", {})))
    stage_rows = [
        _row(st, [s.get("stage_mean_s", {}).get(st) for s in summaries], False, "seconds")
        for st in stages
    ]

    lines = _table("Scores", models, score_rows)
    lines += _table("Classification accuracy by category", models, category_rows)
    if stage_rows:
        lines += _table("Mean time per pipeline stage", models, stage_rows)
    return "\n".join(lines)
