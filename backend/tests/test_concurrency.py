from __future__ import annotations

import asyncio
import threading

from httpx import ASGITransport, AsyncClient

from app.config.loader import load_types
from app.main import app
from app.providers.base import LLM, Transcriber
from app.services.pipeline_service import PipelineService


class UnusedTranscriber(Transcriber):
    def transcribe(self, audio_path: str) -> str:
        raise AssertionError("not used in this test")


class GatedLLM(LLM):
    """Blocks its thread until released, like a slow model call."""

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()

    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        self.started.set()
        self.release.wait(timeout=5)
        return {"type_name": "general", "confidence": 1.0}


async def test_slow_model_call_does_not_block_other_requests():
    llm = GatedLLM()
    app.state.pipeline_service = PipelineService(UnusedTranscriber(), llm, load_types())
    payload = {
        "transcript": "Just thinking out loud.",
        "captured_at": "2026-10-17T10:00:00+05:30",
        "timezone": "Asia/Kolkata",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        processing = asyncio.create_task(client.post("/notes/process-text", json=payload))
        await asyncio.to_thread(llm.started.wait, 5)

        health = await asyncio.wait_for(client.get("/health"), timeout=1)
        assert health.status_code == 200
        assert not processing.done()

        llm.release.set()
        assert (await processing).status_code == 200
