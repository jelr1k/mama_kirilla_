from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from core.vpn.manager import VpnManager
from services.stark_protocols import StarkProtocols


def test_stark_protocols_builtin_scenarios():
    with (
        patch.object(StarkProtocols, "set_volume_max") as mock_vol,
        patch.object(StarkProtocols, "launch_if_not_running") as mock_launch,
        patch.object(StarkProtocols, "close_apps_for_cinema") as mock_cinema,
        patch.object(StarkProtocols, "close_user_apps_for_gaming") as mock_game,
        patch.object(StarkProtocols, "close_steam_games") as mock_steam,
        patch.object(StarkProtocols, "lock_workstation") as mock_lock,
        patch.object(StarkProtocols, "get_weather_info", return_value=", на улице +5°C"),
        patch("services.stark_protocols.empty_recycle_bin", return_value={"success": True}) as mock_bin,
    ):
        morning_res = StarkProtocols.execute_protocol("morning")
        assert "Доброе утро" in morning_res
        assert "+5°C" in morning_res
        mock_vol.assert_called()
        assert mock_launch.call_count >= 3

        assert "Блокирую терминал" in StarkProtocols.execute_protocol("lockdown")
        mock_lock.assert_called_once()

        assert "Кино" in StarkProtocols.execute_protocol("cinema")
        mock_cinema.assert_called_once()

        assert "Игровой протокол" in StarkProtocols.execute_protocol("game")
        mock_game.assert_called_once()

        assert "Корзина очищена" in StarkProtocols.execute_protocol("clean_desk")
        mock_bin.assert_called_once()

        assert "Работа" in StarkProtocols.execute_protocol("work")
        mock_steam.assert_called_once()

        assert "Стандартный режим" in StarkProtocols.execute_protocol("default")
        assert StarkProtocols.execute_protocol("unknown_id") == "Протокол не опознан, сэр."


def test_stark_protocols_dynamic_protocol_executes_all_directives():
    proto = {
        "id": "custom_work",
        "name": "Стриминг",
        "volume_mode": "mute",
        "pause_media": True,
        "close_mode": "steam_games",
        "close_apps": ["notepad"],
        "open_apps": ["obs"],
        "clean_recycle_bin": True,
        "lock_screen": False,
        "briefing": True,
        "response_text": "Стрим-среда готова.",
    }
    with (
        patch("services.stark_protocols.media_control.set_master_mute") as mock_mute,
        patch("services.stark_protocols.media_control._send_key") as mock_key,
        patch("services.stark_protocols.media_control.VK_MAP", {"play_pause": 0xB3}),
        patch.object(StarkProtocols, "close_steam_games") as mock_close_steam,
        patch("tools.application_closer.close_application") as mock_close_app,
        patch.object(StarkProtocols, "launch_if_not_running") as mock_launch,
        patch("services.stark_protocols.empty_recycle_bin", return_value={"success": True}) as mock_bin,
        patch.object(StarkProtocols, "get_weather_info", return_value=""),
    ):
        res = StarkProtocols.execute_protocol(proto)
        assert res.startswith("Доброе утро, сэр.")
        assert res.endswith("Стрим-среда готова.")
        mock_mute.assert_called_once_with(True)
        mock_key.assert_called_once_with(0xB3, repeat=1)
        mock_close_steam.assert_called_once()
        mock_close_app.assert_called_once_with("notepad")
        mock_launch.assert_called_once_with("obs")
        mock_bin.assert_called_once()


def test_vpn_manager_status_caching_and_zapret_launch(tmp_path):
    mgr = VpnManager()
    service_bat = tmp_path / "service.bat"
    service_bat.write_text("@echo off", encoding="utf-8")

    with (
        patch.object(mgr, "_find_service_bat", return_value=service_bat) as mock_find_bat,
        patch.object(mgr, "_discover_client", return_value=None),
        patch("core.vpn.manager._is_proc_running", return_value=False),
        patch("core.vpn.manager.get_zapret_status_data", return_value={"found": True, "running": False}),
    ):
        s1 = mgr.status()
        s2 = mgr.status()
        assert s1 is s2
        assert mock_find_bat.call_count == 1

        mgr.status(force=True)
        assert mock_find_bat.call_count == 2

    # launch_zapret succeeds and invalidates cache
    with (
        patch.object(mgr, "_find_service_bat", return_value=service_bat),
        patch("core.vpn.manager._is_proc_running", return_value=True),
        patch("os.startfile") as mock_start,
    ):
        res = mgr.launch_zapret()
        assert res["success"] is True
        assert res["running"] is True
        assert mgr._cache is None
        mock_start.assert_called_once_with(str(service_bat))

    # launch_zapret falls back to archive extraction and handles missing zapret
    with (
        patch.object(mgr, "_find_service_bat", return_value=None),
        patch.object(mgr, "_find_zapret_archive", return_value=None),
    ):
        missing = mgr.launch_zapret()
        assert missing["success"] is False
        assert "не найден" in missing["message"]


def test_vpn_manager_connect_uri_fallback_and_uia(tmp_path):
    mgr = VpnManager()
    happ_exe = tmp_path / "Happ.exe"
    happ_exe.write_text("exe", encoding="utf-8")
    fl_exe = tmp_path / "FlClashX.exe"
    fl_exe.write_text("exe", encoding="utf-8")

    # 1. Happ URI success
    with (
        patch.object(mgr, "_discover_client", return_value=happ_exe),
        patch("os.startfile") as mock_start,
    ):
        res = mgr.connect("happ")
        assert res["success"] is True
        assert res["method"] == "uri"
        mock_start.assert_called_once()

    # 2. Happ URI OSError falls back to UIA flow
    with (
        patch.object(mgr, "_discover_client", return_value=happ_exe),
        patch("os.startfile", side_effect=OSError("no handler")),
        patch("core.vpn.manager._is_proc_running", return_value=True),
        patch.object(mgr, "_activate_with_uia", return_value=(True, False, "clicked")),
    ):
        res = mgr.connect("happ")
        assert res["success"] is True
        assert res["method"] == "uia"
        assert res["activated"] is True

    # 3. FlClash launches process if not running and handles UIA failure gracefully
    with (
        patch.object(mgr, "_discover_client", return_value=fl_exe),
        patch("core.vpn.manager._is_proc_running", return_value=False),
        patch("subprocess.Popen") as mock_popen,
        patch.object(mgr, "_activate_with_uia", return_value=(False, False, "timeout")),
    ):
        res = mgr.connect("flclash")
        assert res["success"] is True
        assert res["launched"] is True
        assert res["activated"] is False
        mock_popen.assert_called_once_with([str(fl_exe)], cwd=str(tmp_path))

    # 4. No client found
    with patch.object(mgr, "status", return_value={"clients": {}}):
        no_client = mgr.connect(None)
        assert no_client["success"] is False
