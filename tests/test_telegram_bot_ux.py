from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from modules.telegram_bot import TelegramBotModule


class DummyConfig:
    def __init__(self, data: dict):
        self.data = data

    def get(self, key: str, default=None):
        return self.data.get(key, default)


class DummyAppContext:
    def __init__(self):
        self.chat_service = None


def test_telegram_keyboards_structure():
    bot = TelegramBotModule()
    main_kb = bot.get_main_keyboard()
    assert "keyboard" in main_kb
    assert main_kb.get("resize_keyboard") is True
    assert any("Статус ПК" in btn["text"] for row in main_kb["keyboard"] for btn in row)

    vpn_kb = bot.get_vpn_keyboard()
    assert "inline_keyboard" in vpn_kb
    assert any("vpn:zapret" == btn["callback_data"] for row in vpn_kb["inline_keyboard"] for btn in row)

    shutdown_kb = bot.get_shutdown_keyboard()
    assert "inline_keyboard" in shutdown_kb
    assert any("shutdown:cancel" == btn["callback_data"] for row in shutdown_kb["inline_keyboard"] for btn in row)
    assert any("shutdown:reboot" == btn["callback_data"] for row in shutdown_kb["inline_keyboard"] for btn in row)

    cancel_kb = bot.get_cancel_shutdown_keyboard()
    assert "inline_keyboard" in cancel_kb
    assert cancel_kb["inline_keyboard"][0][0]["callback_data"] == "shutdown:cancel"


def test_telegram_chunk_text():
    bot = TelegramBotModule()
    short = "Hello world"
    assert bot._chunk_text(short, max_len=50) == ["Hello world"]

    long_text = ("First chunk\n" + ("a" * 4500) + "\n\nSecond chunk\n" + ("b" * 1000))
    chunks = bot._chunk_text(long_text, max_len=4000)
    assert len(chunks) == 2
    assert all(len(c) <= 4000 for c in chunks)
    assert "First chunk" in chunks[0]
    assert "Second chunk" in chunks[1]


def test_telegram_send_message_chunks_and_reply_markup():
    async def _test():
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "token123", "allowed_chat_ids": [111]}})
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        sent_payloads = []

        async def fake_post(url, json=None, **kwargs):
            sent_payloads.append(json)
            resp = MagicMock()
            resp.is_success = True
            return resp

        mock_client.post = AsyncMock(side_effect=fake_post)

        long_text = ("Part1\n" + ("x" * 3800) + "\n\nPart2\n" + ("y" * 1000))
        markup = bot.get_main_keyboard()
        ok = await bot._send_message(mock_client, 111, long_text, reply_markup=markup)

        assert ok is True
        assert len(sent_payloads) == 2
        # First chunk should NOT contain reply_markup
        assert "reply_markup" not in sent_payloads[0]
        # Final chunk MUST contain reply_markup
        assert "reply_markup" in sent_payloads[1]
        assert sent_payloads[1]["reply_markup"] == markup

    asyncio.run(_test())


def test_telegram_callback_query_vpn_and_shutdown():
    async def _test():
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "token123", "allowed_chat_ids": [111]}})
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        with patch.object(bot, "_answer_callback_query", new_callable=AsyncMock) as mock_answer, \
             patch.object(bot, "_handle_command_vpn", new_callable=AsyncMock) as mock_vpn, \
             patch.object(bot, "_handle_command_shutdown_cancel", new_callable=AsyncMock) as mock_cancel, \
             patch.object(bot, "_handle_command_reboot", new_callable=AsyncMock) as mock_reboot:

            # 1. Test VPN zapret callback
            cq_vpn = {
                "id": "cq_1",
                "from": {"id": 111},
                "message": {"chat": {"id": 111}},
                "data": "vpn:zapret",
            }
            await bot._process_update(mock_client, {"callback_query": cq_vpn})
            mock_answer.assert_called_with(mock_client, "cq_1")
            mock_vpn.assert_called_once_with(mock_client, 111, "zapret")

            # 2. Test shutdown cancel callback
            cq_cancel = {
                "id": "cq_2",
                "from": {"id": 111},
                "message": {"chat": {"id": 111}},
                "data": "shutdown:cancel",
            }
            await bot._process_update(mock_client, {"callback_query": cq_cancel})
            mock_cancel.assert_called_once_with(mock_client, 111)

            # 3. Test shutdown reboot callback
            cq_reboot = {
                "id": "cq_3",
                "from": {"id": 111},
                "message": {"chat": {"id": 111}},
                "data": "shutdown:reboot",
            }
            await bot._process_update(mock_client, {"callback_query": cq_reboot})
            mock_reboot.assert_called_once_with(mock_client, 111, "1")

    asyncio.run(_test())


