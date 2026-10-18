from __future__ import annotations

import pytest
from huggingface_hub.errors import LocalEntryNotFoundError

from app.providers import model_download


class FakeHub:
    def __init__(self, cached: bool, online: bool = True) -> None:
        self.cached = cached
        self.online = online
        self.downloads = 0

    def __call__(self, name: str, local_files_only: bool = False) -> str:
        if self.cached:
            return f"/cache/{name}"
        if local_files_only:
            raise LocalEntryNotFoundError("not cached")
        if not self.online:
            raise ConnectionError("offline")
        self.downloads += 1
        self.cached = True
        return f"/cache/{name}"


def test_cached_model_needs_no_download(monkeypatch):
    hub = FakeHub(cached=True)
    monkeypatch.setattr(model_download, "download_model", hub)
    assert model_download.ensure_whisper_model("small.en") == "/cache/small.en"
    assert hub.downloads == 0


def test_missing_model_is_downloaded_once(monkeypatch):
    hub = FakeHub(cached=False)
    monkeypatch.setattr(model_download, "download_model", hub)
    model_download.ensure_whisper_model("small.en")
    model_download.ensure_whisper_model("small.en")
    assert hub.downloads == 1


def test_missing_model_offline_gives_clear_error(monkeypatch):
    monkeypatch.setattr(model_download, "download_model", FakeHub(cached=False, online=False))
    with pytest.raises(RuntimeError, match="Connect to the internet once"):
        model_download.ensure_whisper_model("small.en")
