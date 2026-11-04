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
    client = TestClient(gateway.fastapi_app)

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
