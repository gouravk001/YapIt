from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar
from uuid import uuid4

from app.api.models import NoteEnvelope, NoteWarning
from app.config.checks_config import PlausibilityRules
from app.config.models_config import TranscriptQualityRules
from app.config.types_config import TypeDefinition
from app.errors import NotANoteError, UnclearAudioError, UnknownTypeError
from app.pipeline.classify import classify
from app.pipeline.extract import extract
from app.pipeline.plausibility import find_concerns
from app.pipeline.plausibility_check import check_plausibility
from app.pipeline.refine import fallback_summary, refine
from app.pipeline.resolve import resolve
from app.pipeline.transcript_check import find_transcript_problem
from app.pipeline.validate import validate
from app.providers.base import LLM, Transcriber
from app.resolvers.dates import capture_day

logger = logging.getLogger(__name__)

T = TypeVar("T")

_NOT_A_NOTE_MESSAGE = (
    "That didn't sound like a note. Try saying what you want to remember, "
    'for example "Ravi owes me 500 rupees".'
)


StageCallback = Callable[[str], None]


def _no_stage(stage: str) -> None:
    """Default stage callback for callers that don't show progress."""


def _timed(step: str, fn: Callable[[], T], on_stage: StageCallback = _no_stage) -> T:
    on_stage(step)
    started = time.perf_counter()
    result = fn()
    logger.info("%s took %.3fs", step, time.perf_counter() - started)
    return result


class PipelineService:
    """Runs the note pipeline. Model calls block, so each public method runs in a worker thread
    to keep the event loop free for other requests."""

    def __init__(
        self,
        transcriber: Transcriber,
        llm: LLM,
        types: list[TypeDefinition],
        quality_rules: TranscriptQualityRules | None = None,
        plausibility_rules: PlausibilityRules | None = None,
    ) -> None:
        self._transcriber = transcriber
        self._llm = llm
        self._types = types
        self._type_map = {t.name: t for t in types}
        self._quality_rules = quality_rules
        self._plausibility_rules = plausibility_rules

    async def process_audio(
        self,
        audio_path: str,
        captured_at: str,
        timezone: str,
        on_stage: StageCallback = _no_stage,
    ) -> NoteEnvelope:
        """Run the full pipeline on a recording. on_stage is called from the worker thread
        as each stage starts: transcribe, classify, extract, refine, check."""
        return await asyncio.to_thread(
            self._process_audio, audio_path, captured_at, timezone, on_stage
        )

    async def process_text(
        self,
        transcript: str,
        captured_at: str,
        timezone: str,
        on_stage: StageCallback = _no_stage,
    ) -> NoteEnvelope:
        return await asyncio.to_thread(
            self._process_text, transcript, captured_at, timezone, on_stage
        )

    async def retype(
        self, transcript: str, type_name: str, captured_at: str, timezone: str
    ) -> NoteEnvelope:
        type_def = self._type_map.get(type_name)
        if not type_def:
            raise UnknownTypeError(f"Unknown note type: {type_name!r}")
        return await asyncio.to_thread(self._draft, transcript, type_def, captured_at, timezone)

    def _process_audio(
        self, audio_path: str, captured_at: str, timezone: str, on_stage: StageCallback
    ) -> NoteEnvelope:
        transcription = _timed(
            "transcribe", lambda: self._transcriber.transcribe(audio_path), on_stage
        )
        if self._quality_rules is not None:
            problem = find_transcript_problem(transcription, self._quality_rules)
            if problem:
                logger.info("Rejected unclear transcript: %s", problem)
                raise UnclearAudioError(problem, transcript=transcription.text)
        return self._process_text(transcription.text, captured_at, timezone, on_stage)

    def _process_text(
        self, transcript: str, captured_at: str, timezone: str, on_stage: StageCallback
    ) -> NoteEnvelope:
        classification = _timed(
            "classify", lambda: classify(transcript, self._types, self._llm), on_stage
        )
        if not classification.is_note:
            raise NotANoteError(_NOT_A_NOTE_MESSAGE, transcript=transcript)
        return self._draft(transcript, classification.type_def, captured_at, timezone, on_stage)

    def _draft(
        self,
        transcript: str,
        type_def: TypeDefinition,
        captured_at: str,
        timezone: str,
        on_stage: StageCallback = _no_stage,
    ) -> NoteEnvelope:
        raw_fields = _timed("extract", lambda: extract(transcript, type_def, self._llm), on_stage)
        fields = resolve(raw_fields, type_def, timezone, captured_at)

        refined = _timed(
            "refine", lambda: refine(transcript, type_def, fields, self._llm), on_stage
        )
        if refined is None:
            summary = fallback_summary(transcript)
        else:
            fields = resolve(refined.fields, type_def, timezone, captured_at)
            summary = refined.summary

        warnings = self._warnings(transcript, fields, type_def, captured_at, timezone, on_stage)

        return NoteEnvelope(
            id=str(uuid4()),
            created_at=captured_at,
            timezone=timezone,
            transcript=transcript,
            type_name=type_def.name,
            type_version=type_def.version,
            summary=summary,
            fields=fields,
            status="needs_review",
            missing_fields=validate(fields, type_def),
            warnings=warnings,
        )

    def _warnings(
        self,
        transcript: str,
        fields: dict[str, Any],
        type_def: TypeDefinition,
        captured_at: str,
        timezone: str,
        on_stage: StageCallback,
    ) -> list[NoteWarning]:
        if self._plausibility_rules is None:
            return []
        on_stage("check")
        concerns = find_concerns(fields, type_def, self._plausibility_rules, captured_at, timezone)
        if concerns:
            return [NoteWarning(field=c.field, message=c.message) for c in concerns]
        # The rules are precise and free, so the model is only asked when they found nothing;
        # that also avoids warning twice about the same value.
        today = capture_day(captured_at, timezone)
        reason = _timed("check", lambda: check_plausibility(transcript, today, self._llm))
        return [NoteWarning(message=reason)] if reason else []
