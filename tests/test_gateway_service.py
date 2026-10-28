from __future__ import annotations

import time
import pytest
from starlette.testclient import TestClient

from core.events import EventBus
from services.gateway_service import GatewayService
from services.statistics_service import StatisticsService


class DummyConfig:
    def __init__(self):
        self.data = {
            "assistant_name": "Kirieshcka",
            "model": "qwen:7b",
            "voice": {"wake_word_enabled": True},
            "rofl": {"chance": 0.12, "demon_chance": 0.15},
            "tools": {"permissions": {}},
        }

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        pass


class DummyChatService:
    def __init__(self):
        self.sent_messages = []

    def send(self, text: str):
        self.sent_messages.append(text)


class DummyWebsiteManager:
    def __init__(self):
        self.sites = [
            {"id": "youtube", "name": "YouTube", "url": "https://youtube.com", "aliases": ["ютуб"]},
        ]

    def get_websites(self):
        return list(self.sites)

    def add_website(self, name, url, aliases=None, auto_aliases=True):
        site_id = name.lower()
        entry = {"id": site_id, "name": name, "url": url, "aliases": aliases or []}
        self.sites.append(entry)
        return entry

    def update_website(self, site_id, name, url, aliases):
        for s in self.sites:
            if s["id"] == site_id:
                s["name"] = name
                s["url"] = url
                s["aliases"] = aliases
                return True
        return False

    def delete_website(self, site_id):
        initial_len = len(self.sites)
        self.sites = [s for s in self.sites if s["id"] != site_id]
        return len(self.sites) < initial_len

    def reset_to_defaults(self):
        self.sites = [{"id": "youtube", "name": "YouTube", "url": "https://youtube.com", "aliases": ["ютуб"]}]


class DummyPermissionManager:
    def __init__(self):
        self.permissions = {}

    def is_enabled(self, tool_name: str) -> bool:
        return self.permissions.get(tool_name, True)

    def update(self, tool_name: str, enabled: bool) -> None:
        self.permissions[tool_name] = enabled


class DummyAppContext:
    def __init__(self):
        self.events = EventBus()
        self.config = DummyConfig()
        self.chat_service = DummyChatService()
        self.website_manager = DummyWebsiteManager()
        self.permission_manager = DummyPermissionManager()
        self.statistics_service = StatisticsService()
        self.voice_service = None
        self.wake_word_detector = None
        self.tts_service = None
        self.dependency_manager = None
        self.update_checker = None


def test_gateway_health_endpoint():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Kirieshcka v2"


