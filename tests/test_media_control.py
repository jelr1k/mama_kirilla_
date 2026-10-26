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


def test_control_media_sound_off_both_states():
    # Состояние 1: звук включен (is_muted=False) -> выключаем
    with patch("tools.media_control.get_master_mute", return_value=False), \
         patch("tools.media_control.set_master_mute") as mock_set:
        res = control_media("sound_off")
        assert res["success"] is True
        assert "Звук выключен" in res["message"]
        mock_set.assert_called_once_with(True)

    # Состояние 2: звук уже выключен (is_muted=True) -> ничего не делаем, сообщаем
    with patch("tools.media_control.get_master_mute", return_value=True), \
         patch("tools.media_control.set_master_mute") as mock_set:
        res = control_media("sound_off")
        assert res["success"] is True
        assert "уже выключен" in res["message"]
        mock_set.assert_not_called()


def test_control_media_sound_on_both_states():
    # Состояние 1: звук выключен (is_muted=True) -> включаем
    with patch("tools.media_control.get_master_mute", return_value=True), \
         patch("tools.media_control.set_master_mute") as mock_set:
        res = control_media("sound_on")
        assert res["success"] is True
        assert "Звук включен" in res["message"]
        mock_set.assert_called_once_with(False)

    # Состояние 2: звук уже включен (is_muted=False) -> ничего не делаем, сообщаем
    with patch("tools.media_control.get_master_mute", return_value=False), \
         patch("tools.media_control.set_master_mute") as mock_set:
        res = control_media("sound_on")
        assert res["success"] is True
        assert "уже включен" in res["message"]
        mock_set.assert_not_called()


def test_control_media_toggle_mute():
    # Тоггл из выключенного состояния -> включает
    with patch("tools.media_control.get_master_mute", return_value=True), \
         patch("tools.media_control.set_master_mute") as mock_set:
        res = control_media("toggle_mute")
        assert res["success"] is True
        assert "включен" in res["message"]
        mock_set.assert_called_once_with(False)

    # Тоггл из включенного состояния -> выключает
    with patch("tools.media_control.get_master_mute", return_value=False), \
         patch("tools.media_control.set_master_mute") as mock_set:
        res = control_media("toggle_mute")
        assert res["success"] is True
        assert "выключен" in res["message"]
        mock_set.assert_called_once_with(True)


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

        with patch("tools.media_control.get_master_mute", return_value=False), \
             patch("tools.media_control.set_master_mute") as mock_set:
            reply_off = router.route("выключи звук")
            assert reply_off is not None
            assert "Звук выключен" in reply_off
            mock_set.assert_called_once_with(True)

        with patch("tools.media_control.get_master_mute", return_value=True), \
             patch("tools.media_control.set_master_mute") as mock_set:
            reply_on = router.route("включи звук")
            assert reply_on is not None
            assert "Звук включен" in reply_on
            mock_set.assert_called_once_with(False)

        with patch("tools.media_control.get_master_mute", return_value=False), \
             patch("tools.media_control.set_master_mute") as mock_set:
            reply_toggle = router.route("переключи звук")
            assert reply_toggle is not None
            mock_set.assert_called_once_with(True)

        reply_play = router.route("пауза")
        assert reply_play is not None
        assert "Воспроизведение переключено" in reply_play


def test_rofl_service_recognizes_media_actions():
    assert RoflService._router_action("сделай громче") == "media_volume_up"
    assert RoflService._router_action("прибавь звук") == "media_volume_up"
    assert RoflService._router_action("сделай потише") == "media_volume_down"
    assert RoflService._router_action("выключи звук") == "media_sound_off"
    assert RoflService._router_action("включи звук") == "media_sound_on"
    assert RoflService._router_action("переключи звук") == "media_mute_toggle"
    assert RoflService._router_action("пауза") == "media_play_pause"
    assert RoflService._router_action("следующий трек") == "media_next"
    assert RoflService._router_action("предыдущий трек") == "media_prev"
