from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import uuid4

from app.api.models import NoteEnvelope
from app.config.types_config import TypeDefinition
from app.errors import UnknownTypeError
from app.pipeline.classify import classify
from app.pipeline.extract import extract
from app.pipeline.resolve import resolve
from app.pipeline.validate import validate
from app.providers.base import LLM, Transcriber

logger = logging.getLogger(__name__)


class PipelineService:
    """Runs the note pipeline. Model calls block, so each public method runs in a worker thread
    to keep the event loop free for other requests."""

    def __init__(
        self,
        transcriber: Transcriber,
        llm: LLM,
        types: list[TypeDefinition],
    ) -> None:
        self._transcriber = transcriber
        self._llm = llm
        self._types = types
        self._type_map = {t.name: t for t in types}

    async def process_audio(self, audio_path: str, captured_at: str, timezone: str) -> NoteEnvelope:
        return await asyncio.to_thread(self._process_audio, audio_path, captured_at, timezone)

    async def process_text(self, transcript: str, captured_at: str, timezone: str) -> NoteEnvelope:
        return await asyncio.to_thread(self._process_text, transcript, captured_at, timezone)

    async def retype(
        self, transcript: str, type_name: str, captured_at: str, timezone: str
    ) -> NoteEnvelope:
        type_def = self._type_map.get(type_name)
        if not type_def:
            raise UnknownTypeError(f"Unknown note type: {type_name!r}")
        return await asyncio.to_thread(self._retype, transcript, type_def, captured_at, timezone)

    def _process_audio(self, audio_path: str, captured_at: str, timezone: str) -> NoteEnvelope:
        t0 = time.perf_counter()
        transcript = self._transcriber.transcribe(audio_path)
        logger.info("Transcribe completed in %.3fs: %r", time.perf_counter() - t0, transcript[:60])
        return self._process_text(transcript, captured_at, timezone)

    def _process_text(self, transcript: str, captured_at: str, timezone: str) -> NoteEnvelope:
        # Step 1: Classify
        t1 = time.perf_counter()
        type_def = classify(transcript, self._types, self._llm)
        logger.info("Classified in %.3fs as type=%s", time.perf_counter() - t1, type_def.name)

        # Step 2: Extract
        t2 = time.perf_counter()
        raw_fields = extract(transcript, type_def, self._llm)
        logger.info("Extracted in %.3fs for %s", time.perf_counter() - t2, type_def.name)

        summary = self._build_summary(raw_fields, type_def.name, transcript)

        # Step 3: Resolve
        t3 = time.perf_counter()
        resolved = resolve(raw_fields, type_def, timezone, captured_at)
        logger.info("Resolved fields in %.3fs", time.perf_counter() - t3)

        # Step 4: Validate
        missing = validate(resolved, type_def)

        # Retry once if required fields were missed
        if missing:
            logger.info("Missing required fields %s, retrying extraction once...", missing)
            try:
                raw_retry = extract(transcript, type_def, self._llm)
                resolved_retry = resolve(raw_retry, type_def, timezone, captured_at)
                missing_retry = validate(resolved_retry, type_def)
                if len(missing_retry) < len(missing):
                    resolved = resolved_retry
                    missing = missing_retry
                    summary = self._build_summary(raw_retry, type_def.name, transcript)
            except Exception as retry_err:
                logger.warning("Extraction retry failed: %s", retry_err)

        return NoteEnvelope(
            id=str(uuid4()),
            created_at=captured_at,
            timezone=timezone,
            transcript=transcript,
            type_name=type_def.name,
            type_version=type_def.version,
            summary=summary,
            fields=resolved,
            status="needs_review",
            missing_fields=missing,
        )

    def _retype(
        self, transcript: str, type_def: TypeDefinition, captured_at: str, timezone: str
    ) -> NoteEnvelope:
        raw_fields = extract(transcript, type_def, self._llm)
        summary = self._build_summary(raw_fields, type_def.name, transcript)
        resolved = resolve(raw_fields, type_def, timezone, captured_at)
        missing = validate(resolved, type_def)

        return NoteEnvelope(
            id=str(uuid4()),
            created_at=captured_at,
            timezone=timezone,
            transcript=transcript,
            type_name=type_def.name,
            type_version=type_def.version,
            summary=summary,
            fields=resolved,
            status="needs_review",
            missing_fields=missing,
        )

    def _build_summary(self, raw_fields: dict[str, Any], type_name: str, transcript: str) -> str:
        """Create a short, clean one-line summary from fields or transcript."""
        if "summary" in raw_fields and raw_fields["summary"]:
            return str(raw_fields.pop("summary")).strip()

        if type_name == "payment":
            person = raw_fields.get("person") or "Someone"
            amount_dict = raw_fields.get("amount")
            amount_str = ""
            if isinstance(amount_dict, dict):
                amount_str = f" {amount_dict.get('amount', '')} {amount_dict.get('currency', '')}"
            elif amount_dict:
                amount_str = f" {amount_dict}"
            direction = raw_fields.get("direction")
            if direction == "they_owe_me":
                return f"{person} owes{amount_str}"
            elif direction == "i_owe_them":
                return f"Owe {person}{amount_str}"
            return f"Payment: {person}{amount_str}"

        if type_name == "promise":
            person = raw_fields.get("person") or "Someone"
            commitment = raw_fields.get("commitment") or "commitment"
            return f"{person}: {commitment}"

        if type_name == "event":
            title = raw_fields.get("title") or "Event"
            date_val = raw_fields.get("date")
            date_str = (
                f" on {date_val.get('resolved') or date_val.get('spoken')}"
                if isinstance(date_val, dict)
                else ""
            )
            return f"{title}{date_str}"

        if type_name == "info":
            topic = raw_fields.get("topic") or "Info"
            return f"Info: {topic}"

        # General
        clean = transcript.strip().replace("\n", " ")
        return clean[:70] + "..." if len(clean) > 70 else clean
