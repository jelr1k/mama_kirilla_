from __future__ import annotations

import sys
from unittest.mock import Mock, patch

import pytest

import start.main as app_main


def test_start_main_headless_happy_path_wires_backend():
    logger = Mock()
    backend = Mock()

    with patch.object(app_main, "setup_logging", return_value=logger), \
         patch.object(app_main, "JarvisApplication", return_value=backend), \
         patch.object(app_main, "write_startup_health_marker") as marker_mock, \
         patch.object(app_main.threading.Event, "wait", return_value=True), \
         patch.object(app_main.threading.Event, "is_set", side_effect=[False, True]), \
         patch.object(sys, "argv", ["main.py", "--headless"]):

        exit_code = app_main.main()

    assert exit_code == 0
    backend.start.assert_called_once()
    marker_mock.assert_called_once()
    backend.shutdown.assert_called_once()
    logger.info.assert_called()


def test_start_main_headless_startup_error_shuts_backend_down_and_exits():
    logger = Mock()
    backend = Mock()
    backend.start.side_effect = RuntimeError("startup boom")

    with patch.object(app_main, "setup_logging", return_value=logger), \
         patch.object(app_main, "JarvisApplication", return_value=backend), \
         patch.object(sys, "argv", ["main.py", "--headless"]), \
         pytest.raises(SystemExit) as exc_info:

        app_main.main()

    assert exc_info.value.code == 1
    backend.shutdown.assert_called_once()
    logger.exception.assert_called()


def test_start_main_legacy_gui_without_pyside_exits_with_clear_error(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if "PySide6" in name:
            raise ImportError("No module named PySide6")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(sys, "argv", ["main.py", "--legacy-gui"])

    with pytest.raises(SystemExit) as exc_info:
        app_main.main()

    assert exc_info.value.code == 1
