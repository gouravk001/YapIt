from __future__ import annotations

from harness.report import METRICS, comparison_markdown


def _summary(**overrides):
    base = {key: None for key, *_ in METRICS}
    base.update(
        {
            "classification_accuracy": 0.9,
            "mean_latency_s": 2.0,
            "errored_cases": [],
            "per_category": {"direction": 0.5, "dates": 1.0},
        }
    )
    base.update(overrides)
    return base


def test_best_value_is_bold_respecting_direction():
    runs = {
        "gemma": _summary(classification_accuracy=0.9, mean_latency_s=2.5),
        "qwen": _summary(classification_accuracy=0.8, mean_latency_s=1.5),
    }
    md = comparison_markdown(runs)
    accuracy_row = next(line for line in md.splitlines() if line.startswith("| Classification"))
    latency_row = next(line for line in md.splitlines() if line.startswith("| Mean time per note"))

    assert "**90.0%**" in accuracy_row and "80.0%" in accuracy_row
    assert "**1.50 s**" in latency_row and "2.50 s" in latency_row


def test_missing_values_show_a_dash_and_are_never_bold():
    runs = {"gemma": _summary(warning_recall=None), "qwen": _summary(warning_recall=0.5)}
    row = next(
        line
        for line in comparison_markdown(runs).splitlines()
        if line.startswith("| Warnings caught")
    )
    assert "—" in row and "**50.0%**" in row


def test_ties_are_all_bold():
    runs = {"a": _summary(classification_accuracy=0.9), "b": _summary(classification_accuracy=0.9)}
    row = next(
        line
        for line in comparison_markdown(runs).splitlines()
        if line.startswith("| Classification")
    )
    assert row.count("**90.0%**") == 2


def test_category_table_lists_every_category_once():
    runs = {"gemma": _summary(), "qwen": _summary(per_category={"direction": 0.75})}
    md = comparison_markdown(runs)
    assert md.count("| direction |") == 1
    assert "| dates | **100.0%** | — |" in md


def test_columns_follow_the_given_model_order():
    runs = {"qwen": _summary(), "gemma": _summary()}
    header = next(
        line for line in comparison_markdown(runs).splitlines() if line.startswith("| Metric")
    )
    assert header.index("qwen") < header.index("gemma")
