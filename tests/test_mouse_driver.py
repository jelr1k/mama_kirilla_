from __future__ import annotations

from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

from core.alias_manager import AliasManager
from tools import mouse_driver
from tools.registry import TOOLS
from services.command_router import CommandRouter


@pytest.fixture
def router(tmp_path):
    aliases = AliasManager(tmp_path / "aliases.json")
    config = {"tools": {name: True for name in TOOLS}}
    return CommandRouter(config, None, aliases)


def test_mouse_driver_already_running():
    with patch("tools.mouse_driver._is_mouse_driver_running", return_value=True), \
         patch("ctypes.windll.user32.FindWindowW", return_value=12345), \
         patch("ctypes.windll.user32.IsWindowVisible", return_value=1), \
         patch("ctypes.windll.user32.IsIconic", return_value=0), \
         patch("ctypes.windll.user32.ShowWindow") as mock_show, \
         patch("ctypes.windll.user32.SetForegroundWindow"), \
         patch("ctypes.windll.user32.ClientToScreen"), \
         patch("ctypes.windll.user32.GetCursorPos"), \
         patch("ctypes.windll.user32.SetCursorPos"), \
         patch("ctypes.windll.user32.mouse_event"), \
         patch("ctypes.windll.user32.PostMessageW"), \
         patch("time.sleep"):

        res = mouse_driver.apply_mouse_settings()
        assert res["success"] is True
        assert res["launched"] is False
        assert "настройки применены" in res["content"]


def test_mouse_driver_not_running_launches():
    fake_exe = Path("C:/Program Files (x86)/Fury3327BK/MouseDriver.exe")
    with patch("tools.mouse_driver._is_mouse_driver_running", return_value=False), \
         patch("tools.mouse_driver._resolve_fury_executable", return_value=fake_exe), \
         patch.object(Path, "is_file", return_value=True), \
         patch("subprocess.Popen") as mock_popen, \
         patch("ctypes.windll.user32.FindWindowW", return_value=12345), \
         patch("ctypes.windll.user32.IsWindowVisible", return_value=0), \
         patch("ctypes.windll.user32.IsIconic", return_value=0), \
         patch("ctypes.windll.user32.ShowWindow") as mock_show, \
         patch("ctypes.windll.user32.SetForegroundWindow"), \
         patch("ctypes.windll.user32.ClientToScreen"), \
         patch("ctypes.windll.user32.GetCursorPos"), \
         patch("ctypes.windll.user32.SetCursorPos"), \
         patch("ctypes.windll.user32.mouse_event"), \
         patch("ctypes.windll.user32.PostMessageW"), \
         patch("time.sleep"):

        res = mouse_driver.apply_mouse_settings(auto_minimize_if_launched=True)
        assert res["success"] is True
        assert res["launched"] is True
        assert "запущена и настройки применены" in res["content"]
        mock_popen.assert_called_once()
        mock_show.assert_any_call(12345, 6) # SW_MINIMIZE = 6


def test_mouse_driver_window_not_found():
    with patch("tools.mouse_driver._is_mouse_driver_running", return_value=True), \
         patch("ctypes.windll.user32.FindWindowW", return_value=0), \
         patch("ctypes.windll.user32.EnumWindows"), \
         patch("time.sleep"):

        res = mouse_driver.apply_mouse_settings()
        assert res["success"] is False
        assert "не найдено" in res["error"]


@pytest.mark.parametrize("phrase", [
    "мышь",
    "мыш",
    "мышка",
    "примени мышь",
    "мышь применить",
    "настройки мыши",
    "активируй мышь",
])
def test_command_router_mouse_matching(router, phrase):
    with patch("tools.executor.ToolExecutor.execute") as mock_exec:
        mock_exec.return_value = {"success": True, "content": "Готово, настройки применены."}
        reply = router.route(phrase)
        mock_exec.assert_called_once_with("apply_mouse_settings", {})
        assert "Готово" in reply