def test_gateway_telemetry_endpoint():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    response = client.get("/api/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data or "error" in data


def test_gateway_settings_endpoints():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    # GET settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    assert get_res.json()["settings"]["assistant_name"] == "Kirieshcka"

    # POST settings
    post_res = client.post("/api/settings", json={"assistant_name": "NewName"})
    assert post_res.status_code == 200
    assert post_res.json()["success"] is True
    assert app_ctx.config.get("assistant_name") == "NewName"


def test_gateway_chat_endpoint():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    res = client.post("/api/chat", json={"text": "Привет"})
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert app_ctx.chat_service.sent_messages == ["Привет"]


def test_gateway_websites_endpoints():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    # GET
    res = client.get("/api/websites")
    assert res.status_code == 200
    assert len(res.json()["websites"]) == 1

    # POST (create)
    create_res = client.post("/api/websites", json={"name": "VK", "url": "https://vk.com", "aliases": ["вконтакте"]})
    assert create_res.status_code == 200
    assert create_res.json()["success"] is True

    # PUT (update)
    update_res = client.put("/api/websites/vk", json={"name": "VKontakte", "url": "https://vk.com", "aliases": ["вк"]})
    assert update_res.status_code == 200
    assert update_res.json()["success"] is True

    # DELETE
    del_res = client.delete("/api/websites/vk")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_gateway_tools_permissions_endpoints():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    # GET tools list
    tools_res = client.get("/api/tools")
    assert tools_res.status_code == 200
    tools = tools_res.json()["tools"]
    assert len(tools) > 0
    assert any(t["name"] == "search_files" for t in tools)

    # POST toggle permission
    perm_res = client.post("/api/tools/permission", json={"tool": "search_files", "enabled": False})
    assert perm_res.status_code == 200
    assert perm_res.json()["success"] is True
    assert app_ctx.permission_manager.is_enabled("search_files") is False


def test_gateway_statistics_endpoint():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    # Add mock generation stats
    class DummyStats:
        model = "qwen:7b"
        input_tokens = 50
        output_tokens = 100
        total_tokens = 150
        generation_time_s = 2.0
        generation_speed_tps = 50.0
        total_time_s = 2.1
        load_time_s = 0.0
        prompt_eval_time_s = 0.05
        ttft_s = 0.06
        thinking = False

    app_ctx.statistics_service.add(DummyStats())

    res = client.get("/api/statistics")
    assert res.status_code == 200
    data = res.json()
    assert data["latest_llm"]["model"] == "qwen:7b"
    assert data["latest_llm"]["generation_speed_tps"] == 50.0
    assert len(data["history"]) == 1


def test_gateway_rofl_settings_and_secret():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    # GET rofl
    get_res = client.get("/api/rofl")
    assert get_res.status_code == 200
    assert get_res.json()["chance"] == 0.12

    # Verify secret - wrong word
    bad_verify = client.post("/api/rofl/verify", json={"secret": "wrong"})
    assert bad_verify.json()["unlocked"] is False

    # Verify secret - correct word "джарвис"
    good_verify = client.post("/api/rofl/verify", json={"secret": "Джарвис"})
    assert good_verify.json()["unlocked"] is True

    # Update rofl - correct secret
    update_res = client.post("/api/rofl", json={"secret": "джарвис", "chance": 0.25, "demon_chance": 0.30})
    assert update_res.status_code == 200
    assert update_res.json()["success"] is True
    assert app_ctx.config.get("rofl")["chance"] == 0.25


def test_gateway_websocket_connection_and_events():
    app_ctx = DummyAppContext()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    with client.websocket_connect("/ws") as ws:
        # First message sent on connect is the initial state
        initial = ws.receive_json()
        assert initial["type"] == "state"
        assert initial["assistant_name"] == "Kirieshcka"

        # Send chat action over websocket
        ws.send_json({"action": "chat.send", "text": "Тест вебсокета"})
        time.sleep(0.05)
        assert app_ctx.chat_service.sent_messages == ["Тест вебсокета"]


def test_gateway_updates_endpoints():
    app_ctx = DummyAppContext()

    class DummyUpdateInfo:
        current_version = "0.1.7"
        latest_version = "0.1.8"
        update_available = True
        release_url = "https://github.com/jelr1k/mama_kirilla_/releases"

    class DummyUpdatePlan:
        asset_name = "jarvis-0.1.8.zip"
        asset_size = 10485760
        target_version = "0.1.8"

    class DummyChecker:
        def check(self):
            return DummyUpdateInfo()

    class DummyService:
        def prepare(self, info):
            return DummyUpdatePlan()

    app_ctx.update_checker = DummyChecker()
    app_ctx.update_service = DummyService()

    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    res = client.get("/api/updates")
    assert res.status_code == 200
    data = res.json()
    assert data["has_update"] is True
    assert data["latest_version"] == "0.1.8"
    assert data["plan_available"] is True
    assert data["archive_name"] == "jarvis-0.1.8.zip"


def test_gateway_ollama_unload_endpoint():
    class DummyOllamaMgr:
        def unload_models(self):
            return [{"model": "qwen3:1.7b", "success": True}]
        def get_loaded_models(self):
            return [{"name": "qwen3:1.7b"}]
        def unload_model(self, m):
            return {"model": m, "success": True}

    app_ctx = DummyAppContext()
    app_ctx.ollama_manager = DummyOllamaMgr()
    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    res = client.post("/api/ollama/unload")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert "qwen3:1.7b" in res.json()["unloaded"]



def test_gateway_protocols_and_steam_endpoints(tmp_path):
    from core.protocols_manager import ProtocolsManager
    from core.steam_manager import SteamManager
    from unittest.mock import patch, MagicMock

    proto_file = tmp_path / "protocols.json"
    pm = ProtocolsManager(file_path=proto_file)
    sm = SteamManager()

    app_ctx = DummyAppContext()
    app_ctx.protocols_manager = pm
    app_ctx.steam_manager = sm

    gw = GatewayService(app_ctx, port=8769)
    client = TestClient(gw.fastapi_app)

    # 1. GET /api/protocols
    res = client.get("/api/protocols")
    assert res.status_code == 200
    data = res.json()
    assert data["active_profile"] == "default"
    assert "default" in data["profiles"]
    assert len(data["protocols"]) >= 5

    # 2. POST /api/protocols/profile (create profile)
    res_create = client.post("/api/protocols/profile", json={"name": "Тестовый профиль", "copy_from_active": True})
    assert res_create.status_code == 200
    create_data = res_create.json()
    assert create_data["success"] is True
    new_pid = create_data["profile_id"]
    assert new_pid in create_data["profiles"]

    # 3. POST /api/protocols/profile/select
    res_select = client.post("/api/protocols/profile/select", json={"profile_id": new_pid})
    assert res_select.status_code == 200
    assert res_select.json()["active_profile"] == new_pid

    # 4. POST /api/protocols (create protocol)
    new_proto = {
        "id": "test_protocol",
        "name": "Тестовый сценарий",
        "phrases": ["тест сценарий"],
        "response_text": "Тест выполнен успешно.",
    }
    res_proto = client.post("/api/protocols", json={"protocol": new_proto})
    assert res_proto.status_code == 200
    assert res_proto.json()["success"] is True
    assert res_proto.json()["protocol_id"] == "test_protocol"

    # 5. POST /api/protocols/execute
    with patch("services.stark_protocols.StarkProtocols.execute_protocol", return_value="Тест выполнен успешно.") as mock_exec:
        res_exec = client.post("/api/protocols/execute", json={"protocol_id": "test_protocol"})
        assert res_exec.status_code == 200
        assert res_exec.json()["success"] is True
        assert res_exec.json()["result"] == "Тест выполнен успешно."
        mock_exec.assert_called_once()

    # 6. DELETE /api/protocols/{protocol_id}
    res_del_proto = client.delete("/api/protocols/test_protocol")
    assert res_del_proto.status_code == 200
    assert res_del_proto.json()["success"] is True

    # 7. DELETE /api/protocols/profile/{profile_id}
    res_del_profile = client.delete(f"/api/protocols/profile/{new_pid}")
    assert res_del_profile.status_code == 200
    assert res_del_profile.json()["success"] is True

    # 8. GET /api/steam
    with patch.object(sm, "scan_installed_games", return_value=[{"appid": 730, "name": "Counter-Strike 2", "clean_name": "counter-strike 2"}]), \
         patch.object(sm, "is_steam_installed", return_value=True):
        res_steam = client.get("/api/steam")
        assert res_steam.status_code == 200
        steam_data = res_steam.json()
        assert steam_data["installed"] is True
        assert len(steam_data["games"]) == 1
        assert steam_data["games"][0]["appid"] == 730

    # 9. POST /api/steam/launch
    with patch.object(sm, "launch_game", return_value={"success": True, "name": "Counter-Strike 2", "appid": 730}) as mock_launch:
        res_launch = client.post("/api/steam/launch", json={"appid": 730})
        assert res_launch.status_code == 200
        assert res_launch.json()["success"] is True
        mock_launch.assert_called_once_with(730)
