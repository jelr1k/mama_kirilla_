from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from core.app_indexer import AppIndexer
from core.events import EventBus
from voice.prompt_builder import VoicePromptBuilder


@pytest.fixture
def mock_start_menu(tmp_path):
    programs_dir = tmp_path / "Programs"
    programs_dir.mkdir()

    # Create dummy files
    discord_lnk = programs_dir / "Discord.lnk"
    discord_lnk.write_bytes(b"dummy lnk")

    cool_app_lnk = programs_dir / "SuperCoolApp.lnk"
    cool_app_lnk.write_bytes(b"dummy lnk")

    obs_lnk = programs_dir / "OBS Studio.lnk"
    obs_lnk.write_bytes(b"dummy lnk")

    uninstall_lnk = programs_dir / "Uninstall Discord.lnk"
    uninstall_lnk.write_bytes(b"dummy lnk")

    readme_lnk = programs_dir / "OBS Readme.lnk"
    readme_lnk.write_bytes(b"dummy lnk")

    return programs_dir


def test_app_indexer_scan_filters_ignored(mock_start_menu):
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu])
    apps = indexer.scan_installed_apps(force=True)

    app_names = [a["name"] for a in apps]
    assert "Discord" in app_names
    assert "OBS Studio" in app_names
    assert "Uninstall Discord" not in app_names
    assert "OBS Readme" not in app_names


def test_app_indexer_aliases_generation():
    indexer = AppIndexer()
    aliases = indexer._generate_aliases("Discord", "Discord")
    assert "дискорд" in aliases
    assert "дс" in aliases

    obs_aliases = indexer._generate_aliases("OBS Studio", "obs64")
    assert "обс" in obs_aliases


def test_app_indexer_resolve_exact_and_fuzzy(mock_start_menu):
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu])
    indexer.scan_installed_apps(force=True)

    # Exact name
    match = indexer.resolve_app("Discord")
    assert match is not None
    assert match["name"] == "Discord"

    # Russian alias
    match_ru = indexer.resolve_app("дискорд")
    assert match_ru is not None
    assert match_ru["name"] == "Discord"

    # Extra short alias
    match_short = indexer.resolve_app("дс")
    assert match_short is not None
    assert match_short["name"] == "Discord"

    # Fuzzy match
    match_fuzzy = indexer.resolve_app("обс студио")
    assert match_fuzzy is not None
    assert match_fuzzy["name"] == "OBS Studio"

    # Non-existent
    assert indexer.resolve_app("NonExistentApp12345") is None


def test_app_indexer_launch_success(mock_start_menu):
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu])
    indexer.scan_installed_apps(force=True)

    with patch("os.startfile") as mock_startfile:
        res = indexer.launch_app("Discord")
        assert res["success"] is True
        assert res["app"] == "Discord"
        mock_startfile.assert_called_once()


def test_app_indexer_launch_not_found():
    indexer = AppIndexer(custom_start_dirs=[])
    res = indexer.launch_app("NonExistentAppXYZ")
    assert res["success"] is False
    assert "не найдено" in res["error"]


def test_command_router_integration(mock_start_menu):
    from services.command_router import CommandRouter

    config = Mock()
    config.get.side_effect = lambda k, d=None: (
        "Kirieshcka" if k == "assistant_name"
        else {"get_process_status": True, "launch_application": True} if k == "tools"
        else d
    )
    ollama_mgr = Mock()
    bus = EventBus()

    indexer = AppIndexer(event_bus=bus, custom_start_dirs=[mock_start_menu])
    indexer.scan_installed_apps(force=True)

    router = CommandRouter(
        config=config,
        ollama_manager=ollama_mgr,
        event_bus=bus,
        app_indexer=indexer,
    )

    with patch("os.startfile"):
        reply = router.route("запусти supercoolapp")
        assert reply == "Запускаю «SuperCoolApp»."

        # Quick check for async system command
        assert router.is_async_system_command("открой supercoolapp") is True


def test_voice_prompt_builder_includes_indexed_apps(mock_start_menu):
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu])
    indexer.scan_installed_apps(force=True)

    builder = VoicePromptBuilder(
        alias_manager=Mock(data={}),
        website_manager=Mock(get_websites=lambda: []),
        protocols_manager=Mock(get_protocols=lambda: []),
        steam_manager=Mock(installed_games=[]),
        app_indexer=indexer,
    )
    prompt = builder.build_prompt(force=True)

    assert "Discord" in prompt or "дискорд" in prompt or "дс" in prompt
    assert "OBS Studio" in prompt or "обс" in prompt


def test_gateway_apps_endpoints(mock_start_menu):
    from fastapi.testclient import TestClient
    from services.gateway_service import GatewayService

    app_context = Mock()
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu])
    indexer.scan_installed_apps(force=True)
    app_context.app_indexer = indexer

    gateway = GatewayService(app_context=app_context)
    client = TestClient(gateway.fastapi_app, headers={"X-Session-Token": gateway.session_token})

    # 1. GET /api/apps
    resp = client.get("/api/apps")
    assert resp.status_code == 200
    data = resp.json()
    assert "apps" in data
    assert data["total"] >= 2

    # 2. POST /api/apps/refresh
    resp_ref = client.post("/api/apps/refresh")
    assert resp_ref.status_code == 200
    assert resp_ref.json()["success"] is True

    # 3. POST /api/apps/launch
    with patch("os.startfile"):
        resp_launch = client.post("/api/apps/launch", json={"app": "Discord"})
        assert resp_launch.status_code == 200
        assert resp_launch.json()["success"] is True

    # 4. GET /api/protocols/suggestions
    resp_sug = client.get("/api/protocols/suggestions?exclude=discord")
    assert resp_sug.status_code == 200
    sug_keys = [item["key"] for item in resp_sug.json()["suggestions"]]
    assert "discord" not in sug_keys


