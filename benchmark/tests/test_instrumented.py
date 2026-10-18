from __future__ import annotations

from app.providers.base import LLM
from harness.instrumented import InstrumentedLLM


class Replies(LLM):
    def __init__(self, *replies):
        self.replies = list(replies)

    def generate(self, prompt, json_schema=None):
        return self.replies.pop(0)


def test_counts_calls_and_malformed_structured_replies():
    llm = InstrumentedLLM(Replies({"ok": 1}, "not json", "free text"))
    assert llm.generate("a", {"type": "object"}) == {"ok": 1}
    assert llm.generate("b", {"type": "object"}) == "not json"
    assert llm.generate("c") == "free text"
    assert (llm.calls, llm.malformed, len(llm.call_seconds)) == (3, 1, 3)
