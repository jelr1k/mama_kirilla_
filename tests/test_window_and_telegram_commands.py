from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from core.events import EventBus
from modules.telegram_bot import TelegramBotModule
from services.chat_service import ChatService
from services.command_router import CommandRouter
from services.gateway_service import GatewayService
from services.statistics_service import StatisticsService


def _make_alias_mock():
    return Mock(
        data={"apps": {}, "websites": {}, "actions": {}, "protocols": {}},
        normalize_command_text=lambda t: t,
    )


def _make_router(ui_actions=None):
    r = CommandRouter(
        alias_manager=_make_alias_mock(),
        website_manager=Mock(get_websites=lambda: [], resolve_url=lambda _t: None),
        ollama_manager=Mock(),
        protocols_manager=Mock(get_protocols=lambda: [], find_protocol_by_phrase=lambda _t: None),
        config={"assistant_name": "Kirieshcka", "tools": {"permissions": {}}},
    )
    if ui_actions is not None:
        r.set_ui_actions(ui_actions)
    return r


def test_window_commands_route_before_app_management_and_invoke_actions():
    calls = []
    actions = {
        "minimize": lambda: calls.append("minimize"),
        "hide": lambda: calls.append("hide"),
        "maximize": lambda: calls.append("maximize"),
        "restore": lambda: calls.append("restore"),
        "shutdown": lambda: calls.append("shutdown"),
    }
    router = _make_router(actions)

    assert router.route("сверни окно") == "Сворачиваю окно."
    assert router.route("свернуть окно") == "Сворачиваю окно."
    assert router.route("сверни кириешку") == "Сворачиваю окно."
    assert router.route("скрой окно") == "Сворачиваю окно."
    assert router.route("разверни окно") == "Разворачиваю окно."
    assert router.route("развернуть окно") == "Разворачиваю окно."
    assert router.route("разверни кириешку") == "Разворачиваю окно."
    assert router.route("покажи окно") == "Разворачиваю окно."
    assert router.route("восстанови окно") == "Восстанавливаю обычный размер окна."
    assert router.route("закрой себя") == "Полностью закрываю приложение."

    assert calls == [
        "minimize",
        "minimize",
        "minimize",
        "hide",
        "maximize",
        "maximize",
        "maximize",
        "maximize",
        "restore",
        "shutdown",
    ]


def test_gateway_registers_ui_actions_and_broadcasts_window_events():
    class _AppCtx:
        def __init__(self):
            self.events = EventBus()
            self.config = {"assistant_name": "Kirieshcka", "tools": {"permissions": {}}}
            self.statistics_service = StatisticsService()
            self.chat_service = ChatService(
                provider=Mock(),
                config=self.config,
                ollama_manager=Mock(),
                alias_manager=_make_alias_mock(),
                website_manager=Mock(get_websites=lambda: [], resolve_url=lambda _t: None),
                protocols_manager=Mock(get_protocols=lambda: [], find_protocol_by_phrase=lambda _t: None),
                event_bus=self.events,
            )
            self.website_manager = None
            self.permission_manager = None
            self.voice_service = None
            self.wake_word_detector = None
            self.tts_service = None
            self.dependency_manager = None
            self.update_checker = None

        def set_ui_actions(self, actions):
            self.chat_service.set_ui_actions(actions)

    ctx = _AppCtx()
    gw = GatewayService(ctx, port=8773)
    gw.hub.broadcast = MagicMock()

    assert ctx.chat_service.router.route("сверни окно") == "Сворачиваю окно."
    gw.hub.broadcast.assert_called_with({"type": "minimize_window"})

    assert ctx.chat_service.router.route("разверни окно") == "Разворачиваю окно."
    gw.hub.broadcast.assert_called_with({"type": "maximize_window"})

    assert ctx.chat_service.router.route("восстанови окно") == "Восстанавливаю обычный размер окна."
    gw.hub.broadcast.assert_called_with({"type": "restore_window"})

    assert ctx.chat_service.router.route("очисти чат") == "История чата очищена."
    gw.hub.broadcast.assert_called_with({"type": "clear_chat"})


def test_telegram_manual_text_and_russian_slash_commands():
    async def _test():
        cfg = MagicMock()
        cfg.get = lambda k, d=None: {"telegram": {"enabled": True, "bot_token": "t", "allowed_chat_ids": [111]}}.get(k, d)
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        with (
            patch.object(bot, "_handle_command_status", new_callable=AsyncMock) as mock_status,
            patch.object(bot, "_handle_command_screen", new_callable=AsyncMock) as mock_screen,
            patch.object(bot, "_handle_command_ping", new_callable=AsyncMock) as mock_ping,
            patch.object(bot, "_handle_command_sleep", new_callable=AsyncMock) as mock_sleep,
            patch.object(bot, "_send_message", new_callable=AsyncMock) as mock_send,
        ):
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "статус"}})
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "/статус"}})
            assert mock_status.call_count == 2

            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "скриншот"}})
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "/скрин"}})
            assert mock_screen.call_count == 2

            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "пинг"}})
            mock_ping.assert_called_once()

            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "/сон"}})
            mock_sleep.assert_called_once()

            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "помощь"}})
            assert any("Kirieshcka v2 Remote Control" in call.args[2] for call in mock_send.call_args_list)

    asyncio.run(_test())


def test_alo_deterministic_auto_reply():
    events = EventBus()
    direct_replies = []
    events.subscribe("chat.direct_response", lambda text: direct_replies.append(text))

    provider = Mock()
    service = ChatService(
        provider=provider,
        config={"assistant_name": "Kirieshcka", "model": "qwen3:1.7b", "tools": {"permissions": {}}},
        ollama_manager=Mock(),
        event_bus=events,
    )

    for variant in ("ало", "Ало", "АЛО!", "ало?", "алло..."):
        assert service.router.route(variant) == "ало да, вас не слышно"

    assert service.router.route("алоха") is None

    service.send("ало")
    assert direct_replies == ["ало да, вас не слышно"]
    provider.stream_chat.assert_not_called()
