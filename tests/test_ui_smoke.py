from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from starlette.testclient import TestClient

from core.app_paths import APP_ROOT
from services.gateway_service import GatewayService


def test_ui_dist_bundle_exists():
    """Verify pre-built React/Tauri distribution exists and has valid entry points."""
    dist_dir = APP_ROOT / "ui" / "dist"
    index_html = dist_dir / "index.html"
    assets_dir = dist_dir / "assets"

    assert dist_dir.is_dir(), f"UI dist directory not found at {dist_dir}"
    assert index_html.is_file(), f"index.html not found at {index_html}"
    assert assets_dir.is_dir(), f"Assets directory not found at {assets_dir}"

    html_content = index_html.read_text(encoding="utf-8")
    assert '<div id="root">' in html_content or 'id="root"' in html_content

    js_files = list(assets_dir.glob("*.js"))
    css_files = list(assets_dir.glob("*.css"))
    assert len(js_files) > 0, "No bundled JS files found in assets"
    assert len(css_files) > 0, "No bundled CSS files found in assets"


def test_ui_package_spec_has_no_electron_dependencies():
    """Verify package.json is configured for Vite/Tauri without leftover Electron dependencies."""
    pkg_file = APP_ROOT / "ui" / "package.json"
    assert pkg_file.is_file(), "ui/package.json missing"

    data = json.loads(pkg_file.read_text(encoding="utf-8"))
    dev_deps = data.get("devDependencies", {})
    deps = data.get("dependencies", {})
    scripts = data.get("scripts", {})

    assert "electron" not in dev_deps
    assert "electron" not in deps
    assert "main" not in data, "package.json should not declare main: main.js"
    assert "build" in scripts
    assert "tauri:dev" in scripts or "tauri" in scripts


def test_gateway_serves_modern_ui_index():
    """Verify FastAPI gateway properly mounts and serves the React/Tauri UI at root."""
    class DummyAppContext:
        def __init__(self):
            self.events = Mock()
            self.events.subscribe = Mock()

    gw = GatewayService(DummyAppContext())
    client = TestClient(gw.fastapi_app)

    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert '<div id="root">' in res.text or 'id="root"' in res.text


def test_ui_core_endpoints_contract():
    """Smoke test contracts for all core views: Settings, Tools, Aliases, Websites, Statistics."""
    class DummyConfig:
        data = {
            "assistant_name": "Kirieshcka",
            "model": "qwen2.5:7b",
            "voice": {"wake_word": "джарвис"},
        }
        def get(self, k, d=None):
            return self.data.get(k, d)

    class DummyAliasManager:
        def list_objects(self, cat=None):
            return [{"id": "1", "name": "Steam", "target": "steam.exe"}]

    class DummyWebsitesManager:
        def get_websites(self):
            return [{"id": "1", "name": "YouTube", "url": "https://youtube.com"}]

    class DummyStatisticsService:
        latest = None
        latest_whisper = None
        history = []
        def get_history(self):
            return []

    class DummyToolManager:
        def list_tools(self):
            return [{"name": "read_file", "category": "system", "enabled": True}]

    class DummyAppContext:
        def __init__(self):
            self.config = DummyConfig()
            self.alias_manager = DummyAliasManager()
            self.website_manager = DummyWebsitesManager()
            self.statistics_service = DummyStatisticsService()
            self.tool_manager = DummyToolManager()
            self.events = Mock()
            self.events.subscribe = Mock()

    gw = GatewayService(DummyAppContext())
    client = TestClient(gw.fastapi_app)

    # 1. Settings view contract
    s_res = client.get("/api/settings")
    assert s_res.status_code == 200
    assert "settings" in s_res.json()
    assert s_res.json()["settings"]["assistant_name"] == "Kirieshcka"

    # 2. Aliases view contract
    a_res = client.get("/api/aliases")
    assert a_res.status_code == 200
    assert "aliases" in a_res.json()
    assert len(a_res.json()["aliases"]) == 1

    # 3. Websites view contract
    w_res = client.get("/api/websites")
    assert w_res.status_code == 200
    assert "websites" in w_res.json()
    assert len(w_res.json()["websites"]) == 1

    # 4. Statistics view contract
    st_res = client.get("/api/statistics")
    assert st_res.status_code == 200
    data = st_res.json()
    assert "telemetry" in data
    assert "history" in data

    # 5. Tools & Ollama view contract
    t_res = client.get("/api/tools")
    assert t_res.status_code == 200
    assert "tools" in t_res.json()
