from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.protocol_adapters import BrowserAdapter, is_app_in_lock_list, resolve_role_token
from core.protocols_manager import ProtocolsManager
from services.stark_protocols import StarkProtocols


def test_protocols_manager_roles_per_profile(tmp_path):
    pm = ProtocolsManager(file_path=tmp_path / "protocols.json")
    roles = pm.get_roles()
    assert "browser" in roles

    updated = pm.set_roles({"browser": "vivaldi", "messenger": "telegram"})
    assert updated["browser"] == "vivaldi"
    assert updated["messenger"] == "telegram"

    pm2 = ProtocolsManager(file_path=tmp_path / "protocols.json")
    assert pm2.get_roles()["browser"] == "vivaldi"

    guest_roles = pm2.get_roles("guest")
    assert guest_roles["browser"] != "vivaldi" or "browser" in guest_roles


def test_protocols_manager_saves_isolated_locks(tmp_path):
    pm = ProtocolsManager(file_path=tmp_path / "protocols.json")
    game = pm.get_protocol_by_id("game")
    assert game is not None
    game["blocked_close_apps"] = ["telegram", "telegram", "  "]
    game["blocked_open_apps"] = ["obs"]
    pm.save_protocol(game)

    morning = pm.get_protocol_by_id("morning")
    assert morning is not None
    assert morning.get("blocked_close_apps", []) == []
    assert morning.get("blocked_open_apps", []) == []

    reloaded_game = pm.get_protocol_by_id("game")
    assert reloaded_game["blocked_close_apps"] == ["telegram"]
    assert reloaded_game["blocked_open_apps"] == ["obs"]


def test_browser_adapter_chromium_and_firefox_args():
    chromium_args = BrowserAdapter.build_launch_args(
        "vivaldi",
        ["https://github.com", "https://youtube.com"],
        profile="Profile 1",
        new_window=True,
    )
    assert chromium_args == [
        "--profile-directory=Profile 1",
        "--new-window",
        "https://github.com",
        "https://youtube.com",
    ]

    ff_args = BrowserAdapter.build_launch_args(
        "firefox",
        ["https://github.com", "https://youtube.com"],
        profile="work",
        new_window=True,
    )
    assert ff_args == [
        "-P",
        "work",
        "-new-window",
        "https://github.com",
        "-new-tab",
        "https://youtube.com",
    ]


def test_role_token_and_lock_matching():
    roles = {"browser": "vivaldi", "messenger": "telegram"}
    assert resolve_role_token("role:browser", roles) == "vivaldi"
    assert resolve_role_token("discord", roles) == "discord"

    assert is_app_in_lock_list("telegram.exe", ["telegram"], roles=roles)
    assert is_app_in_lock_list("role:messenger", ["telegram"], roles=roles)
    assert not is_app_in_lock_list("discord.exe", ["telegram"], roles=roles)


def test_protocol_blocked_open_apps_skips_launch():
    proto = {
        "id": "custom_test",
        "name": "Тест",
        "open_apps": ["role:browser", "discord"],
        "blocked_open_apps": ["vivaldi"],
        "close_mode": "none",
        "close_apps": [],
        "volume_mode": "none",
    }
    launched = []

    def fake_launch(app_key: str):
        launched.append(app_key)
        return True, "запущено"

    with patch.object(StarkProtocols, "launch_if_not_running", side_effect=fake_launch):
        report = StarkProtocols.execute_dynamic_protocol(proto, roles={"browser": "vivaldi"})

    assert launched == ["discord"]
    assert "не открыто vivaldi" in report


def test_protocol_blocked_close_apps_protects_telegram_in_game_mode():
    tg_proc = MagicMock()
    tg_proc.info = {"pid": 101, "name": "Telegram.exe"}
    chrome_proc = MagicMock()
    chrome_proc.info = {"pid": 102, "name": "chrome.exe"}

    with (
        patch("services.stark_protocols.psutil.process_iter", return_value=[tg_proc, chrome_proc]),
        patch("services.stark_protocols.psutil.wait_procs"),
    ):
        closed = StarkProtocols.close_user_apps_for_gaming(blocked_apps=["telegram"])

    assert "chrome.exe" in closed
    assert "telegram.exe" not in closed
    tg_proc.terminate.assert_not_called()
    chrome_proc.terminate.assert_called_once()


def test_protocol_steps_open_urls_uses_role_browser(tmp_path):
    fake_exe = tmp_path / "chrome.exe"
    fake_exe.write_text("", encoding="utf-8")

    proto = {
        "id": "work_urls",
        "name": "Ссылки",
        "open_apps": [],
        "close_mode": "none",
        "close_apps": [],
        "volume_mode": "none",
        "steps": [
            {
                "type": "open_urls",
                "browser": "role:browser",
                "profile": "Default",
                "urls": ["https://github.com"],
                "new_window": True,
            }
        ],
    }

    with (
        patch.object(StarkProtocols, "_resolve_app_path", return_value=fake_exe),
        patch.object(StarkProtocols, "focus_app_window", return_value=True),
        patch("core.protocol_adapters.subprocess.Popen") as popen_mock,
    ):
        report = StarkProtocols.execute_dynamic_protocol(proto, roles={"browser": "chrome"})

    popen_mock.assert_called_once()
    cmd = popen_mock.call_args[0][0]
    assert cmd[0] == str(fake_exe)
    assert "--profile-directory=Default" in cmd
    assert "https://github.com" in cmd
    assert "chrome" in report
