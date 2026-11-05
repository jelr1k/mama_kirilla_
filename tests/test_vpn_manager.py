from __future__ import annotations

from pathlib import Path

from core.vpn_manager import NOT_FOUND_MESSAGE, VpnManager, normalize_client


def test_normalize_client_aliases():
    assert normalize_client("happ") == "happ"
    assert normalize_client("Хапп") == "happ"
    assert normalize_client("FlClashX") == "flclash"
    assert normalize_client("флклэш") == "flclash"
    assert normalize_client("unknown") is None


def test_connect_returns_exact_not_found_message(monkeypatch):
    manager = VpnManager()
    monkeypatch.setattr(manager, "_discover_client", lambda key: None)

    result = manager.connect("flclash")

    assert result["success"] is False
    assert result["error"] == NOT_FOUND_MESSAGE
    assert result["message"].startswith(NOT_FOUND_MESSAGE)


def test_launch_zapret_opens_found_service_bat(tmp_path, monkeypatch):
    service_bat = tmp_path / "zapret" / "service.bat"
    service_bat.parent.mkdir()
    service_bat.write_text("@echo off\n", encoding="utf-8")
    (service_bat.parent / "bin").mkdir()
    (service_bat.parent / "bin" / "winws.exe").write_bytes(b"")

    opened = []
    manager = VpnManager()
    monkeypatch.setattr(manager, "_find_service_bat", lambda: service_bat)
    monkeypatch.setattr("os.startfile", lambda path: opened.append(path))

    result = manager.launch_zapret()

    assert result["success"] is True
    assert opened == [str(service_bat)]
    assert result["path"] == str(service_bat)


def test_zapret_status_reports_archive_when_service_missing(tmp_path, monkeypatch):
    archive = tmp_path / "zapret-discord-youtube.zip"
    archive.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    manager = VpnManager()
    monkeypatch.setattr(manager, "_find_service_bat", lambda: None)
    monkeypatch.setattr(manager, "_find_zapret_archive", lambda: archive)
    monkeypatch.setattr("core.vpn_manager._process_running", lambda names: False)

    result = manager._zapret_status(force=True)

    assert result["found"] is True
    assert result["source"] == "archive"
    assert result["path"] == str(archive)


def test_looks_like_zapret_detects_markers(tmp_path):
    folder = tmp_path / "zapret"
    (folder / "bin").mkdir(parents=True)
    (folder / "bin" / "winws.exe").write_bytes(b"")
    assert VpnManager._looks_like_zapret(folder) is True

    empty = tmp_path / "empty"
    empty.mkdir()
    assert VpnManager._looks_like_zapret(empty) is False


def test_client_status_separates_gui_and_vpn(monkeypatch):
    manager = VpnManager()
    monkeypatch.setattr(manager, "_discover_client", lambda key: Path("C:/dummy/Happ.exe"))

    # Симулируем случай: служба happd.exe запущена, но окно Happ.exe закрыто
    def mock_process_running(names):
        return any(name.casefold() == "happd.exe" for name in names)

    monkeypatch.setattr("core.vpn_manager._process_running", mock_process_running)

    status = manager._client_status("happ", force=True)
    assert status["found"] is True
    assert status["gui_running"] is False
    assert status["vpn_running"] is True
    assert status["running"] is True
    assert "окно закрыто" in status["message"]
    assert "VPN работает" in status["message"]


def test_vpn_package_exports_and_singleton():
    from core.vpn import VpnManager as PkgVpnManager, get_vpn_manager
    manager1 = get_vpn_manager()
    manager2 = get_vpn_manager()
    assert isinstance(manager1, PkgVpnManager)
    assert manager1 is manager2


def test_extract_zapret_prevents_directory_traversal(tmp_path, monkeypatch):
    import zipfile
    from core.vpn.zapret_controller import extract_zapret

    archive_path = tmp_path / "malicious.zip"
    target_dir = tmp_path / "app_data"
    target_dir.mkdir()
    monkeypatch.setattr("core.app_paths.APP_DATA_DIR", target_dir)

    with zipfile.ZipFile(archive_path, "w") as zf:
        # Корректный файл
        zf.writestr("service.bat", "@echo off\n")
        zf.writestr("bin/winws.exe", "")
        # Опасный файл вне целевой директории
        zf.writestr("../evil.txt", "hacked")

    bat = extract_zapret(archive_path)
    assert bat is not None
    assert bat.is_file()
    assert not (tmp_path / "evil.txt").exists()


def test_control_area_and_largest_unlabeled_button():
    from core.vpn.uia_driver import control_area, largest_unlabeled_button

    class DummyRect:
        def __init__(self, left, top, right, bottom):
            self.left = left
            self.top = top
            self.right = right
            self.bottom = bottom

    class DummyControl:
        def __init__(self, name, rect, c_type="ButtonControl", enabled=True, offscreen=False):
            self.Name = name
            self.BoundingRectangle = rect
            self.ControlTypeName = c_type
            self.IsEnabled = enabled
            self.IsOffscreen = offscreen

    c1 = DummyControl("Submit", DummyRect(0, 0, 100, 50))
    assert control_area(c1) == 5000

    # Без имени, площадь 10000
    big_unlabeled = DummyControl("", DummyRect(0, 0, 100, 100))
    # Маленькая без имени
    small_unlabeled = DummyControl("", DummyRect(0, 0, 10, 10))

    chosen = largest_unlabeled_button([c1, big_unlabeled, small_unlabeled])
    assert chosen is big_unlabeled


def test_vpn_manager_backwards_compatibility_shims(monkeypatch):
    import core.vpn_manager as vm

    # Проверка доступности модулей для monkeypatch
    assert hasattr(vm, "os")
    assert hasattr(vm, "psutil")

    # Проверка живой связи vm._manager с синглтоном
    initial = vm.get_vpn_manager()
    assert vm._manager is initial
    vm._manager = None
    assert vm._manager is None
    second = vm.get_vpn_manager()
    assert vm._manager is second


