from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from modules.network_checker import NetworkChecker, get_network_checker
from modules.telegram_bot import TelegramBotModule, get_telegram_bot
from services.gateway_service import GatewayService


class DummyConfig:
    def __init__(self, data: dict | None = None):
        self.data = data or {}

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value

    def save(self):
        pass


class DummyAppContext:
    def __init__(self):
        self.config = DummyConfig({
            "assistant_name": "Kirieshcka",
            "model": "qwen3",
            "telegram": {
                "enabled": True,
                "bot_token": "123456:FAKE_TOKEN",
                "allowed_chat_ids": [12345678],
                "notify_on_startup": False,
            },
        })
        self.chat_service = MagicMock()
        self.events = MagicMock()


def test_network_checker_caching_and_structure():
    async def _test():
        mock_targets = [
            {"id": "discord", "name": "Discord", "url": "https://discord.com", "icon": "discord"},
            {"id": "youtube", "name": "YouTube", "url": "https://youtube.com", "icon": "youtube"},
        ]
        checker = NetworkChecker(targets=mock_targets, cache_ttl=5.0)

        async def fake_check_single(client, target):
            return {
                "id": target["id"],
                "name": target["name"],
                "url": target["url"],
                "icon": target["icon"],
                "status": "ok",
                "ping_ms": 42,
                "http_code": 200,
                "message": "200 OK",
            }

        with patch.object(checker, "_check_single", side_effect=fake_check_single):
            res1 = await checker.check_all(force=True)
            assert res1["summary"]["status"] == "all_ok"
            assert res1["summary"]["ok_count"] == 2
            assert len(res1["services"]) == 2

            res2 = await checker.check_all(force=False)
            assert res2["timestamp"] == res1["timestamp"]

    asyncio.run(_test())


def test_telegram_bot_config_and_status():
    cfg = DummyConfig({
        "telegram": {
            "enabled": True,
            "bot_token": "999:TEST_TOKEN",
            "allowed_chat_ids": ["123", "456"],
            "notify_on_startup": True,
        }
    })
    bot = TelegramBotModule(config_manager=cfg)

    assert bot.is_enabled is True
    assert bot.bot_token == "999:TEST_TOKEN"
    assert bot.allowed_chat_ids == {123, 456}
    assert bot.notify_on_startup is True

    status = bot.get_status()
    assert status["enabled"] is True
    assert status["configured"] is True
    assert status["allowed_chat_count"] == 2


def test_telegram_bot_test_token_invalid():
    async def _test():
        bot = TelegramBotModule()
        res = await bot.test_token("")
        assert res["success"] is False
        assert "Токен не указан" in res["error"]

    asyncio.run(_test())


def test_telegram_bot_process_update_unauthorized():
    async def _test():
        cfg = DummyConfig({
            "telegram": {
                "enabled": True,
                "bot_token": "fake",
                "allowed_chat_ids": [11111],
            }
        })
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        with patch.object(bot, "_send_message", new_callable=AsyncMock) as mock_send:
            unauth_update = {
                "message": {
                    "chat": {"id": 99999},
                    "text": "/status",
                }
            }
            await bot._process_update(mock_client, unauth_update)
            mock_send.assert_called_once()
            sent_text = mock_send.call_args[0][2]
            assert "Доступ запрещен" in sent_text
            assert "99999" in sent_text

    asyncio.run(_test())


def test_telegram_bot_process_update_authorized_status():
    async def _test():
        cfg = DummyConfig({
            "telegram": {
                "enabled": True,
                "bot_token": "fake",
                "allowed_chat_ids": [11111],
            }
        })
        bot = TelegramBotModule(config_manager=cfg)
        mock_client = AsyncMock()

        with patch.object(bot, "_handle_command_status", new_callable=AsyncMock) as mock_status:
            auth_update = {
                "message": {
                    "chat": {"id": 11111},
                    "text": "/status",
                }
            }
            await bot._process_update(mock_client, auth_update)
            mock_status.assert_called_once_with(mock_client, 11111)

    asyncio.run(_test())


