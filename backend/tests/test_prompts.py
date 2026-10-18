from __future__ import annotations

import pytest

from app.config.loader import load_types
from app.pipeline.prompt_builder import classification_prompt, extraction_prompt, refine_prompt

TYPES = load_types()


@pytest.mark.parametrize("type_def", TYPES, ids=[t.name for t in TYPES])
def test_prompts_build_for_every_configured_type(type_def):
    transcript = "Something to remember tomorrow."
    draft = {f.name: "" for f in type_def.fields}

    assert transcript in extraction_prompt(transcript, type_def)
    assert transcript in refine_prompt(transcript, type_def, draft)


def test_classification_prompt_lists_every_type():
    prompt = classification_prompt("hello", TYPES)
    assert all(f"- {t.name}:" in prompt for t in TYPES)


def test_examples_show_enum_labels_not_stored_values():
    payment = next(t for t in TYPES if t.name == "payment")
    prompt = extraction_prompt("x", payment)
    assert '"direction": "I will give the money"' in prompt
    assert '"direction": "i_owe_them"' not in prompt


def test_plausibility_prompt_states_today():
    from app.pipeline.prompt_builder import plausibility_prompt

    prompt = plausibility_prompt("Flight leaves yesterday", "Sunday 18 October 2026")
    assert "Today is Sunday 18 October 2026." in prompt
    assert '"""Flight leaves yesterday"""' in prompt
