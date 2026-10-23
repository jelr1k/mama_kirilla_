from __future__ import annotations

from unittest.mock import Mock, patch

from core.alias_manager import AliasManager
from services.command_router import CommandRouter
from services.rofl_service import RoflService
from tools.media_control import control_media, VK_MAP


def test_control_media_sends_keys():
    with patch("tools.media_control._send_key") as mock_send:
        res = control_media("volume_up", steps=4)
        assert res["success"] is True
        assert res["media_control"] is True
        assert "Громкость увеличена" in res["message"]
        mock_send.assert_called_once_with(VK_MAP["volume_up"], repeat=4)

    with patch("tools.media_control._send_key") as mock_send:
        res = control_media("volume_mute")
        assert res["success"] is True
        mock_send.assert_called_once_with(VK_MAP["volume_mute"], repeat=1)


def test_control_media_rejects_unknown_action():
    res = control_media("unknown_action")
    assert res["success"] is False
    assert "Неизвестное действие медиа" in res["error"]


def test_command_router_routes_media_commands():
    config = {
        "tools": {"control_media": True},
        "model": "qwen",
        "temperature": 0.7,
        "context_length": 4096,
        "max_tokens": 128,
    }
    router = CommandRouter(config, Mock(), AliasManager())

    with patch("tools.media_control._send_key"):
        reply = router.route("сделай потише")
        assert reply is not None
        assert "Громкость уменьшена" in reply

        reply_mute = router.route("выключи звук")
        assert reply_mute is not None
        assert "Звук переключен" in reply_mute

        reply_play = router.route("пауза")
        assert reply_play is not None
        assert "Воспроизведение переключено" in reply_play


def test_rofl_service_recognizes_media_actions():
    assert RoflService._router_action("сделай громче") == "media_volume_up"
    assert RoflService._router_action("прибавь звук") == "media_volume_up"
    assert RoflService._router_action("сделай потише") == "media_volume_down"
    assert RoflService._router_action("выключи звук") == "media_mute"
    assert RoflService._router_action("пауза") == "media_play_pause"
    assert RoflService._router_action("следующий трек") == "media_next"
    assert RoflService._router_action("предыдущий трек") == "media_prev"
