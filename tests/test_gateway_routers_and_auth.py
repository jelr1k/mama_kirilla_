from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from core.events import EventBus
from services.gateway_service import GatewayService
from services.statistics_service import StatisticsService


class _AppCtx:
    def __init__(self):
        self.events = EventBus()
        self.config = {"assistant_name": "Kirieshcka", "model": "qwen3:1.7b"}
        self.chat_service = Mock()
        self.chat_service.router = Mock(command_catalog=Mock(return_value=[{"id": "t", "name": "Тест"}]))
        self.website_manager = None
        self.permission_manager = None
        self.statistics_service = StatisticsService()
        self.voice_service = Mock()
        self.wake_word_detector = Mock()
        self.tts_service = Mock()
        self.dependency_manager = Mock()
        self.update_checker = None
        self.protocols_manager = Mock()
        self.ollama_manager = Mock()


def test_gateway_http_and_ws_auth_enforcement(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("JARVIS_DISABLE_AUTH", raising=False)

    gw = GatewayService(_AppCtx(), port=8774)
    gw.session_token = "secret-session-token"
    client = TestClient(gw.fastapi_app)

    # /health is always public
    assert client.get("/health").status_code == 200

    # Protected route rejects missing or wrong token
    assert client.get("/api/commands").status_code == 401
    assert client.get("/api/commands", headers={"Authorization": "Bearer wrong"}).status_code == 401

    # Accepts Bearer and X-Session-Token
    ok_bearer = client.get("/api/commands", headers={"Authorization": "Bearer secret-session-token"})
    assert ok_bearer.status_code == 200
    assert ok_bearer.json() == {"commands": [{"id": "t", "name": "Тест"}]}

    ok_header = client.get("/api/commands", headers={"X-Session-Token": "secret-session-token"})
    assert ok_header.status_code == 200

    # WebSocket rejects bad token and untrusted origin
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?token=bad-token"):
            pass

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?token=secret-session-token", headers={"Origin": "https://evil.example"}):
            pass

    # Valid origin + token succeeds
    with client.websocket_connect("/ws?token=secret-session-token", headers={"Origin": "tauri://localhost"}) as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "state"


def test_chat_router_endpoints():
    ctx = _AppCtx()
    gw = GatewayService(ctx, port=8775)
    client = TestClient(gw.fastapi_app)

    assert client.post("/api/chat", json={"text": "   "}).json() == {"success": False, "error": "Empty message"}
    assert client.post("/api/chat", json={"text": "привет"}).json() == {"success": True}
    ctx.chat_service.send.assert_called_with("привет")

    assert client.post("/api/commands/execute", json={"command": ""}).json() == {"success": False, "error": "Empty command"}
    assert client.post("/api/commands/execute", json={"command": "время"}).json() == {"success": True}
    ctx.chat_service.send.assert_called_with("время")

    ctx.chat_service = None
    assert client.post("/api/chat", json={"text": "тест"}).json()["success"] is False
    assert client.post("/api/commands/execute", json={"command": "тест"}).json()["success"] is False
    assert client.get("/api/commands").json() == {"commands": []}


def test_voice_router_endpoints():
    ctx = _AppCtx()
    ctx.voice_service.list_microphones.return_value = {"success": True, "devices": [{"id": 0, "name": "Mic"}]}
    ctx.dependency_manager.whisper_status.return_value = "installed"
    ctx.tts_service.voice_status.return_value = "missing"
    ctx.ollama_manager.get_loaded_models.return_value = [{"name": "qwen3:1.7b"}]

    gw = GatewayService(ctx, port=8776)
    client = TestClient(gw.fastapi_app)

    assert client.get("/api/microphones").json()["devices"] == [{"id": 0, "name": "Mic"}]

    tts_ok = client.post("/api/tts/test", json={"text": "Проверка"}).json()
    assert tts_ok == {"success": True}
    ctx.tts_service.speak.assert_called_once_with("Проверка")

    ctx.tts_service.speak.side_effect = RuntimeError("audio busy")
    tts_err = client.post("/api/tts/test", json={"text": "Проверка"}).json()
    assert tts_err == {"success": False, "error": "audio busy"}

    assert client.get("/api/whisper/status").json()["statuses"]["small"] == "installed"
    assert client.get("/api/tts/status").json()["statuses"]["ru_RU-dmitri-medium"] == "missing"

    ctx.ollama_manager.start.return_value = "started"
    assert client.post("/api/ollama/restart").json() == {"success": True, "result": "started"}

    with patch("services.gateway.routers.voice.ModelService") as mock_ms:
        mock_ms.return_value.get_available_models.return_value = {"models": ["qwen3:1.7b"]}
        ctx.provider = object()
        models_res = client.get("/api/models").json()
        assert models_res["current_model"] == "qwen3:1.7b"
        assert models_res["loaded_models"] == ["qwen3:1.7b"]


def test_gateway_client_actions_and_event_bus_forwarding():
    ctx = _AppCtx()
    ctx.wake_word_detector.is_running.return_value = True
    ctx.protocols_manager.get_active_profile.return_value = "default"
    ctx.protocols_manager.list_profiles.return_value = {"default": "Основной"}
    ctx.protocols_manager.get_protocols.return_value = [{"id": "work"}]
    ctx.protocols_manager.get_protocol_by_id.return_value = {"id": "work", "name": "Работа", "open_apps": []}

    gw = GatewayService(ctx, port=8777)
    gw.hub.broadcast = Mock()

    gw._handle_client_action("voice.start", {})
    ctx.wake_word_detector.stop.assert_called_once()
    ctx.voice_service.start.assert_called_once()

    gw._handle_client_action("voice.stop", {})
    ctx.voice_service.stop.assert_called_once()

    gw._handle_client_action("tts.stop", {})
    ctx.tts_service.stop.assert_called_once()

    gw._handle_client_action("wake_word.toggle", {"enabled": True})
    ctx.wake_word_detector.start.assert_called_once()

    gw._handle_client_action("protocols.get", {})
    gw.hub.broadcast.assert_called_with({
        "type": "protocols",
        "data": {
            "active_profile": "default",
            "profiles": {"default": "Основной"},
            "protocols": [{"id": "work"}],
        },
    })

    with patch("services.stark_protocols.StarkProtocols.execute_protocol", return_value="Готово") as mock_exec:
        gw._handle_client_action("protocols.execute", {"protocol_id": "work"})
        mock_exec.assert_called_once()
        gw.hub.broadcast.assert_called_with({"type": "protocol.executed", "protocol_id": "work", "result": "Готово"})

    # EventBus -> WebSocketHub forwarding
    ctx.events.emit("chat.direct_response", "Ответ роутера")
    gw.hub.broadcast.assert_called_with({"type": "chat.response", "text": "Ответ роутера"})

    ctx.events.emit("chat.rofl_response", "Шутка")
    gw.hub.broadcast.assert_called_with({"type": "chat.response", "text": "Шутка", "is_rofl": True})

    ctx.events.emit("tts.state_changed", "speaking", "Привет")
    gw.hub.broadcast.assert_called_with({"type": "tts.state", "state": "speaking", "message": "Привет"})
