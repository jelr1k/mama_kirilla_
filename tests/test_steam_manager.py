from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from core.steam_manager import SteamManager


@pytest.fixture
def fake_steam_structure(tmp_path):
    steam_root = tmp_path / "Steam"
    steam_root.mkdir()
    sapps = steam_root / "steamapps"
    sapps.mkdir()
    common = sapps / "common"
    common.mkdir()

    # 1. Counter-Strike 2 (installed)
    cs2_dir = common / "Counter-Strike Global Offensive"
    cs2_dir.mkdir()
    acf_cs2 = sapps / "appmanifest_730.acf"
    acf_cs2.write_text(
        '"AppState"\n{\n\t"appid"\t"730"\n\t"name"\t"Counter-Strike 2"\n\t"installdir"\t"Counter-Strike Global Offensive"\n\t"StateFlags"\t"4"\n}\n',
        encoding="utf-8"
    )

    # 2. Dota 2 (installed)
    dota_dir = common / "dota 2 beta"
    dota_dir.mkdir()
    acf_dota = sapps / "appmanifest_570.acf"
    acf_dota.write_text(
        '"AppState"\n{\n\t"appid"\t"570"\n\t"name"\t"Dota 2"\n\t"installdir"\t"dota 2 beta"\n\t"StateFlags"\t"4"\n}\n',
        encoding="utf-8"
    )

    # 3. Steamworks Common Redistributables (should be ignored)
    acf_redist = sapps / "appmanifest_228980.acf"
    acf_redist.write_text(
        '"AppState"\n{\n\t"appid"\t"228980"\n\t"name"\t"Steamworks Common Redistributables"\n\t"installdir"\t"Steamworks Shared"\n\t"StateFlags"\t"4"\n}\n',
        encoding="utf-8"
    )

    # 4. Uninstalled game (StateFlags 0, no folder)
    acf_uninstalled = sapps / "appmanifest_999999.acf"
    acf_uninstalled.write_text(
        '"AppState"\n{\n\t"appid"\t"999999"\n\t"name"\t"Deleted Game"\n\t"installdir"\t"NonExistentFolder"\n\t"StateFlags"\t"0"\n}\n',
        encoding="utf-8"
    )

    # 5. External library folder in libraryfolders.vdf
    ext_lib = tmp_path / "ExternalSteamLib"
    ext_lib.mkdir()
    ext_sapps = ext_lib / "steamapps"
    ext_sapps.mkdir()
    ext_common = ext_sapps / "common"
    ext_common.mkdir()
    cyberpunk_dir = ext_common / "Cyberpunk 2077"
    cyberpunk_dir.mkdir()

    acf_cp = ext_sapps / "appmanifest_1091500.acf"
    acf_cp.write_text(
        '"AppState"\n{\n\t"appid"\t"1091500"\n\t"name"\t"Cyberpunk 2077"\n\t"installdir"\t"Cyberpunk 2077"\n\t"StateFlags"\t"4"\n}\n',
        encoding="utf-8"
    )

    vdf = sapps / "libraryfolders.vdf"
    escaped_ext_path = str(ext_lib).replace("\\", "\\\\")
    vdf.write_text(
        f'"libraryfolders"\n{{\n\t"0"\n\t{{\n\t\t"path"\t"{steam_root}"\n\t}}\n\t"1"\n\t{{\n\t\t"path"\t"{escaped_ext_path}"\n\t}}\n}}\n',
        encoding="utf-8"
    )

    return steam_root


def test_steam_manager_scans_only_installed_games(fake_steam_structure):
    sm = SteamManager(steam_root=fake_steam_structure)
    games = sm.scan_installed_games()

    appids = {g["appid"] for g in games}
    # CS2, Dota 2, and Cyberpunk 2077 should be found
    assert 730 in appids
    assert 570 in appids
    assert 1091500 in appids

    # Redistributables and uninstalled games should NOT be included
    assert 228980 not in appids
    assert 999999 not in appids


def test_steam_manager_resolves_aliases_and_names(fake_steam_structure):
    sm = SteamManager(steam_root=fake_steam_structure)

    # Exact name
    assert sm.resolve_game("Counter-Strike 2")["appid"] == 730
    assert sm.resolve_game("Dota 2")["appid"] == 570
    assert sm.resolve_game("Cyberpunk 2077")["appid"] == 1091500

    # Common aliases
    assert sm.resolve_game("cs")["appid"] == 730
    assert sm.resolve_game("cs2")["appid"] == 730
    assert sm.resolve_game("dota")["appid"] == 570
    assert sm.resolve_game("cyberpunk")["appid"] == 1091500

    # steam: protocol URI syntax
    assert sm.resolve_game("steam:730")["appid"] == 730
    assert sm.resolve_game("steam://rungameid/570")["appid"] == 570

    # Non-existent game
    assert sm.resolve_game("Half-Life 3") is None


def test_steam_manager_safe_launch(fake_steam_structure):
    sm = SteamManager(steam_root=fake_steam_structure)

    with patch("os.startfile") as mock_start:
        res = sm.launch_game(730)
        assert res["success"] is True
        assert res["name"] == "Counter-Strike 2"
        assert res["url"] == "steam://rungameid/730"
        mock_start.assert_called_once_with("steam://rungameid/730")


def test_steam_manager_is_running_detection(fake_steam_structure):
    sm = SteamManager(steam_root=fake_steam_structure)

    mock_proc_cs = Mock()
    mock_proc_cs.info = {
        "pid": 1234,
        "name": "cs2.exe",
        "exe": "C:\\Games\\Steam\\steamapps\\common\\Counter-Strike Global Offensive\\game\\bin\\win64\\cs2.exe",
        "cwd": "C:\\Games\\Steam\\steamapps\\common\\Counter-Strike Global Offensive",
    }

    with patch("psutil.process_iter", return_value=[mock_proc_cs]):
        assert sm.is_game_running(730) is True
        assert sm.is_game_running(570) is False


def test_command_router_steam_game_launch(fake_steam_structure):
    from services.command_router import CommandRouter
    from core.config_manager import ConfigManager
    from core.ollama_manager import OllamaManager

    sm = SteamManager(steam_root=fake_steam_structure)
    cfg = ConfigManager()
    cfg.set("router_only_mode", True)
    router = CommandRouter(cfg, OllamaManager(), steam_manager=sm)

    with patch.object(sm, "is_game_running", return_value=False), \
         patch.object(sm, "launch_game", return_value={"success": True}) as mock_launch:
        resp = router.route("запусти кс")
        assert "Counter-Strike 2" in resp
        assert "Steam" in resp
        mock_launch.assert_called_once()


def test_command_router_steam_game_already_running(fake_steam_structure):
    from services.command_router import CommandRouter
    from core.config_manager import ConfigManager
    from core.ollama_manager import OllamaManager

    sm = SteamManager(steam_root=fake_steam_structure)
    cfg = ConfigManager()
    router = CommandRouter(cfg, OllamaManager(), steam_manager=sm)

    with patch.object(sm, "is_game_running", return_value=True):
        resp = router.route("запусти доту")
        assert "уже запущена" in resp

