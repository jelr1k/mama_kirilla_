from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from starlette.testclient import TestClient

from core.config_manager import ConfigManager
from services.gateway_service import GatewayService
from services.update_checker import DEFAULT_REPOSITORY


def test_config_manager_deep_merge(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    initial_data = {
        "assistant_name": "Jarvis",
        "voice": {
            "device": "cpu",
            "compute_type": "int8",
            "sample_rate": 16000,
            "min_duration": 0.5,
            "wake_word": "джарвис",
        },
    }
    cfg_file.write_text(json.dumps(initial_data), encoding="utf-8")
    cm = ConfigManager(cfg_file)

    # Partial update to voice (e.g. only wake_word and min_duration)
    cm.set("voice", {"wake_word": "кириешка", "min_duration": 1.0})

    # Reload from disk to verify persistence
    saved = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert saved["voice"]["wake_word"] == "кириешка"
    assert saved["voice"]["min_duration"] == 1.0
    # Original keys must NOT be wiped out!
    assert saved["voice"]["device"] == "cpu"
    assert saved["voice"]["compute_type"] == "int8"
    assert saved["voice"]["sample_rate"] == 16000


def test_update_checker_default_repository():
    assert DEFAULT_REPOSITORY == "jelr1k/mama_kirilla_"


def test_autostart_launcher_path_resolution():
    from core.app_paths import APP_ROOT
    root_bat = APP_ROOT / "start.bat"
    assert root_bat.is_file(), f"start.bat not found at {root_bat}"


def test_gateway_whisper_and_tts_error_tracking():
    class DummyDep:
        def whisper_status(self, m):
            return "missing"
        def ensure_whisper_model(self, m):
            raise RuntimeError("Network timeout connecting to HuggingFace")

    class DummyTTS:
        def voice_status(self, v):
            return "missing"
        def ensure_voice(self, v):
            raise RuntimeError("Disk full")

    class AppContext:
        def __init__(self):
            self.dependency_manager = DummyDep()
            self.tts_service = DummyTTS()
            self.events = Mock()
            self.events.subscribe = Mock()

    app_ctx = AppContext()
    gw = GatewayService(app_ctx)
    client = TestClient(gw.fastapi_app)

    # Initial status
    res = client.get("/api/whisper/status")
    assert res.status_code == 200
    assert res.json()["statuses"]["small"] == "missing"

    # Trigger download which will fail
    d_res = client.post("/api/whisper/download", json={"model": "small"})
    assert d_res.status_code == 200

    # Wait for background thread
    import time
    time.sleep(0.1)

    s_res = client.get("/api/whisper/status")
    assert s_res.status_code == 200
    data = s_res.json()
    assert data["statuses"]["small"] == "failed"
    assert "Network timeout" in data["errors"]["small"]


def test_gateway_cors_allows_tauri_and_localhost():
    class AppContext:
        def __init__(self):
            self.events = Mock()
            self.events.subscribe = Mock()

    gw = GatewayService(AppContext())
    client = TestClient(gw.fastapi_app)

    # Request from Tauri origin
    res = client.options(
        "/api/statistics",
        headers={
            "Origin": "tauri://localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") == "tauri://localhost"

    # Request from dev server
    res2 = client.options(
        "/api/statistics",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res2.headers.get("access-control-allow-origin") == "http://127.0.0.1:5174"
