"""The benchmark's model list (models.yaml) and the choice of which models to run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

THINKING_CAPABILITY = "thinking"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    tag: str
    label: str
    think: bool | None
    options: dict[str, Any]


def _parse_entry(model_id: str, entry: Any, defaults: dict[str, Any]) -> ModelSpec:
    if isinstance(entry, str):
        return ModelSpec(model_id, entry, entry, None, dict(defaults))
    if not isinstance(entry, dict):
        raise ValueError(f"Model {model_id!r} must be an Ollama tag or a mapping with a 'tag'.")
    if "tag" not in entry:
        raise ValueError(f"Model {model_id!r} needs a 'tag' (its Ollama name, e.g. qwen3.5:4b).")
    return ModelSpec(
        id=model_id,
        tag=entry["tag"],
        label=entry.get("label", entry["tag"]),
        think=entry.get("think"),
        options={**defaults, **entry.get("options", {})},
    )


def parse_models(raw: dict[str, Any]) -> list[ModelSpec]:
    """Read models.yaml. An entry is either just an Ollama tag, or a mapping with a tag and
    optional label, think and per-model options (which override `defaults`)."""
    models = raw.get("models") or {}
    if not models:
        raise ValueError("models.yaml lists no models.")
    defaults = raw.get("defaults") or {}
    return [_parse_entry(model_id, entry, defaults) for model_id, entry in models.items()]


def resolve_think(spec: ModelSpec, capabilities: list[str]) -> bool | None:
    """Thinking models get thinking switched off unless models.yaml says otherwise: the hidden
    reasoning would use up the reply budget and cut the JSON short. None means "don't send it",
    for models that don't support the option at all."""
    if spec.think is not None:
        return spec.think
    return False if THINKING_CAPABILITY in capabilities else None


def models_to_run(
    specs: list[ModelSpec],
    done: set[str],
    only: list[str] | None = None,
    rerun: bool = False,
) -> list[ModelSpec]:
    """The models to benchmark now: the ones asked for, otherwise every model without a result
    on the current test set (or all of them with rerun)."""
    by_id = {s.id: s for s in specs}
    if only:
        unknown = [m for m in only if m not in by_id]
        if unknown:
            raise ValueError(f"unknown model ids: {', '.join(unknown)} (see models.yaml)")
        return [by_id[m] for m in only]
    return [s for s in specs if rerun or s.id not in done]
