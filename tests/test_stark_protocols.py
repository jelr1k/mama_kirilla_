from __future__ import annotations

from unittest.mock import Mock, patch
from pathlib import Path

import pytest

from services.stark_protocols import StarkProtocols
from services.command_router import CommandRouter


def test_is_app_running_matches():
    mock_p1 = Mock()
    mock_p1.info = {"name": "opera.exe"}
    mock_p2 = Mock()
    mock_p2.info = {"name": "discord.exe"}

    with patch("psutil.process_iter", return_value=[mock_p1, mock_p2]):
        assert StarkProtocols.is_app_running("opera") is True
        assert StarkProtocols.is_app_running("discord") is True
        assert StarkProtocols.is_app_running("steam") is False


def test_launch_if_not_running_prevents_duplicate_launches():
    # If app is already running, it MUST NOT call os.startfile
    with patch.object(StarkProtocols, "is_app_running", return_value=True), \
         patch("os.startfile") as mock_start:
        ok, status = StarkProtocols.launch_if_not_running("opera")
        assert ok is True
        assert status == "уже запущено"
        mock_start.assert_not_called()


def test_launch_if_not_running_launches_when_not_running(tmp_path):
    dummy_exe = tmp_path / "dummy.exe"
    dummy_exe.touch()

    with patch.object(StarkProtocols, "is_app_running", return_value=False), \
         patch.object(StarkProtocols, "_resolve_app_path", return_value=dummy_exe), \
         patch("os.startfile") as mock_start:
        ok, status = StarkProtocols.launch_if_not_running("opera")
        assert ok is True
        assert status == "запущено"
        mock_start.assert_called_once_with(str(dummy_exe))


def test_protocol_morning_briefing():
    with patch.object(StarkProtocols, "set_volume_max") as mock_vol, \
         patch.object(StarkProtocols, "launch_if_not_running") as mock_launch, \
         patch.object(StarkProtocols, "get_weather_info", return_value=", в Москве сейчас +10°"):
        resp = StarkProtocols.execute_protocol("morning")
        mock_vol.assert_called_once()
        assert mock_launch.call_count == 3
        assert "Доброе утро, сэр" in resp
        assert "Громкость на максимуме" in resp
        assert "Браузер, Discord и Steam запущены" in resp


def test_protocol_lockdown():
    with patch.object(StarkProtocols, "lock_workstation") as mock_lock:
        resp = StarkProtocols.execute_protocol("lockdown")
        mock_lock.assert_called_once()
        assert "Блокирую терминал" in resp


def test_protocol_cinema():
    with patch.object(StarkProtocols, "set_volume_max") as mock_vol, \
         patch.object(StarkProtocols, "launch_if_not_running") as mock_launch, \
         patch.object(StarkProtocols, "close_apps_for_cinema") as mock_close:
        resp = StarkProtocols.execute_protocol("cinema")
        mock_vol.assert_called_once()
        mock_launch.assert_called_once_with("opera")
        mock_close.assert_called_once()
        assert "Протокол «Кино» активирован" in resp
        assert "Discord и Steam сохранены" in resp


def test_protocol_game():
    with patch.object(StarkProtocols, "launch_if_not_running") as mock_launch, \
         patch.object(StarkProtocols, "close_user_apps_for_gaming") as mock_close:
        resp = StarkProtocols.execute_protocol("game")
        assert mock_launch.call_count == 2
        mock_close.assert_called_once()
        assert "Игровой протокол активирован" in resp
        assert "Steam и Discord на связи" in resp


def test_protocol_clean_desk():
    with patch("services.stark_protocols.empty_recycle_bin", return_value={"success": True}):
        resp = StarkProtocols.execute_protocol("clean_desk")
        assert "Корзина очищена, сэр" in resp


def test_protocol_work():
    with patch.object(StarkProtocols, "close_steam_games") as mock_close_games, \
         patch.object(StarkProtocols, "launch_if_not_running") as mock_launch:
        resp = StarkProtocols.execute_protocol("work")
        mock_close_games.assert_called_once()
        assert mock_launch.call_count == 3
        assert "Протокол «Работа» активирован" in resp
        assert "Discord активен" in resp


def test_protocol_default():
    with patch.object(StarkProtocols, "set_volume_max") as mock_vol:
        resp = StarkProtocols.execute_protocol("default")
        mock_vol.assert_called_once()
        assert "Стандартный режим восстановлен" in resp


def test_router_dispatches_protocols():
    config = {"assistant_name": "JARVIS"}
    ollama_manager = Mock()
    router = CommandRouter(config, ollama_manager)

    test_cases = [
        ("доброе утро", "morning"),
        ("протокол доброе утро", "morning"),
        ("защита", "lockdown"),
        ("протокол защита", "lockdown"),
        ("заблокируй пк", "lockdown"),
        ("кино", "cinema"),
        ("протокол кино", "cinema"),
        ("режим кино", "cinema"),
        ("игра", "game"),
        ("протокол игра", "game"),
        ("чистый стол", "clean_desk"),
        ("протокол чистый стол", "clean_desk"),
        ("очистка", "clean_desk"),
        ("работа", "work"),
        ("протокол работа", "work"),
        ("к работе", "work"),
        ("дефолт", "default"),
        ("верни как обычно", "default"),
        ("обычный режим", "default"),
        ("сброс режима", "default"),
    ]

    for phrase, proto_id in test_cases:
        with patch.object(StarkProtocols, "execute_protocol", return_value=f"ok_{proto_id}") as mock_exec:
            res = router.route(phrase)
            assert res == f"ok_{proto_id}", f"Failed for phrase: {phrase}"
            mock_exec.assert_called_once_with(proto_id)
