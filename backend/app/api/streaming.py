from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from fastapi.responses import StreamingResponse

from app.api.models import NoteEnvelope
from app.errors import AppError
from app.services.pipeline_service import StageCallback

logger = logging.getLogger(__name__)

NDJSON = "application/x-ndjson"


def _line(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode()


def _result_line(task: asyncio.Task[NoteEnvelope]) -> bytes:
    try:
        return _line({"draft": task.result().model_dump()})
    except AppError as exc:
        return _line({"error": exc.code, "detail": exc.message, **exc.extra})
    except Exception:
        logger.exception("Streaming pipeline failed")
        return _line({"error": "InternalServerError", "detail": "An unexpected error occurred."})


def stream_pipeline(
    run: Callable[[StageCallback], Awaitable[NoteEnvelope]],
    on_finish: Callable[[], None] = lambda: None,
) -> StreamingResponse:
    """Stream {"stage": ...} lines while the pipeline runs, then one {"draft": ...} or
    {"error": ...} line. on_finish runs once the pipeline has really stopped, even if the
    client disconnects first."""

    async def events() -> AsyncIterator[bytes]:
        loop = asyncio.get_running_loop()
        stages: asyncio.Queue[str] = asyncio.Queue()
        # The pipeline reports stages from its worker thread.
        task = asyncio.ensure_future(
            run(lambda stage: loop.call_soon_threadsafe(stages.put_nowait, stage))
        )
        try:
            while not task.done() or not stages.empty():
                next_stage = asyncio.ensure_future(stages.get())
                await asyncio.wait({next_stage, task}, return_when=asyncio.FIRST_COMPLETED)
                if next_stage.done():
                    yield _line({"stage": next_stage.result()})
                else:
                    next_stage.cancel()
            yield _result_line(task)
        finally:
            if task.done():
                on_finish()
            else:
                task.add_done_callback(lambda finished: _finish_late(finished, on_finish))

    return StreamingResponse(events(), media_type=NDJSON)


def _finish_late(task: asyncio.Task[NoteEnvelope], on_finish: Callable[[], None]) -> None:
    if not task.cancelled() and task.exception() is not None:
        logger.info("Pipeline for a disconnected client ended with: %s", task.exception())
    on_finish()
