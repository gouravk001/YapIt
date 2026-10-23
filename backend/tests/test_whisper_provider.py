from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.providers import cuda_libs, whisper_provider


class FakeWhisperModel:
    """Stands in for faster_whisper.WhisperModel; GPU instances can be made to fail on use."""

    gpu_works = True
    created: list[str] = []

    def __init__(self, path, device, compute_type):
        self.device = device
        FakeWhisperModel.created.append(device)

    def transcribe(self, audio, vad_filter=False):
        if self.device == "cuda" and not FakeWhisperModel.gpu_works:
            raise RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
        return iter([]), SimpleNamespace(duration=1.0)


@pytest.fixture
def fake_whisper(monkeypatch):
    FakeWhisperModel.created = []
    fake_module = ModuleType("faster_whisper")
    fake_module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    monkeypatch.setattr(whisper_provider, "ensure_whisper_model", lambda name: f"/models/{name}")
    monkeypatch.setattr(whisper_provider, "preload_cuda_libraries", lambda dirs: [])
    return FakeWhisperModel


def _provider():
    return whisper_provider.WhisperProvider(
        model_name="small.en",
        device="cuda",
        compute_type="float16",
        device_fallback="cpu",
        compute_type_fallback="int8",
        vad_filter=True,
        cuda_library_dirs=[],
    )


def test_working_gpu_is_used(fake_whisper):
    fake_whisper.gpu_works = True
    assert _provider().device == "cuda"
    assert fake_whisper.created == ["cuda"]


def test_gpu_that_loads_but_cannot_run_falls_back_to_cpu(fake_whisper):
    fake_whisper.gpu_works = False
    provider = _provider()
    assert provider.device == "cpu"
    assert fake_whisper.created == ["cuda", "cpu"]


def _fake_lib_dir(root, names=("libcublasLt.so.12", "libcublas.so.12")):
    root.mkdir(parents=True)
    for name in names:
        (root / name).touch()
    return root


@pytest.fixture
def recorded_loads(monkeypatch):
    loaded = []
    monkeypatch.setattr(cuda_libs.ctypes, "CDLL", lambda path, mode: loaded.append(path))
    return loaded


def _pip_package(monkeypatch, tmp_path):
    _fake_lib_dir(tmp_path / "pip" / "lib")
    package = ModuleType("nvidia.cublas")
    package.__path__ = [str(tmp_path / "pip")]
    monkeypatch.setitem(sys.modules, "nvidia.cublas", package)


def test_pip_package_libraries_are_loaded_first(tmp_path, monkeypatch, recorded_loads):
    _pip_package(monkeypatch, tmp_path)
    other = _fake_lib_dir(tmp_path / "ollama")

    loaded = cuda_libs.preload_cuda_libraries([str(other)])

    assert loaded == recorded_loads
    assert [p.split("/")[-1] for p in loaded] == ["libcublasLt.so.12", "libcublas.so.12"]
    assert all("/pip/" in p for p in loaded)


def test_configured_folder_is_used_when_pip_package_is_missing(
    tmp_path, monkeypatch, recorded_loads
):
    monkeypatch.setattr(cuda_libs, "_PIP_PACKAGE", "nvidia.not_installed")
    missing = tmp_path / "missing"
    ollama = _fake_lib_dir(tmp_path / "ollama")

    loaded = cuda_libs.preload_cuda_libraries([str(missing), str(ollama)])

    assert loaded == [str(ollama / "libcublasLt.so.12"), str(ollama / "libcublas.so.12")]


def test_nothing_found_loads_nothing(monkeypatch, recorded_loads):
    monkeypatch.setattr(cuda_libs, "_PIP_PACKAGE", "nvidia.not_installed")
    assert cuda_libs.preload_cuda_libraries(["/nowhere"]) == []
    assert recorded_loads == []
