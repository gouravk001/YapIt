from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config.loader import load_types
from app.main import app
from app.providers.base import LLM, Transcriber, Transcription
from app.services.pipeline_service import PipelineService
from app.storage.database import init_db


class MockTranscriber(Transcriber):
    def transcribe(self, audio_path: str) -> Transcription:
        return Transcription(
            text="Ravi owes me 500 rupees, he said he will pay by next Friday.",
            avg_logprob=-0.2,
            no_speech_prob=0.01,
        )


class MockLLM(LLM):
    def generate(self, prompt: str, json_schema: dict | None = None) -> str | dict:
        properties = (json_schema or {}).get("properties", {})
        if "kind" in properties:
            return {"kind": "note", "type_name": "payment"}
        if "summary" in properties:
            return {
                "person": "Ravi",
                "direction": "they_owe_me",
                "amount": "₹500",
                "due_date": "next Friday",
                "note": "",
                "summary": "Ravi owes me ₹500 by next Friday.",
            }
        return {
            "person": "ravi",
            "direction": "they_owe_me",
            "amount": "500 rupees",
            "due_date": "next Friday",
        }


@pytest.fixture
async def client(tmp_path):
    test_db = str(tmp_path / "test.db")
    await init_db(test_db)
    types = load_types()

    app.state.db_path = test_db
    app.state.types = types
    app.state.type_definitions = types
    from app.services.note_service import NoteService

    app.state.note_service = NoteService(db_path=test_db)
    app.state.pipeline_service = PipelineService(MockTranscriber(), MockLLM(), types)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_list_types(client):
    res = await client.get("/types")
    assert res.status_code == 200
    types = res.json()
    assert len(types) >= 5
    type_names = [t["name"] for t in types]
    assert "payment" in type_names
    assert "general" in type_names


async def test_process_text(client):
    payload = {
        "transcript": "Ravi owes me 500 rupees, he said he'll pay by next Friday.",
        "captured_at": "2026-10-17T10:00:00+05:30",
        "timezone": "Asia/Kolkata",
    }
    res = await client.post("/notes/process-text", json=payload)
    assert res.status_code == 200
    draft = res.json()
    assert draft["type_name"] == "payment"
    assert draft["status"] == "needs_review"
    assert draft["fields"]["person"] == "Ravi"
    assert draft["fields"]["amount"] == {"amount": 500.0, "currency": "INR"}
    assert draft["fields"]["due_date"] == {"spoken": "next Friday", "resolved": "2026-10-30"}
    assert draft["summary"] == "Ravi owes me ₹500 by next Friday"
    assert "note" not in draft["fields"]
    assert draft["missing_fields"] == []


async def test_save_and_list_note(client):
    note_payload = {
        "id": "test-note-1",
        "created_at": "2026-10-17T10:00:00+05:30",
        "timezone": "Asia/Kolkata",
        "transcript": "Meeting with Priya tomorrow",
        "type_name": "event",
        "type_version": 1,
        "summary": "Meeting with Priya tomorrow",
        "fields": {
            "title": "Meeting with Priya",
            "date": {"spoken": "tomorrow", "resolved": "2026-10-18"},
        },
        "status": "confirmed",
        "missing_fields": [],
    }

    # Save note
    res = await client.post("/notes", json=note_payload)
    assert res.status_code == 201

    # List notes
    list_res = await client.get("/notes")
    assert list_res.status_code == 200
    notes = list_res.json()
    assert len(notes) == 1
    assert notes[0]["id"] == "test-note-1"
    assert notes[0]["summary"] == "Meeting with Priya tomorrow"

    # Search filter
    search_res = await client.get("/notes?search=Priya")
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1

    # Delete note
    del_res = await client.delete("/notes/test-note-1")
    assert del_res.status_code == 204

    # Confirm deletion
    list_res_after = await client.get("/notes")
    assert len(list_res_after.json()) == 0


async def test_date_filter_and_order_compare_instants_across_offsets(client):
    base = {
        "timezone": "Asia/Kolkata",
        "transcript": "t",
        "type_name": "general",
        "type_version": 1,
        "summary": "s",
        "fields": {},
        "status": "confirmed",
        "missing_fields": [],
    }
    # 18:40Z, written with a +05:30 offset, and 19:10Z written in UTC.
    await client.post(
        "/notes", json={**base, "id": "early", "created_at": "2026-10-18T00:10:00+05:30"}
    )
    await client.post(
        "/notes", json={**base, "id": "late", "created_at": "2026-10-17T19:10:00.000Z"}
    )

    res = await client.get("/notes", params={"date_from": "2026-10-17T19:00:00.000Z"})
    assert [n["id"] for n in res.json()] == ["late"]

    res = await client.get("/notes")
    assert [n["id"] for n in res.json()] == ["late", "early"]
