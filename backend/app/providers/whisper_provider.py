from __future__ import annotations

import logging
from typing import Any

from app.providers.base import Transcriber

logger = logging.getLogger(__name__)

# PyAV 19.0.0+ removed the 'metadata_errors' parameter from av.open()
# which faster-whisper passes in decode_audio(). This shim ensures compatibility.
try:
    import av

    _orig_av_open = av.open

    def _compat_av_open(*args: Any, **kwargs: Any) -> Any:
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)

    av.open = _compat_av_open
except Exception:
    pass


class WhisperProvider(Transcriber):
    """Transcriber backed by faster-whisper. Tries GPU first, falls back to CPU."""

    def __init__(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        device_fallback: str,
        compute_type_fallback: str,
    ) -> None:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]

        try:
            self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
            logger.info("WhisperProvider loaded on %s with compute_type=%s", device, compute_type)
        except Exception as gpu_exc:
            logger.warning(
                "Failed to load Whisper on %s (%s): %s — falling back to %s/%s",
                device,
                compute_type,
                gpu_exc,
                device_fallback,
                compute_type_fallback,
            )
            self._model = WhisperModel(
                model_name,
                device=device_fallback,
                compute_type=compute_type_fallback,
            )
            logger.info(
                "WhisperProvider loaded on %s with compute_type=%s",
                device_fallback,
                compute_type_fallback,
            )

    def transcribe(self, audio_path: str) -> str:
        segments, _ = self._model.transcribe(audio_path)
        return " ".join(segment.text.strip() for segment in segments)
