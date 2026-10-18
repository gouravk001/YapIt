"""Benchmark LLMs on YapIt's real text pipeline and compare them.

Add a model to benchmark/models.yaml, then run (from the repo root, backend virtualenv):
    backend/.venv/bin/python benchmark/run.py            # download + test any new models, report
    backend/.venv/bin/python benchmark/run.py --rerun    # test every model again
    backend/.venv/bin/python benchmark/run.py --models qwen3.5-4b   # just these models
    backend/.venv/bin/python benchmark/run.py --smoke    # quick check, 5 cases, nothing saved
    backend/.venv/bin/python benchmark/run.py --compare  # rebuild comparison.md only
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import socket
import sys
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

BENCHMARK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCHMARK_DIR.parent / "backend"))
sys.path.insert(0, str(BENCHMARK_DIR))

import yaml  # noqa: E402

from app.config.loader import load_checks, load_types  # noqa: E402
from app.providers.base import Transcriber, Transcription  # noqa: E402
from app.services.pipeline_service import PipelineService  # noqa: E402
from harness.instrumented import InstrumentedLLM  # noqa: E402
from harness.models import ModelSpec, models_to_run, parse_models, resolve_think  # noqa: E402
from harness.ollama_client import (  # noqa: E402
    OllamaClient,
    ensure_downloaded,
    model_capabilities,
    ollama_reachable,
    unload_all_models,
    wait_until_unloaded,
)
from harness.report import comparison_markdown  # noqa: E402
from harness.results import latest_runs, save_run  # noqa: E402
from harness.runner import run_case  # noqa: E402
from harness.scoring import Case, Outcome, summarise  # noqa: E402
from harness.vram import VramSampler, read_vram_mb  # noqa: E402

DATASET = BENCHMARK_DIR / "dataset.json"
MODELS = BENCHMARK_DIR / "models.yaml"
RESULTS = BENCHMARK_DIR / "results"
COMPARISON = RESULTS / "comparison.md"
SMOKE_CASES = 5
APP_PORT = 8000
WARMUP_PROMPT = "Reply with OK."
UNLOAD_TIMEOUT_SECONDS = 60


class NoTranscriber(Transcriber):
    """The benchmark feeds transcripts directly; audio never reaches the pipeline."""

    def transcribe(self, audio_path: str) -> Transcription:
        raise RuntimeError("The benchmark only runs the text pipeline.")


def app_is_running() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", APP_PORT)) == 0


def load_dataset() -> tuple[dict[str, Any], list[Case]]:
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    return raw["metadata"], [Case.from_dict(c) for c in raw["cases"]]


def load_models() -> list[ModelSpec]:
    return parse_models(yaml.safe_load(MODELS.read_text(encoding="utf-8")))


def show_download_progress(tag: str) -> Callable[[int, int], None]:
    def show(done: int, total: int) -> None:
        print(
            f"\r   downloading {tag}: {done / total:4.0%} of {total / 1e9:.1f} GB",
            end="",
            flush=True,
        )

    return show


async def run_cases(pipeline: PipelineService, cases: list[Case], anchor: dict[str, str]) -> list:
    outcomes = []
    for index, case in enumerate(cases, 1):
        outcome = await run_case(pipeline, case, anchor["captured_at"], anchor["timezone"])
        mark = "✗" if outcome.error else ("✓" if outcome.actual_type == case.expected_type else "·")
        print(
            f"  [{index:3d}/{len(cases)}] {mark} {case.id:<10} {outcome.latency_s:5.2f}s",
            flush=True,
        )
        outcomes.append(outcome)
    return outcomes


def benchmark_model(spec: ModelSpec, cases: list[Case], anchor: dict[str, str]) -> dict[str, Any]:
    think = resolve_think(spec, model_capabilities(spec.tag))
    client = OllamaClient(spec.tag, options=spec.options, think=think)
    llm = InstrumentedLLM(client)
    pipeline = PipelineService(NoTranscriber(), llm, load_types(), plausibility_rules=load_checks())

    wait_until_unloaded(UNLOAD_TIMEOUT_SECONDS)
    baseline_mb = read_vram_mb()
    started_at = datetime.now().isoformat(timespec="seconds")
    with VramSampler() as vram:
        load_started = time.perf_counter()
        client.generate(WARMUP_PROMPT)  # loads the model; excluded from the scores
        load_seconds = time.perf_counter() - load_started
        outcomes = asyncio.run(run_cases(pipeline, cases, anchor))
    client.unload()

    model_mb = vram.peak_mb - baseline_mb if None not in (vram.peak_mb, baseline_mb) else None
    counters = {
        "llm_calls": llm.calls,
        "malformed_replies": llm.malformed,
        "vram_model_mb": model_mb,
        "load_seconds": load_seconds,
    }
    return {
        "model_id": spec.id,
        "label": spec.label,
        "tag": spec.tag,
        "settings": {**spec.options, "think": think},
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "counters": counters,
        "summary": score_run(cases, outcomes, counters),
        "outcomes": [asdict(o) for o in outcomes],
    }


def score_run(cases: list[Case], outcomes: list[Outcome], counters: dict[str, Any]) -> dict:
    return summarise(
        cases,
        outcomes,
        counters["llm_calls"],
        counters["malformed_replies"],
        counters["vram_model_mb"],
        free_text_fields(load_types()),
    )


def free_text_fields(types: list) -> set[str]:
    """Text fields whose wording varies (titles, topics, notes); "time" is compared as a clock time."""
    return {
        f"{t.name}.{f.name}"
        for t in types
        for f in t.fields
        if f.field_type == "text" and f.name != "time"
    }


def dataset_fingerprint() -> str:
    return hashlib.sha256(DATASET.read_bytes()).hexdigest()[:12]


def write_comparison(model_order: list[str]) -> str:
    runs = latest_runs(RESULTS, model_order, dataset_fingerprint())
    if not runs:
        return "No saved runs for the current dataset yet."
    # Scores are recomputed from the saved outcomes, so scoring fixes never need a model re-run.
    _, cases = load_dataset()
    summaries = {
        r["label"]: score_run(cases, [Outcome(**o) for o in r["outcomes"]], r["counters"])
        for r in runs.values()
    }
    report = comparison_markdown(summaries)
    header = (
        "# YapIt model comparison\n\n"
        f"Dataset: `benchmark/dataset.json` ({dataset_fingerprint()}). "
        "Generated by `benchmark/run.py`.\n\n"
    )
    COMPARISON.write_text(header + report + "\n", encoding="utf-8")
    return report


def print_run_summary(run: dict[str, Any]) -> None:
    s = run["summary"]
    print(
        f"   classification {s['classification_accuracy']:.1%}, "
        f"fields {s['field_accuracy'] or 0:.1%}, mean {s['mean_latency_s'] or 0:.2f}s, "
        f"errored {len(s['errored_cases'])}"
    )


def main() -> None:
    # The pipeline logs every retry; the benchmark counts those itself, so keep the console readable.
    logging.getLogger("app").setLevel(logging.ERROR)
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--models", nargs="+", help="only these model ids from models.yaml")
    parser.add_argument(
        "--rerun", action="store_true", help="test models that already have results"
    )
    parser.add_argument(
        "--smoke", action="store_true", help=f"first {SMOKE_CASES} cases only, nothing saved"
    )
    parser.add_argument("--compare", action="store_true", help="only rebuild comparison.md")
    args = parser.parse_args()

    try:
        specs = load_models()
    except ValueError as exc:
        parser.error(str(exc))
    order = [s.id for s in specs]
    if args.compare:
        print(write_comparison(order))
        return
    if not ollama_reachable():
        parser.error("Ollama isn't running. Start it (sudo systemctl start ollama) and try again.")

    done = set(latest_runs(RESULTS, order, dataset_fingerprint()))
    try:
        targets = models_to_run(specs, done, only=args.models, rerun=args.rerun or args.smoke)
    except ValueError as exc:
        parser.error(str(exc))
    if not targets:
        print("Every model in models.yaml already has results on this test set (--rerun to redo).")
        print("\n" + write_comparison(order))
        return
    if app_is_running():
        print(
            f"Warning: something is listening on port {APP_PORT} (the app?). Its traffic will skew "
            "timings and VRAM, and unloading models will make its next request slow."
        )

    metadata, cases = load_dataset()
    if args.smoke:
        cases = cases[:SMOKE_CASES]
    print(f"Models to test: {', '.join(s.id for s in targets)}")
    print(f"Unloaded from memory: {', '.join(unload_all_models()) or 'nothing'}")

    for spec in targets:
        print(f"\n== {spec.label} ({spec.tag}) on {len(cases)} cases")
        if ensure_downloaded(spec.tag, show_download_progress(spec.tag)):
            print(f"\n   downloaded {spec.tag}")
        run = benchmark_model(spec, cases, metadata["anchor"])
        run["dataset_sha"] = dataset_fingerprint()
        print_run_summary(run)
        if not args.smoke:
            print(f"   saved {save_run(run, RESULTS).relative_to(BENCHMARK_DIR.parent)}")

    if not args.smoke:
        print("\n" + write_comparison(order))


if __name__ == "__main__":
    main()
