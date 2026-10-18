"""Runs test cases through the app's real text pipeline and records what happened."""

from __future__ import annotations

import time

from app.errors import NotANoteError
from app.services.pipeline_service import PipelineService
from harness.scoring import NOT_A_NOTE, Case, Outcome


class StageTimer:
    """Turns the pipeline's stage-start callbacks into seconds spent in each stage."""

    def __init__(self) -> None:
        self._starts: list[tuple[str, float]] = []

    def __call__(self, stage: str) -> None:
        self._starts.append((stage, time.perf_counter()))

    def durations(self, finished_at: float) -> dict[str, float]:
        ends = [start for _, start in self._starts[1:]] + [finished_at]
        return {stage: end - start for (stage, start), end in zip(self._starts, ends, strict=True)}


async def run_case(
    pipeline: PipelineService, case: Case, captured_at: str, timezone: str
) -> Outcome:
    """Process one transcript exactly as the app would and capture the result."""
    timer = StageTimer()
    started = time.perf_counter()
    try:
        draft = await pipeline.process_text(case.transcript, captured_at, timezone, timer)
    except NotANoteError:
        actual_type, fields, warnings = NOT_A_NOTE, {}, []
    except Exception as exc:  # recorded per case so one failure doesn't stop the run
        return Outcome(case_id=case.id, actual_type=None, error=f"{type(exc).__name__}: {exc}")
    else:
        actual_type = draft.type_name
        fields = draft.fields
        warnings = [w.message for w in draft.warnings]
    finished = time.perf_counter()
    return Outcome(
        case_id=case.id,
        actual_type=actual_type,
        fields=fields,
        warnings=warnings,
        latency_s=finished - started,
        stage_s=timer.durations(finished),
    )
