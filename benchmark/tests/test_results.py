from __future__ import annotations

from harness.results import latest_runs, save_run


def _run(model_id, started_at, sha="abc"):
    return {"model_id": model_id, "started_at": started_at, "dataset_sha": sha, "summary": {}}


def test_saved_runs_round_trip_and_newest_wins(tmp_path):
    save_run(_run("gemma", "2026-10-18T18:00:00"), tmp_path)
    save_run(_run("gemma", "2026-10-18T19:00:00"), tmp_path)
    save_run(_run("qwen", "2026-10-18T18:30:00"), tmp_path)

    latest = latest_runs(tmp_path, ["qwen", "gemma"], dataset_sha="abc")
    assert list(latest) == ["qwen", "gemma"]
    assert latest["gemma"]["started_at"] == "2026-10-18T19:00:00"


def test_runs_on_another_dataset_version_are_ignored(tmp_path):
    save_run(_run("gemma", "2026-10-18T18:00:00", sha="old"), tmp_path)
    assert latest_runs(tmp_path, ["gemma"], dataset_sha="new") == {}


def test_models_not_in_the_order_are_left_out(tmp_path):
    save_run(_run("removed-model", "2026-10-18T18:00:00"), tmp_path)
    assert latest_runs(tmp_path, ["gemma"], dataset_sha="abc") == {}
