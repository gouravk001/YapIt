from __future__ import annotations

import logging
from typing import Any

import av
import numpy as np

from app.errors import TranscriptionError
from app.providers.base import Transcriber, Transcription
from app.providers.cuda_libs import preload_cuda_libraries
from app.providers.model_download import ensure_whisper_model

logger = logging.getLogger(__name__)

# PyAV 19.0.0+ removed the 'metadata_errors' parameter from av.open()
# which faster-whisper passes in decode_audio(). This shim ensures compatibility.
_orig_av_open = av.open


def _compat_av_open(*args: Any, **kwargs: Any) -> Any:
    kwargs.pop("metadata_errors", None)
    return _orig_av_open(*args, **kwargs)


av.open = _compat_av_open


# One second of silence at Whisper's 16 kHz sample rate: enough to run the model once.
_CHECK_SAMPLES = 16_000


def _check_model_runs(model: Any) -> None:
    """Run one tiny transcription. Some GPU problems, such as a missing CUDA library, only appear
    when audio is processed, not when the model loads."""
    segments, _ = model.transcribe(np.zeros(_CHECK_SAMPLES, dtype=np.float32), vad_filter=False)
    list(segments)


class WhisperProvider(Transcriber):
    """Transcriber backed by faster-whisper. Uses the GPU if it actually works, else the CPU."""

    def __init__(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        device_fallback: str,
        compute_type_fallback: str,
        vad_filter: bool,
        cuda_library_dirs: list[str],
    ) -> None:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]

        self._vad_filter = vad_filter
        preload_cuda_libraries(cuda_library_dirs)
        # Loading from a local path keeps startup offline once the model is cached.
        model_path = ensure_whisper_model(model_name)
        try:
            self._model = WhisperModel(model_path, device=device, compute_type=compute_type)
            _check_model_runs(self._model)
            self.device = device
        except Exception as exc:
            logger.warning(
                "Whisper can't run on %s (%s): %s. Falling back to %s/%s, which is slower.",
                device,
                compute_type,
                exc,
                device_fallback,
                compute_type_fallback,
            )
            self._model = WhisperModel(
                model_path, device=device_fallback, compute_type=compute_type_fallback
            )
            self.device = device_fallback
        logger.info("WhisperProvider ready on %s", self.device)

    def transcribe(self, audio_path: str) -> Transcription:
        try:
            segments, info = self._model.transcribe(audio_path, vad_filter=self._vad_filter)
            segments = list(segments)
        except av.error.FFmpegError as exc:
            raise TranscriptionError("The uploaded audio could not be decoded.") from exc

        text = " ".join(segment.text.strip() for segment in segments).strip()
        total_duration = sum(segment.end - segment.start for segment in segments)
        if not segments or total_duration <= 0:
            return Transcription(text=text, duration_seconds=info.duration)

        def weighted(attr: str) -> float:
            return (
                sum(getattr(seg, attr) * (seg.end - seg.start) for seg in segments) / total_duration
            )

        return Transcription(
            text=text,
            avg_logprob=weighted("avg_logprob"),
            no_speech_prob=weighted("no_speech_prob"),
            duration_seconds=info.duration,
        )
