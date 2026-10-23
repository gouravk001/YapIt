from __future__ import annotations

from app.config.models_config import ModelRegistry
from app.providers.base import LLM, Transcriber
from app.providers.ollama_provider import OllamaProvider
from app.providers.whisper_provider import WhisperProvider


def create_providers(registry: ModelRegistry) -> tuple[Transcriber, LLM]:
    """Instantiate and return (Transcriber, LLM) from the active registry entries."""
    transcriber_entry = registry.get_active("transcriber")
    llm_entry = registry.get_active("llm")

    transcriber = WhisperProvider(
        model_name=transcriber_entry.model_name,
        device=transcriber_entry.device or "cpu",
        compute_type=transcriber_entry.compute_type or "int8",
        device_fallback=transcriber_entry.device_fallback or "cpu",
        compute_type_fallback=transcriber_entry.compute_type_fallback or "int8",
        vad_filter=transcriber_entry.vad_filter,
        cuda_library_dirs=transcriber_entry.cuda_library_dirs,
    )

    llm = OllamaProvider(llm_entry)

    return transcriber, llm
