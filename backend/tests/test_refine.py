from __future__ import annotations

import pytest

from app.config.loader import load_types
from app.pipeline.refine import fallback_summary, refine
from app.providers.base import LLM
from app.resolvers.money import format_money

PAYMENT = next(t for t in load_types() if t.name == "payment")


class ScriptedLLM(LLM):
    def __init__(self, *responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        self.prompts.append(prompt)
        return self.responses.pop(0)


@pytest.mark.parametrize(
    ("money", "expected"),
    [
        ({"amount": 150000.0, "currency": "INR"}, "₹1,50,000"),
        ({"amount": 12345678.0, "currency": "INR"}, "₹1,23,45,678"),
        ({"amount": 500.0, "currency": "INR"}, "₹500"),
        ({"amount": 2500.5, "currency": "INR"}, "₹2,500.50"),
        ({"amount": 1500000.0, "currency": "USD"}, "$1,500,000"),
    ],
)
def test_format_money(money, expected):
    assert format_money(money) == expected


def test_fallback_summary_cuts_on_a_word():
    summary = fallback_summary("word " * 30)
    assert summary.endswith("…")
    assert len(summary) <= 71


def test_refine_shows_draft_in_spoken_form_and_returns_corrections():
    llm = ScriptedLLM(
        {
            "person": "Ram",
            "direction": "i_owe_them",
            "amount": "₹200",
            "due_date": "tomorrow",
            "note": "",
            "summary": "  Pay Ram ₹200 tomorrow. ",
        }
    )
    draft = {
        "person": "Ram",
        "direction": "they_owe_me",
        "amount": {"amount": 200.0, "currency": "INR"},
        "due_date": {"spoken": "tomorrow", "resolved": "2026-10-18"},
    }

    refined = refine("I have to give Ram 200 rupees tomorrow", PAYMENT, draft, llm)

    assert '"amount": "₹200"' in llm.prompts[0]
    assert '"due_date": "tomorrow"' in llm.prompts[0]
    assert refined.fields["direction"] == "i_owe_them"
    assert refined.summary == "Pay Ram ₹200 tomorrow"


def test_refine_keeps_a_required_value_it_dropped():
    llm = ScriptedLLM(
        {
            "person": "",
            "direction": "they_owe_me",
            "amount": "₹500",
            "due_date": "",
            "note": "",
            "summary": "Ravi owes me ₹500",
        }
    )
    draft = {
        "person": "Ravi",
        "direction": "they_owe_me",
        "amount": {"amount": 500.0, "currency": "INR"},
    }

    refined = refine("Ravi owes me 500", PAYMENT, draft, llm)

    assert refined.fields["person"] == "Ravi"
    assert refined.fields["due_date"] == ""


def test_refine_retries_once_then_gives_up():
    llm = ScriptedLLM("not json", "still not json")
    assert refine("Ravi owes me 500", PAYMENT, {}, llm) is None
    assert len(llm.prompts) == 2
