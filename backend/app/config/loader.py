from __future__ import annotations

import os
from pathlib import Path

import yaml

from app.config.checks_config import PlausibilityRules
from app.config.models_config import ActiveModels, ModelEntry, ModelRegistry
from app.config.types_config import TypeDefinition


def _config_dir() -> Path:
    explicit = os.environ.get("CONFIG_DIR")
    if explicit:
        return Path(explicit)
    local = Path("config")
    if (local / "types.yaml").exists():
        return local
    backend_local = Path("backend/config")
    if (backend_local / "types.yaml").exists():
        return backend_local
    package_config = Path(__file__).resolve().parent.parent.parent / "config"
    return package_config


def load_types() -> list[TypeDefinition]:
    """Load and validate note type definitions from types.yaml."""
    types_path = _config_dir() / "types.yaml"
    if not types_path.exists():
        raise ValueError(f"Types config file not found: {types_path}")

    with types_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict) or "types" not in raw:
        raise ValueError(
            f"types.yaml must be a mapping with a top-level 'types' key. Got: {type(raw)}"
        )

    raw_types = raw["types"]
    if not isinstance(raw_types, list):
        raise ValueError(f"'types' in types.yaml must be a list. Got: {type(raw_types)}")

    definitions: list[TypeDefinition] = []
    for idx, entry in enumerate(raw_types):
        try:
            definitions.append(TypeDefinition.model_validate(entry))
        except Exception as exc:
            name = (
                entry.get("name", f"<index {idx}>") if isinstance(entry, dict) else f"<index {idx}>"
            )
            raise ValueError(f"Invalid type definition for {name!r}: {exc}") from exc

    return definitions


def load_model_registry() -> ModelRegistry:
    """Load and validate the model registry from models.yaml."""
    models_path = _config_dir() / "models.yaml"
    if not models_path.exists():
        raise ValueError(f"Models config file not found: {models_path}")

    with models_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError(f"models.yaml must be a mapping. Got: {type(raw)}")

    for required_key in ("models", "active"):
        if required_key not in raw:
            raise ValueError(f"models.yaml is missing required key: {required_key!r}")

    if not isinstance(raw["models"], list):
        raise ValueError(f"'models' in models.yaml must be a list. Got: {type(raw['models'])}")

    model_entries: list[ModelEntry] = []
    for idx, entry in enumerate(raw["models"]):
        try:
            model_entries.append(ModelEntry.model_validate(entry))
        except Exception as exc:
            model_id = (
                entry.get("id", f"<index {idx}>") if isinstance(entry, dict) else f"<index {idx}>"
            )
            raise ValueError(f"Invalid model entry for {model_id!r}: {exc}") from exc

    try:
        active = ActiveModels.model_validate(raw["active"])
    except Exception as exc:
        raise ValueError(f"Invalid 'active' block in models.yaml: {exc}") from exc

    return ModelRegistry(models=model_entries, active=active)


def load_checks() -> PlausibilityRules:
    """Load and validate the plausibility thresholds from checks.yaml."""
    checks_path = _config_dir() / "checks.yaml"
    if not checks_path.exists():
        raise ValueError(f"Checks config file not found: {checks_path}")

    with checks_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    try:
        return PlausibilityRules.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"Invalid checks.yaml: {exc}") from exc
