"""Samples GPU memory in the background while a model runs."""

from __future__ import annotations

import subprocess
import threading

POLL_SECONDS = 0.5
NVIDIA_SMI = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]


def read_vram_mb() -> int | None:
    """Memory in use on the first GPU, or None without an NVIDIA GPU."""
    try:
        out = subprocess.run(NVIDIA_SMI, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return int(out.splitlines()[0])


class VramSampler:
    """Context manager that records the highest reading seen while it is open."""

    def __init__(self) -> None:
        self.peak_mb: int | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll, daemon=True)

    def _poll(self) -> None:
        while not self._stop.is_set():
            reading = read_vram_mb()
            if reading is not None:
                self.peak_mb = max(self.peak_mb or 0, reading)
            self._stop.wait(POLL_SECONDS)

    def __enter__(self) -> VramSampler:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()
