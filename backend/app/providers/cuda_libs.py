"""Load the CUDA 12 libraries Whisper needs without relying on a system-wide CUDA toolkit.

CTranslate2 (faster-whisper's engine) looks for libcublas.so.12 when it first processes audio.
A system CUDA toolkit can disappear with a driver change, so the libraries are loaded from:
1. NVIDIA's pip package (nvidia-cublas-cu12), if installed;
2. otherwise, the folders configured for the transcriber in models.yaml (by default the copy
   that Ollama ships, which YapIt needs anyway).
Loading a library by its full path first makes later lookups by name find it, without changing
LD_LIBRARY_PATH.
"""

from __future__ import annotations

import ctypes
import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PIP_PACKAGE = "nvidia.cublas"
# In dependency order: libcublas needs libcublasLt.
_LIBRARIES = ("libcublasLt.so.12", "libcublas.so.12")


def _pip_library_dir() -> Path | None:
    try:
        module = importlib.import_module(_PIP_PACKAGE)
    except ImportError:
        return None
    return Path(next(iter(module.__path__))) / "lib"


def _has_libraries(folder: Path) -> bool:
    return all((folder / name).exists() for name in _LIBRARIES)


def preload_cuda_libraries(fallback_dirs: list[str]) -> list[str]:
    """Load the libraries from the first source that has them all. Returns the loaded paths, or
    an empty list if none was found (a system-wide CUDA install may still provide them)."""
    candidates = [_pip_library_dir(), *(Path(d) for d in fallback_dirs)]
    folder = next((c for c in candidates if c is not None and _has_libraries(c)), None)
    if folder is None:
        return []
    loaded = []
    for name in _LIBRARIES:
        path = str(folder / name)
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        loaded.append(path)
    logger.info("Loaded CUDA libraries for Whisper from %s", folder)
    return loaded
