from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication

from core.dependency_manager import DependencyManager, _ProgressTqdm, _NullStream
from voice.devices import resolve_shared_input_device, get_shared_input_extra_settings
from llm.ollama import _scan_local_ollama_manifests
from ui.animations.tab_animations import SlidingStackedWidget
from ui.home_page import HomePage


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


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


def test_sliding_stacked_widget_fast_switch(qapp):
    stack = SlidingStackedWidget()
    from PySide6.QtWidgets import QLabel
    w0 = QLabel("Tab 0")
    w1 = QLabel("Tab 1")
    w2 = QLabel("Tab 2")
    stack.addWidget(w0)
    stack.addWidget(w1)
    stack.addWidget(w2)
    stack.resize(400, 300)
    stack.show()

    # Rapid sequential switches
    stack.slide_to_index(1)
    # While animating, switch again to 2
    stack.slide_to_index(2)

    assert stack.currentIndex() == 2
    assert stack.currentWidget() == w2
    assert w2.isVisible()
    assert not w0.isVisible()


def test_home_page_init_and_signals(qapp):
    config = Mock()
    config.get.side_effect = lambda k, d=None: "qwen2.5:7b" if k == "model" else d
    stats_ctrl = Mock()
    stats_ctrl.system_status = Mock()

    page = HomePage(config, stats_ctrl)
    assert page is not None

    nav_events = []
    page.navigate_requested.connect(nav_events.append)
    page.navigate_requested.emit("chat")
    assert nav_events == ["chat"]

    cmd_events = []
    page.command_requested.connect(cmd_events.append)
    page.command_requested.emit("сделай скриншот")
    assert cmd_events == ["сделай скриншот"]
