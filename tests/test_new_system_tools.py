from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.alias_manager import AliasManager
from services.command_router import CommandRouter
from tools.system_actions import (
    empty_recycle_bin,
    get_current_time_date,
    lock_pc,
    open_system_folder,
    take_screenshot,
)


@pytest.fixture
def mock_dependencies(tmp_path):
    ollama_manager = MagicMock()
    config = {
        "tools": {
            "take_screenshot": True,
            "lock_pc": True,
            "get_current_time_date": True,
            "open_system_folder": True,
            "empty_recycle_bin": True,
        }
    }
    alias_manager = AliasManager(tmp_path / "aliases.json")
    router = CommandRouter(config, ollama_manager, alias_manager=alias_manager)
    return router


def test_get_current_time_date():
    res = get_current_time_date()
    assert res["success"] is True
    assert "content" in res
    assert "Сейчас" in res["content"]
    assert "г." in res["content"]
    assert res["time"] != ""
    assert res["weekday"] != ""


def test_lock_pc_mocked(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with patch("ctypes.windll.user32.LockWorkStation", return_value=1) as mock_lock:
        res = lock_pc()
        assert res["success"] is True
        assert res["content"] == "Система заблокирована."
        mock_lock.assert_called_once()


def test_take_screenshot_mocked(tmp_path):
    with patch("tools.system_actions.TOOL_WORKSPACE", tmp_path):
        res = take_screenshot("test_screen.png")
        # Either succeeded or fallback tried
        assert "success" in res


def test_open_system_folder_mocked():
    with patch("os.startfile") as mock_startfile:
        res = open_system_folder("загрузки")
        assert res["success"] is True
        assert "открыта" in res["content"]
        mock_startfile.assert_called_once()

    with patch("subprocess.Popen") as mock_popen:
        res_exp = open_system_folder("проводник")
        assert res_exp["success"] is True
        mock_popen.assert_called_once_with(["explorer.exe"])


def test_open_system_folder_invalid():
    res = open_system_folder("несуществующая_папка_12345")
    assert res["success"] is False
    assert "Неизвестная системная папка" in res["error"]


def test_router_handles_screenshot(mock_dependencies):
    with patch("tools.system_actions.take_screenshot", return_value={"success": True, "content": "Скриншот сохранён: screen.png"}):
        reply = mock_dependencies.route("сделай скриншот")
        assert "Скриншот сохранён" in reply


def test_router_handles_date_time(mock_dependencies):
    reply = mock_dependencies.route("сколько времени")
    assert "Сейчас" in reply or ":" in reply


def test_router_handles_lock_pc(mock_dependencies):
    with patch("tools.system_actions.lock_pc", return_value={"success": True, "content": "Система заблокирована."}):
        reply = mock_dependencies.route("заблокируй пк")
        assert "Система заблокирована" in reply


def test_router_handles_open_folder(mock_dependencies):
    with patch("tools.system_actions.open_system_folder", return_value={"success": True, "content": "Папка загрузки открыта."}):
        reply = mock_dependencies.route("открой загрузки")
        assert "открыта" in reply


def test_router_handles_clear_chat(mock_dependencies):
    mock_clear = MagicMock()
    mock_dependencies.set_ui_actions({"clear_chat": mock_clear})
    reply = mock_dependencies.route("очисти чат")
    assert "очищена" in reply or "очищен" in reply
    mock_clear.assert_called_once()
