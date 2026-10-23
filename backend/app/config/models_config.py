from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TranscriptQualityRules(BaseModel):
    """Thresholds below which a transcript is treated as unclear and the user asked to retry."""

    min_words: int
    max_seconds: float
    min_avg_logprob: float
    max_no_speech_prob: float
    known_hallucinations: list[str] = Field(default_factory=list)


class ModelEntry(BaseModel):
    id: str
    role: Literal["transcriber", "llm"]
    runtime: Literal["faster-whisper", "ollama"]
    model_name: str
    vram_mb: int
    # faster-whisper optional fields
    compute_type: str | None = None
    device: str | None = None
    device_fallback: str | None = None
    compute_type_fallback: str | None = None
    vad_filter: bool = False
    cuda_library_dirs: list[str] = Field(default_factory=list)
    quality: TranscriptQualityRules | None = None
    # ollama optional fields
    temperature: float | None = None
    top_p: float | None = None
    num_ctx: int | None = None
    num_predict: int | None = None


class ActiveModels(BaseModel):
    transcriber: str
    llm: str


class ModelRegistry(BaseModel):
    models: list[ModelEntry]
    active: ActiveModels

    def get_active(self, role: str) -> ModelEntry:
        """Return the active ModelEntry for a given role ('transcriber' or 'llm')."""
        active_id = getattr(self.active, role, None)
        if active_id is None:
            raise ValueError(f"Unknown role: {role!r}")
        for model in self.models:
            if model.id == active_id:
                return model
        raise ValueError(f"Active {role!r} model id {active_id!r} not found in model registry.")