def test_gateway_network_and_telegram_endpoints():
    app_context = DummyAppContext()
    gateway = GatewayService(app_context=app_context, port=9999)
    client = TestClient(gateway.fastapi_app)

    # 1. Test /api/network/services
    fake_payload = {
        "timestamp": 12345.0,
        "summary": {"status": "all_ok", "ok_count": 5, "total": 5},
        "services": [],
    }
    with patch("modules.network_checker.get_network_checker") as mock_gnc:
        mock_inst = MagicMock()
        mock_inst.check_all = AsyncMock(return_value=fake_payload)
        mock_gnc.return_value = mock_inst

        resp = client.get("/api/network/services")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["status"] == "all_ok"

    # 2. Test /api/telegram/status
    resp = client.get("/api/telegram/status")
    assert resp.status_code == 200
    st_data = resp.json()
    assert "enabled" in st_data
    assert "configured" in st_data

    # 3. Test /api/telegram/test with empty token
    resp = client.post("/api/telegram/test", json={"token": ""})
    assert resp.status_code == 200
    test_data = resp.json()
    assert test_data["success"] is False

    # 4. Test /api/settings update includes telegram
    resp = client.post("/api/settings", json={
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "allowed_chat_ids": [],
            "notify_on_startup": False,
        }
    })
    assert resp.status_code == 200
    assert app_context.config.data["telegram"]["enabled"] is False



def test_telegram_bot_choice_selector_does_not_consume_pending_choices():
    async def _test():
        from pathlib import Path
        from tools import applications
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "fake", "allowed_chat_ids": [11111]}})
        app_ctx = DummyAppContext()
        app_ctx.chat_service = MagicMock()
        app_ctx.chat_service.router = MagicMock()
        bot = TelegramBotModule(config_manager=cfg, app_context=app_ctx)
        mock_client = AsyncMock()

        applications._PENDING_LAUNCH_CHOICES = [Path("app1.exe"), Path("app2.exe")]

        with patch.object(bot, "_send_message", new_callable=AsyncMock) as mock_send:
            update = {"message": {"chat": {"id": 11111}, "text": "1"}}
            await bot._process_update(mock_client, update)

            # Router should NOT be called with "1"
            assert not app_ctx.chat_service.router.route.called
            # Pending choices must remain intact
            assert len(applications._PENDING_LAUNCH_CHOICES) == 2
            assert "только в локальном интерфейсе" in mock_send.call_args[0][2]

        applications._PENDING_LAUNCH_CHOICES = []

    asyncio.run(_test())


def test_telegram_bot_session_stale_token_does_not_kill_newer_session():
    async def _test():
        cfg = DummyConfig({"telegram": {"enabled": True, "bot_token": "fake", "allowed_chat_ids": [11111]}})
        import threading
        bot = TelegramBotModule(config_manager=cfg)

        bot._running = True
        bot._session_id = 1
        stop_event = threading.Event()

        with patch.object(bot, "test_token", new_callable=AsyncMock) as mock_test_token:
            async def _fake(*a, **kw):
                bot._session_id = 2
                return {"success": False, "error": "Old token bad"}
            mock_test_token.side_effect = _fake

            # Simulate stale session 1 finishing its failed check
            await bot._polling_loop(session_id=1, stop_event=stop_event)

            # bot._running should NOT have been set to False by the old session 1!
            assert bot._running is True

    asyncio.run(_test())


def test_telegram_bot_singleton_lock():
    import concurrent.futures
    import modules.telegram_bot as tb_mod

    # Reset singleton
    tb_mod._global_telegram_bot = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: tb_mod.get_telegram_bot(), range(20)))

    # All instances should be identical
    assert len(set(id(inst) for inst in results)) == 1
    assert results[0] is tb_mod._global_telegram_bot
