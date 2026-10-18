from __future__ import annotations

from types import SimpleNamespace

import pytest

from harness import ollama_client


def _ps_sequence(monkeypatch, *loaded_lists):
    """Make ollama.ps() report these loaded models on successive calls (the last one repeats)."""
    replies = list(loaded_lists)

    def fake_ps():
        names = replies.pop(0) if len(replies) > 1 else replies[0]
        return SimpleNamespace(models=[SimpleNamespace(model=n) for n in names])

    monkeypatch.setattr(ollama_client.ollama, "ps", fake_ps)
    monkeypatch.setattr(ollama_client.time, "sleep", lambda s: None)


def test_waits_until_ollama_reports_nothing_loaded(monkeypatch):
    _ps_sequence(monkeypatch, ["gemma3:4b"], ["gemma3:4b"], [])
    ollama_client.wait_until_unloaded(timeout_s=5)


def test_gives_up_with_a_clear_error(monkeypatch):
    _ps_sequence(monkeypatch, ["gemma3:4b"])
    clock = iter(range(100))
    monkeypatch.setattr(ollama_client.time, "monotonic", lambda: next(clock))
    with pytest.raises(RuntimeError, match="still loaded after 3s: gemma3:4b"):
        ollama_client.wait_until_unloaded(timeout_s=3)


def _installed(monkeypatch, *tags):
    monkeypatch.setattr(
        ollama_client.ollama,
        "list",
        lambda: SimpleNamespace(models=[SimpleNamespace(model=t) for t in tags]),
    )


def test_installed_model_is_not_downloaded_again(monkeypatch):
    _installed(monkeypatch, "qwen3.5:4b", "phi4-mini:latest")
    monkeypatch.setattr(ollama_client.ollama, "pull", lambda *a, **k: pytest.fail("pulled"))
    assert ollama_client.ensure_downloaded("qwen3.5:4b", lambda done, total: None) is False
    assert ollama_client.ensure_downloaded("phi4-mini", lambda done, total: None) is False


def test_missing_model_is_downloaded_with_progress(monkeypatch):
    _installed(monkeypatch)
    events = [
        SimpleNamespace(status="pulling manifest", completed=None, total=None),
        SimpleNamespace(status="pulling a", completed=50, total=100),
        SimpleNamespace(status="pulling a", completed=100, total=100),
        SimpleNamespace(status="success", completed=None, total=None),
    ]
    pulled = []
    monkeypatch.setattr(
        ollama_client.ollama, "pull", lambda tag, stream: pulled.append(tag) or iter(events)
    )
    progress = []
    assert ollama_client.ensure_downloaded("llama3.2:3b", lambda d, t: progress.append((d, t)))
    assert pulled == ["llama3.2:3b"]
    assert progress == [(50, 100), (100, 100)]
