from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config.loader import load_types
from app.errors import ModelUnavailableError
from app.main import app
from app.providers.base import LLM, Transcriber
from app.services.note_service import NoteService
from app.services.pipeline_service import PipelineService
from app.storage.database import init_db

TEXT_PAYLOAD = {
    "transcript": "Ravi owes me 500 rupees.",
    "captured_at": "2026-10-17T10:00:00+05:30",
    "timezone": "Asia/Kolkata",
}


class UnusedTranscriber(Transcriber):
    def transcribe(self, audio_path: str) -> str:
        raise AssertionError("not used in these tests")


class RaisingLLM(LLM):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        raise self._exc


async def _client_with_llm(tmp_path, llm: LLM) -> AsyncClient:
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    types = load_types()
    app.state.type_definitions = types
    app.state.note_service = NoteService(db_path=db_path)
    app.state.pipeline_service = PipelineService(UnusedTranscriber(), llm, types)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client(tmp_path):
    async with await _client_with_llm(tmp_path, RaisingLLM(RuntimeError("unused"))) as c:
        yield c


async def test_missing_note_returns_not_found_shape(client):
    res = await client.delete("/notes/does-not-exist")
    assert res.status_code == 404
    assert res.json() == {"error": "NotFound", "detail": "Note 'does-not-exist' not found."}


async def test_unknown_route_uses_same_shape(client):
    res = await client.get("/nope")
    assert res.status_code == 404
    assert res.json()["error"] == "NotFound"


async def test_validation_error_is_a_readable_string(client):
    res = await client.post("/notes/process-text", json={"transcript": "hi"})
    body = res.json()
    assert res.status_code == 422
    assert body["error"] == "ValidationError"
    assert "captured_at: Field required" in body["detail"]


async def test_retype_unknown_type_is_bad_request(client):
    res = await client.post("/notes/retype", json={**TEXT_PAYLOAD, "type_name": "recipe"})
    assert res.status_code == 400
    assert res.json() == {"error": "UnknownType", "detail": "Unknown note type: 'recipe'"}


async def test_model_unavailable_is_service_unavailable(tmp_path):
    llm = RaisingLLM(ModelUnavailableError("Cannot reach Ollama."))
    async with await _client_with_llm(tmp_path, llm) as c:
        res = await c.post("/notes/process-text", json=TEXT_PAYLOAD)
    assert res.status_code == 503
    assert res.json() == {"error": "ModelUnavailable", "detail": "Cannot reach Ollama."}


async def test_unexpected_error_does_not_leak_internals(tmp_path):
    llm = RaisingLLM(RuntimeError("secret internal path /home/x"))
    async with await _client_with_llm(tmp_path, llm) as c:
        res = await c.post(
            "/notes/process-text", json=TEXT_PAYLOAD, headers={"Origin": "http://localhost:5173"}
        )
    assert res.status_code == 500
    assert res.json() == {"error": "InternalServerError", "detail": "An unexpected error occurred."}
    assert res.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_unclear_audio_reports_what_was_heard(tmp_path):
    from app.config.models_config import TranscriptQualityRules
    from app.providers.base import Transcription

    class MumbleTranscriber(Transcriber):
        def transcribe(self, audio_path: str) -> Transcription:
            return Transcription(text="Thanks for watching!", avg_logprob=-0.2, no_speech_prob=0.1)

    rules = TranscriptQualityRules(
        min_words=2,
        min_avg_logprob=-1.0,
        max_no_speech_prob=0.6,
        known_hallucinations=["thanks for watching"],
    )
    async with await _client_with_llm(tmp_path, RaisingLLM(RuntimeError("unused"))) as c:
        app.state.pipeline_service = PipelineService(
            MumbleTranscriber(), RaisingLLM(RuntimeError()), load_types(), rules
        )
        res = await c.post(
            "/notes/process",
            files={"audio": ("rec.webm", b"fake", "audio/webm")},
            data={"captured_at": TEXT_PAYLOAD["captured_at"], "timezone": "Asia/Kolkata"},
        )
    body = res.json()
    assert res.status_code == 422
    assert body["error"] == "UnclearAudio"
    assert body["transcript"] == "Thanks for watching!"
