from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.dependency_manager import DependencyManager, _ProgressTqdm, _NullStream
from voice.devices import resolve_shared_input_device, get_shared_input_extra_settings
from llm.ollama import _scan_local_ollama_manifests


def test_progress_tqdm_null_stream_when_stderr_none():
    null_s = _NullStream()
    null_s.write("test")
    null_s.flush()
    assert null_s.isatty() is False

    # Simulate sys.stderr is None in GUI mode
    with patch("sys.stderr", None):
        t = _ProgressTqdm(total=100)
        assert t.fp is not None
        # Should not raise AttributeError: 'NoneType' object has no attribute 'write'
        t.update(10)
        t.close()


def test_whisper_status_local_path(tmp_path):
    dm = DependencyManager()
    model_dir = tmp_path / "custom_whisper"
    model_dir.mkdir()
    (model_dir / "model.bin").write_text("dummy")

    assert dm.whisper_status(str(model_dir)) == "installed"


def test_scan_local_ollama_manifests(tmp_path, monkeypatch):
    manifests_dir = tmp_path / "manifests" / "registry.ollama.ai" / "library" / "test_model"
    manifests_dir.mkdir(parents=True)
    (manifests_dir / "latest").write_text("{}")

    monkeypatch.setenv("OLLAMA_MODELS", str(tmp_path))
    models = _scan_local_ollama_manifests()
    assert "test_model:latest" in models


def test_resolve_shared_input_device_none():
    # Calling with None should not crash
    res = resolve_shared_input_device(None)
    # May return an index or None if no device
    assert res is None or isinstance(res, int)

    settings = get_shared_input_extra_settings(None)
    import sounddevice as sd
    assert settings is None or isinstance(settings, sd.WasapiSettings)
