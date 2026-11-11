from __future__ import annotations

from unittest.mock import patch
from starlette.testclient import TestClient

from core.events import EventBus
from services.gateway_service import GatewayService
from services.statistics_service import StatisticsService


class _DummyCtx:
    def __init__(self):
        self.events = EventBus()
        self.config = None
        self.chat_service = None
        self.website_manager = None
        self.permission_manager = None
        self.statistics_service = StatisticsService()
        self.voice_service = None
        self.wake_word_detector = None
        self.tts_service = None
        self.dependency_manager = None
        self.update_checker = None


def test_media_status_and_control_endpoints():
    gw = GatewayService(_DummyCtx(), port=8771)
    client = TestClient(gw.fastapi_app)

    with (
        patch("tools.media_control.get_master_volume_scalar", return_value=0.64),
        patch("tools.media_control.get_master_mute", return_value=False),
    ):
        res = client.get("/api/media/status")
        assert res.status_code == 200
        assert res.json() == {"volume": 64, "muted": False}

    with (
        patch("tools.media_control.set_master_volume_scalar", return_value=True) as mock_set,
        patch("tools.media_control.get_master_volume_scalar", return_value=0.8),
        patch("tools.media_control.get_master_mute", return_value=False),
    ):
        res = client.post("/api/media/control", json={"action": "set_volume", "level": 80})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["volume"] == 80
        mock_set.assert_called_once_with(0.8)

    with (
        patch("tools.media_control.control_media", return_value={"success": True, "action": "play_pause"}) as mock_ctrl,
        patch("tools.media_control.get_master_volume_scalar", return_value=0.8),
        patch("tools.media_control.get_master_mute", return_value=False),
    ):
        res = client.post("/api/media/control", json={"action": "play_pause"})
        assert res.status_code == 200
        assert res.json()["success"] is True
        mock_ctrl.assert_called_once_with(action="play_pause", steps=5)

    invalid_res = client.post("/api/media/control", json={"action": "set_volume", "level": "abc"})
    assert invalid_res.status_code == 200
    assert invalid_res.json()["success"] is False


def test_system_quick_action_endpoint():
    gw = GatewayService(_DummyCtx(), port=8772)
    client = TestClient(gw.fastapi_app)

    with patch("tools.system_actions.take_screenshot", return_value={"success": True, "content": "Скриншот сохранён."}) as mock_shot:
        res = client.post("/api/system/quick-action", json={"action": "screenshot"})
        assert res.status_code == 200
        assert res.json()["success"] is True
        mock_shot.assert_called_once()

    unknown_res = client.post("/api/system/quick-action", json={"action": "rm_rf"})
    assert unknown_res.status_code == 200
    assert unknown_res.json()["success"] is False