def test_telegram_callback_query_rejected_when_allowlist_empty():
    async def _test():
        # Empty allowed_chat_ids must reject callback queries with alert
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "token123", "allowed_chat_ids": []}})
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        with patch.object(bot, "_answer_callback_query", new_callable=AsyncMock) as mock_answer, \
             patch.object(bot, "_handle_command_shutdown", new_callable=AsyncMock) as mock_shutdown:

            cq = {
                "id": "cq_unauth",
                "from": {"id": 999},
                "message": {"chat": {"id": 999}},
                "data": "shutdown:0",
            }
            await bot._process_update(mock_client, {"callback_query": cq})
            mock_answer.assert_called_once_with(mock_client, "cq_unauth", text="⛔ Доступ запрещен", alert=True)
            mock_shutdown.assert_not_called()

    asyncio.run(_test())


def test_telegram_reply_keyboard_buttons_dispatch():
    async def _test():
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "token123", "allowed_chat_ids": [111]}})
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        with patch.object(bot, "_handle_command_status", new_callable=AsyncMock) as mock_status, \
             patch.object(bot, "_handle_command_screen", new_callable=AsyncMock) as mock_screen, \
             patch.object(bot, "_handle_command_ping", new_callable=AsyncMock) as mock_ping, \
             patch.object(bot, "_send_message", new_callable=AsyncMock) as mock_send:

            # 1. "📊 Статус ПК" button
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "📊 Статус ПК"}})
            mock_status.assert_called_once_with(mock_client, 111)

            # 2. "📸 Скриншот" button
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "📸 Скриншот"}})
            mock_screen.assert_called_once_with(mock_client, 111)

            # 3. "📡 Сеть / Пинг" button
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "📡 Сеть / Пинг"}})
            mock_ping.assert_called_once_with(mock_client, 111)

            # 4. "🔌 Выключение" button opens shutdown menu
            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "🔌 Выключение"}})
            mock_send.assert_called()
            assert "Управление питанием ПК" in mock_send.call_args[0][2]
            assert "inline_keyboard" in mock_send.call_args[1].get("reply_markup", {})

    asyncio.run(_test())


def test_telegram_llm_fallback():
    async def _test():
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "token123", "allowed_chat_ids": [111]}})
        app_ctx = DummyAppContext()
        chat_svc = MagicMock()
        chat_svc.router = MagicMock()
        chat_svc.router.route.return_value = None  # Router fails to find direct command
        chat_svc.config = {"router_only_mode": False, "model": "test-model"}

        mock_provider = MagicMock()
        chunk1 = MagicMock()
        chunk1.text = "Привет! "
        chunk2 = MagicMock()
        chunk2.text = "Я твой ассистент."
        mock_provider.stream_chat.return_value = [chunk1, chunk2]
        chat_svc.provider = mock_provider

        app_ctx.chat_service = chat_svc
        bot = TelegramBotModule(config_manager=cfg, app_context=app_ctx)
        mock_client = AsyncMock()

        with patch.object(bot, "_send_chat_action", new_callable=AsyncMock) as mock_action, \
             patch.object(bot, "_send_message", new_callable=AsyncMock) as mock_send:

            await bot._process_update(mock_client, {"message": {"chat": {"id": 111}, "text": "расскажи шутку"}})

            mock_action.assert_called_once_with(mock_client, 111, action="typing")
            mock_send.assert_called_once()
            sent_text = mock_send.call_args[0][2]
            assert "Привет! Я твой ассистент." in sent_text

    asyncio.run(_test())
