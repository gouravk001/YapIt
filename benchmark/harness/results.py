"""Saving model runs and finding the latest one per model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def save_run(run: dict[str, Any], results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = run["started_at"].replace(":", "").replace("-", "")
    path = results_dir / f"{run['model_id']}_{stamp}.json"
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def latest_runs(
    results_dir: Path, model_order: list[str], dataset_sha: str
) -> dict[str, dict[str, Any]]:
    """Newest saved run per model, for this dataset version only, in model_order order.

    Runs on an older dataset are skipped so the comparison never mixes different test sets.
    """
    latest: dict[str, dict[str, Any]] = {}
    for path in sorted(results_dir.glob("*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        if run.get("dataset_sha") != dataset_sha:
            continue
        current = latest.get(run["model_id"])
        if current is None or run["started_at"] > current["started_at"]:
            latest[run["model_id"]] = run
    return {model: latest[model] for model in model_order if model in latest}
