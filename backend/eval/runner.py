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

from app.config.loader import load_model_registry, load_types
from app.providers.factory import create_providers
from app.services.pipeline_service import PipelineService

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("eval")


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
    pipeline = PipelineService(transcriber, llm, types)

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

    durations: list[float] = []

    print(
        f"\nRunning evaluation on {total} samples using LLM: {active_llm.model_name} ({active_llm.id})"
    )
    print("-" * 65)

    import asyncio

    async def _evaluate_all():
        nonlocal correct_classifications, needs_review_count
        nonlocal total_fields_checked, total_fields_matched

        for idx, sample in enumerate(samples, 1):
            exp_type = sample["expected_type"]
            if exp_type not in per_type_stats:
                per_type_stats[exp_type] = {"total": 0, "correct": 0}
            per_type_stats[exp_type]["total"] += 1

            t0 = time.perf_counter()
            try:
                envelope = await pipeline.process_text(
                    sample["transcript"], captured_at=captured_at, timezone=timezone
                )
            except Exception as e:
                logger.error("Error processing sample %s: %s", sample["id"], e)
                continue
            elapsed = time.perf_counter() - t0
            durations.append(elapsed)

            # Check classification
            is_class_correct = envelope.type_name == exp_type
            if is_class_correct:
                correct_classifications += 1
                per_type_stats[exp_type]["correct"] += 1

            if envelope.status == "needs_review":
                needs_review_count += 1

            # Check field match
            exp_fields = sample.get("expected_fields", {})
            for k, expected_v in exp_fields.items():
                total_fields_checked += 1
                actual_v = envelope.fields.get(k)
                if _field_matches(expected_v, actual_v):
                    total_fields_matched += 1

            status_char = "✓" if is_class_correct else "✗"
            print(
                f"[{idx:02d}/{total:02d}] {status_char} Expected: {exp_type:<8} Actual: {envelope.type_name:<8} ({elapsed:.2f}s)"
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
    }

    # Save run
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{active_llm.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print("EVALUATION RESULTS")
    print("=" * 65)
    print(f"Model:                   {results['model_name']} ({results['model_id']})")
    print(f"Classification Accuracy: {results['classification_accuracy']}%")
    print(f"Field Accuracy:          {results['field_accuracy']}%")
    print(f"Needs Review Fraction:   {results['needs_review_fraction'] * 100:.1f}%")
    print(f"Avg Latency per note:    {results['average_latency_sec']}s")
    print(f"VRAM used:               {results['vram_used_mb'] or 'N/A'} MB")
    print("-" * 65)
    print("Per-type accuracy:")
    for t, acc in results["per_type_accuracy"].items():
        print(f"  {t:<10}: {acc}%")
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
