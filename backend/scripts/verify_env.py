#!/usr/bin/env python3
"""Milestone 1 verification script.

Checks GPU driver, ffmpeg, Ollama, faster-whisper GPU transcription,
and Gemma LLM response. Reports VRAM used when both are loaded.
Run from the backend directory with the venv active.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def check_nvidia() -> bool:
    section("NVIDIA GPU")
    result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines()[:6]:
            print(f"  {line}")
        ok("nvidia-smi succeeded")
        return True
    else:
        fail(result.stderr.strip() or "nvidia-smi failed")
        warn("Will attempt CPU fallback for whisper")
        return False


def check_ffmpeg() -> bool:
    section("ffmpeg")
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode == 0:
        ok(result.stdout.splitlines()[0])
        return True
    fail("ffmpeg not found — install with: sudo apt install ffmpeg")
    return False


def check_ollama() -> tuple[bool, str]:
    section("Ollama")
    result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        fail("ollama not in PATH — install from https://ollama.com")
        return False, ""
    ok(result.stdout.strip())

    # Check that the configured model is available
    from app.config.loader import load_model_registry

    registry = load_model_registry()
    llm_entry = registry.get_active("llm")
    model_name = llm_entry.model_name

    result2 = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if model_name in result2.stdout:
        ok(f"Model {model_name} found locally")
    else:
        warn(f"Model {model_name} not found — pulling now (this may take a while)...")
        subprocess.run(["ollama", "pull", model_name], check=True)
        ok(f"Pulled {model_name}")

    return True, model_name


def check_whisper_gpu(has_gpu: bool) -> tuple[bool, str]:
    section("faster-whisper transcription")
    try:
        import torch
        from faster_whisper import WhisperModel
    except ImportError as e:
        fail(f"Import error: {e} — run: pip install faster-whisper torch")
        return False, "import_error"

    from app.config.loader import load_model_registry

    registry = load_model_registry()
    entry = registry.get_active("transcriber")
    device = entry.device if has_gpu and torch.cuda.is_available() else entry.device_fallback
    compute_type = entry.compute_type if device == "cuda" else entry.compute_type_fallback

    print(f"  Loading {entry.model_name} on {device} ({compute_type})...")
    t0 = time.perf_counter()
    model = WhisperModel(entry.model_name, device=device, compute_type=compute_type)
    load_time = time.perf_counter() - t0
    ok(f"Loaded in {load_time:.1f}s on {device}")

    # Generate a tiny synthetic WAV (0.5 s silence) for the smoke test
    sample_path = _make_silent_wav()
    t1 = time.perf_counter()
    segs, _ = model.transcribe(sample_path, language="en")
    transcript = " ".join(s.text.strip() for s in segs)
    transcribe_time = time.perf_counter() - t1
    os.unlink(sample_path)

    ok(f"Transcribed in {transcribe_time:.2f}s — output: {repr(transcript)}")
    return True, device


def check_ollama_llm(model_name: str) -> bool:
    section("Ollama LLM smoke test")
    try:
        import ollama
    except ImportError:
        fail("ollama package missing — run: pip install ollama")
        return False

    prompt = "Reply with exactly one sentence confirming you are working."
    t0 = time.perf_counter()
    response = ollama.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1},
    )
    elapsed = time.perf_counter() - t0
    text = response["message"]["content"].strip()
    ok(f"Response in {elapsed:.1f}s: {text[:120]}")
    return True


def report_vram() -> None:
    section("VRAM usage (both models loaded)")
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        used, total = result.stdout.strip().split(",")
        ok(f"VRAM: {used.strip()} MB used / {total.strip()} MB total")
    else:
        warn("Cannot read VRAM — nvidia-smi unavailable")


def _make_silent_wav() -> str:
    """Write a minimal valid WAV file (0.5 s silence, 16kHz mono 16-bit)."""
    import struct

    num_samples = 8000
    data = b"\x00\x00" * num_samples
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        16000,
        32000,
        2,
        16,
        b"data",
        len(data),
    )
    path = tempfile.mktemp(suffix=".wav")
    with open(path, "wb") as f:
        f.write(header + data)
    return path


def main() -> None:
    print("\nYapIt — Milestone 1 Environment Verification")

    results: dict[str, bool] = {}
    results["nvidia"] = check_nvidia()
    results["ffmpeg"] = check_ffmpeg()

    ollama_ok, model_name = check_ollama()
    results["ollama"] = ollama_ok

    whisper_ok, device = check_whisper_gpu(results["nvidia"])
    results["whisper"] = whisper_ok

    if ollama_ok:
        results["llm"] = check_ollama_llm(model_name)
    else:
        results["llm"] = False

    if results["nvidia"] and results["whisper"] and results["llm"]:
        report_vram()

    section("Summary")
    all_ok = True
    for name, passed in results.items():
        status = "[OK]  " if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_ok = False

    if not all_ok:
        print("\n  Some checks failed. See messages above.")
        sys.exit(1)
    else:
        print("\n  All checks passed. Milestone 1 complete.")


if __name__ == "__main__":
    main()