def test_app_indexer_persistent_json_cache(mock_start_menu, tmp_path):
    cache_file = tmp_path / "installed_apps.json"

    indexer1 = AppIndexer(custom_start_dirs=[mock_start_menu], cache_file=cache_file)
    apps1 = indexer1.scan_installed_apps(force=True)
    assert cache_file.is_file()
    assert any(a["name"] == "Discord" for a in apps1)

    # Новый инстанс сразу подхватывает кэш с диска без сканирования
    indexer2 = AppIndexer(custom_start_dirs=[mock_start_menu], cache_file=cache_file)
    cached_apps = indexer2.scan_installed_apps(force=False)
    assert [a["name"] for a in cached_apps] == [a["name"] for a in apps1]

    # Добавляем новую прогу и пересканируем -> кэш должен обновиться
    (mock_start_menu / "Vivaldi.lnk").write_bytes(b"dummy lnk")
    apps_updated = indexer2.scan_installed_apps(force=True)
    assert any(a["name"] == "Vivaldi" for a in apps_updated)
    assert "Vivaldi" in cache_file.read_text(encoding="utf-8")


def test_app_indexer_filters_windows_system_junk():
    from core.app_indexer import _is_system_or_junk

    # Системный мусор режется
    assert _is_system_or_junk("Cmd", r"C:\Windows\System32\cmd.exe") is True
    assert _is_system_or_junk("Regedit", r"C:\Windows\regedit.exe") is True
    assert _is_system_or_junk("Visual C++ Redist", r"C:\Program Files\vcredist_x64.exe") is True
    assert _is_system_or_junk("Some Driver", r"C:\Windows\SysWOW64\driver.exe") is True

    # Базовые полезные утилиты остаются
    assert _is_system_or_junk("Блокнот", r"C:\Windows\System32\notepad.exe") is False
    assert _is_system_or_junk("Калькулятор", r"C:\Windows\System32\calc.exe") is False
    assert _is_system_or_junk("Vivaldi", r"C:\Users\User\AppData\Local\Vivaldi\Application\vivaldi.exe") is False


def test_app_indexer_protocol_suggestions_no_duplicates(mock_start_menu):
    (mock_start_menu / "Vivaldi.lnk").write_bytes(b"dummy lnk")
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu])
    indexer.scan_installed_apps(force=True)

    all_sug = indexer.get_protocol_suggestions(limit=0)
    keys = [s["key"] for s in all_sug]
    assert len(keys) == len(set(keys))
    # Браузер и мессенджер идут раньше обычного софта
    assert keys.index("vivaldi") < keys.index("supercoolapp")

    # Исключение по имени и по русскому алиасу работает без повторов
    filtered = indexer.get_protocol_suggestions(exclude=["Vivaldi", "дс"], limit=0)
    filtered_keys = [s["key"] for s in filtered]
    assert "vivaldi" not in filtered_keys
    assert "discord" not in filtered_keys


def test_app_indexer_classification_word_boundaries_and_shortcut_dirs():
    from core.app_indexer import _classify_app, _is_system_or_junk

    # Подстрока "tor" не должна превращать системные редакторы/мониторы в браузеры
    assert _classify_app("Registry Editor", "regedit") == "app"
    assert _classify_app("Resource Monitor", "resmon") == "app"
    assert _classify_app("Slideshow Creator", "creator") == "app"
    assert _classify_app("Tor Browser", "firefox") == "browser"

    # Мусорные папки Start Menu отсеиваются
    assert _is_system_or_junk("Some Tool", None, r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Administrative Tools\Some Tool.lnk") is True
    assert _is_system_or_junk("Sample App", None, r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Windows Kits\Sample App.lnk") is True
    assert _is_system_or_junk("Task Manager", None, r"C:\Users\User\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\System Tools\Task Manager.lnk") is False


def test_app_indexer_hidden_apps_toggle(mock_start_menu, tmp_path):
    hidden_file = tmp_path / "hidden_apps.json"
    indexer = AppIndexer(custom_start_dirs=[mock_start_menu], hidden_file=hidden_file)
    indexer.scan_installed_apps(force=True)

    assert any(s["key"] == "discord" for s in indexer.get_protocol_suggestions(limit=0))
    indexer.set_app_hidden("Discord", True)
    assert hidden_file.is_file()
    assert not any(s["key"] == "discord" for s in indexer.get_protocol_suggestions(limit=0))

    # Новый инстанс подхватывает hidden_apps.json и позволяет вернуть обратно
    indexer2 = AppIndexer(custom_start_dirs=[mock_start_menu], hidden_file=hidden_file)
    indexer2.scan_installed_apps(force=True)
    assert not any(s["key"] == "discord" for s in indexer2.get_protocol_suggestions(limit=0))

    indexer2.set_app_hidden("discord", False)
    assert any(s["key"] == "discord" for s in indexer2.get_protocol_suggestions(limit=0))
