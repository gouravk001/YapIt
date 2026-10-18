import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.loader import load_checks, load_model_registry, load_types
from app.errors import NotANoteError
from app.providers.factory import create_providers
from app.services.pipeline_service import PipelineService

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("eval")

NOT_A_NOTE = "not_a_note"


def get_vram_used_mb() -> int | None:
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return int(res.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


def run_eval(llm_override: str | None = None) -> dict[str, Any]:
    registry = load_model_registry()
    if llm_override:
        registry.active.llm = llm_override

    active_llm = registry.get_active("llm")
    types = load_types()
    transcriber, llm = create_providers(registry)
    pipeline = PipelineService(transcriber, llm, types, plausibility_rules=load_checks())

    dataset_path = Path(__file__).parent / "dataset.json"
    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data["samples"]
    anchor = data["metadata"]["fixed_anchor"]
    captured_at = anchor["captured_at"]
    timezone = anchor["timezone"]

    total = len(samples)
    correct_classifications = 0
    per_type_stats: dict[str, dict[str, int]] = {}
    needs_review_count = 0
    total_fields_checked = 0
    total_fields_matched = 0
    per_field_stats: dict[str, dict[str, int]] = {}
    errored: list[str] = []
    warnings_expected = warnings_caught = 0
    ordinary_notes = false_warnings = 0
    mismatches: list[dict[str, Any]] = []

    durations: list[float] = []

    print(
        f"\nRunning evaluation on {total} samples using LLM: {active_llm.model_name} ({active_llm.id})"
    )
    print("-" * 65)

    import asyncio

    async def _evaluate_all():
        nonlocal correct_classifications, needs_review_count
        nonlocal total_fields_checked, total_fields_matched
        nonlocal warnings_expected, warnings_caught, ordinary_notes, false_warnings

        for idx, sample in enumerate(samples, 1):
            exp_type = sample["expected_type"]
            if exp_type not in per_type_stats:
                per_type_stats[exp_type] = {"total": 0, "correct": 0}
            per_type_stats[exp_type]["total"] += 1

            t0 = time.perf_counter()
            envelope = None
            try:
                envelope = await pipeline.process_text(
                    sample["transcript"], captured_at=captured_at, timezone=timezone
                )
                actual_type = envelope.type_name
            except NotANoteError:
                actual_type = NOT_A_NOTE
            except Exception as e:
                logger.error("Error processing sample %s: %s", sample["id"], e)
                errored.append(sample["id"])
                continue
            elapsed = time.perf_counter() - t0
            durations.append(elapsed)

            is_class_correct = actual_type == exp_type
            if is_class_correct:
                correct_classifications += 1
                per_type_stats[exp_type]["correct"] += 1

            if envelope is not None and envelope.missing_fields:
                needs_review_count += 1

            warned = envelope is not None and bool(envelope.warnings)
            if sample.get("expect_warning"):
                warnings_expected += 1
                warnings_caught += warned
            elif envelope is not None:
                ordinary_notes += 1
                false_warnings += warned

            fields = envelope.fields if envelope is not None else {}
            for k, expected_v in sample.get("expected_fields", {}).items():
                stats = per_field_stats.setdefault(f"{exp_type}.{k}", {"checked": 0, "matched": 0})
                total_fields_checked += 1
                stats["checked"] += 1
                if _field_matches(expected_v, fields.get(k)):
                    total_fields_matched += 1
                    stats["matched"] += 1
                else:
                    mismatches.append(
                        {
                            "id": sample["id"],
                            "field": k,
                            "expected": expected_v,
                            "actual": fields.get(k),
                        }
                    )

            status_char = "✓" if is_class_correct else "✗"
            summary = f"  {envelope.summary}" if envelope is not None else ""
            if warned:
                summary += f"  ⚠ {envelope.warnings[0].message}"
            print(
                f"[{idx:02d}/{total:02d}] {status_char} Expected: {exp_type:<10} "
                f"Actual: {actual_type:<10} ({elapsed:.2f}s){summary}"
            )

    asyncio.run(_evaluate_all())

    classification_acc = (correct_classifications / total) if total else 0.0
    field_acc = (total_fields_matched / total_fields_checked) if total_fields_checked else 0.0
    avg_latency = (sum(durations) / len(durations)) if durations else 0.0
    vram_mb = get_vram_used_mb()

    results = {
        "model_id": active_llm.id,
        "model_name": active_llm.model_name,
        "timestamp": datetime.now().isoformat(),
        "total_samples": total,
        "classification_accuracy": round(classification_acc * 100, 2),
        "field_accuracy": round(field_acc * 100, 2),
        "needs_review_fraction": round(needs_review_count / total, 2) if total else 0.0,
        "average_latency_sec": round(avg_latency, 3),
        "vram_used_mb": vram_mb,
        "per_type_accuracy": {
            t: round((stats["correct"] / stats["total"]) * 100, 2)
            for t, stats in per_type_stats.items()
            if stats["total"] > 0
        },
        "per_field_accuracy": {
            f: round((stats["matched"] / stats["checked"]) * 100, 2)
            for f, stats in sorted(per_field_stats.items())
        },
        "warning_recall": (
            round(warnings_caught / warnings_expected * 100, 2) if warnings_expected else None
        ),
        "false_warning_rate": (
            round(false_warnings / ordinary_notes * 100, 2) if ordinary_notes else None
        ),
        "errored_samples": errored,
        "field_mismatches": mismatches,
    }

    # Save run
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{active_llm.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("EVALUATION RESULTS")
    print("=" * 65)
    print(f"Model:                   {results['model_name']} ({results['model_id']})")
    print(f"Classification Accuracy: {results['classification_accuracy']}%")
    print(f"Field Accuracy:          {results['field_accuracy']}%")
    print(f"Needs Review Fraction:   {results['needs_review_fraction'] * 100:.1f}%")
    print(f"Avg Latency per note:    {results['average_latency_sec']}s")
    print(
        f"Warnings:                caught {warnings_caught}/{warnings_expected} unreasonable, "
        f"false alarms on {false_warnings}/{ordinary_notes} ordinary notes"
    )
    print(f"VRAM used:               {results['vram_used_mb'] or 'N/A'} MB")
    print("-" * 65)
    print("Per-type accuracy:")
    for t, acc in results["per_type_accuracy"].items():
        print(f"  {t:<10}: {acc}%")
    print("Per-field accuracy:")
    for f, acc in results["per_field_accuracy"].items():
        print(f"  {f:<22}: {acc}%")
    if errored:
        print(f"ERRORED SAMPLES (counted as wrong): {', '.join(errored)}")
    print(f"Saved to: {out_file}")

    return results


def _field_matches(exp: Any, act: Any) -> bool:
    if exp == act:
        return True
    if isinstance(exp, dict) and isinstance(act, dict):
        if "amount" in exp and "amount" in act:
            return float(exp["amount"]) == float(act["amount"])
        if "resolved" in exp and "resolved" in act:
            return str(exp["resolved"]) == str(act["resolved"])
    if isinstance(exp, str) and isinstance(act, str):
        return exp.strip().lower() == act.strip().lower()
    return False


def compare_runs() -> None:
    results_dir = Path(__file__).parent / "results"
    if not results_dir.exists():
        print("No saved results found.")
        return

    files = sorted(results_dir.glob("*.json"))
    if not files:
        print("No saved results found.")
        return

    print("\n" + "=" * 80)
    print(f"{'Model ID':<20} {'Date':<18} {'Class Acc':<12} {'Field Acc':<12} {'Avg Latency':<12}")
    print("=" * 80)
    for f in files:
        try:
            with f.open("r", encoding="utf-8") as fh:
                d = json.load(fh)
            dt_str = d.get("timestamp", "")[:16].replace("T", " ")
            print(
                f"{d.get('model_id', ''):<20} {dt_str:<18} "
                f"{d.get('classification_accuracy', 0):>6.1f}%      "
                f"{d.get('field_accuracy', 0):>6.1f}%      "
                f"{d.get('average_latency_sec', 0):>6.2f}s"
            )
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YapIt Evaluation Harness")
    parser.add_argument("--llm", help="Override active LLM model ID from registry")
    parser.add_argument(
        "--compare", action="store_true", help="Print comparison of previous eval runs"
    )
    args = parser.parse_args()

    if args.compare:
        compare_runs()
    else:
        run_eval(llm_override=args.llm)
