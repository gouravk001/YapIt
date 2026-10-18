from __future__ import annotations

import pytest

from harness.models import ModelSpec, models_to_run, parse_models, resolve_think

RAW = {
    "defaults": {"temperature": 0.1, "num_predict": 400},
    "models": {
        "gemma3-4b": {"tag": "gemma3:4b", "label": "Gemma 3 4B"},
        "phi": "phi4-mini",
        "qwen": {"tag": "qwen3.5:4b", "think": True, "options": {"num_predict": 2048}},
    },
}


def test_short_and_full_entries_are_both_accepted():
    specs = parse_models(RAW)
    assert [s.id for s in specs] == ["gemma3-4b", "phi", "qwen"]
    assert specs[1] == ModelSpec(
        id="phi", tag="phi4-mini", label="phi4-mini", think=None, options=RAW["defaults"]
    )
    assert specs[0].label == "Gemma 3 4B"


def test_model_options_override_the_defaults():
    qwen = parse_models(RAW)[2]
    assert qwen.options == {"temperature": 0.1, "num_predict": 2048}
    assert qwen.think is True


@pytest.mark.parametrize(
    ("models", "message"),
    [
        ({"x": {"label": "no tag"}}, "needs a 'tag'"),
        ({"x": 42}, "must be an Ollama tag"),
        ({}, "no models"),
    ],
)
def test_invalid_entries_give_clear_errors(models, message):
    with pytest.raises(ValueError, match=message):
        parse_models({"defaults": {}, "models": models})


def test_thinking_is_switched_off_automatically_for_thinking_models():
    spec = parse_models(RAW)[1]
    assert resolve_think(spec, ["completion", "thinking"]) is False
    assert resolve_think(spec, ["completion", "tools"]) is None


def test_an_explicit_think_setting_wins():
    qwen = parse_models(RAW)[2]
    assert resolve_think(qwen, ["completion", "thinking"]) is True


def test_only_models_without_a_current_result_run_by_default():
    specs = parse_models(RAW)
    assert [s.id for s in models_to_run(specs, done={"gemma3-4b"})] == ["phi", "qwen"]
    assert [s.id for s in models_to_run(specs, done={"gemma3-4b"}, rerun=True)] == [
        "gemma3-4b",
        "phi",
        "qwen",
    ]
    assert [s.id for s in models_to_run(specs, done=set(), only=["qwen"])] == ["qwen"]


def test_unknown_requested_model_is_an_error():
    with pytest.raises(ValueError, match="unknown model ids: nope"):
        models_to_run(parse_models(RAW), done=set(), only=["nope"])
