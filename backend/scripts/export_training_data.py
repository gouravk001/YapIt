import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.loader import load_types
from app.pipeline.prompt_builder import classification_prompt, extraction_prompt


def export_dataset(dataset_path: Path, output_path: Path) -> None:
    types = load_types()
    type_map = {t.name: t for t in types}

    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data["samples"]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as out:
        for s in samples:
            transcript = s["transcript"]
            expected_type = s["expected_type"]
            expected_fields = s.get("expected_fields", {})

            # 1. Classification training example
            cls_prompt = classification_prompt(transcript, types)
            cls_completion = json.dumps({"type_name": expected_type, "confidence": 1.0})
            cls_example = {
                "task": "classification",
                "sample_id": s["id"],
                "messages": [
                    {"role": "user", "content": cls_prompt},
                    {"role": "assistant", "content": cls_completion},
                ],
            }
            out.write(json.dumps(cls_example) + "\n")
            count += 1

            # 2. Extraction training example
            type_def = type_map.get(expected_type)
            if type_def:
                ext_prompt = extraction_prompt(transcript, type_def)
                ext_completion = json.dumps(expected_fields)
                ext_example = {
                    "task": "extraction",
                    "sample_id": s["id"],
                    "type": expected_type,
                    "messages": [
                        {"role": "user", "content": ext_prompt},
                        {"role": "assistant", "content": ext_completion},
                    ],
                }
                out.write(json.dumps(ext_example) + "\n")
                count += 1

    print(f"Exported {count} training examples to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export training data in exact prompt format")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("eval/dataset.json"),
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("fine_tune/train.jsonl"),
        help="Path to output JSONL file",
    )
    args = parser.parse_args()

    export_dataset(args.input, args.output)
