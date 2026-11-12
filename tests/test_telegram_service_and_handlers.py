from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from modules.telegram.service import TelegramBotService


def _make_service(tg_cfg: dict | None = None, app_context=None) -> TelegramBotService:
    cfg = MagicMock()
    data = tg_cfg if tg_cfg is not None else {
        "enabled": True,
        "bot_token": "123:token",
        "allowed_chat_ids": [1001, "1002", "bad_id"],
        "notify_on_startup": True,
        "api_base_url": "https://tg.proxy.local/",
    }
    cfg.get = lambda key, default=None: data if key == "telegram" else default
    return TelegramBotService(config_manager=cfg, app_context=app_context)


def test_telegram_service_config_and_status():
    svc = _make_service()
    assert svc.is_enabled is True
    assert svc.bot_token == "123:token"
    assert svc.allowed_chat_ids == {1001, 1002}
    assert svc.notify_on_startup is True
    assert svc.api_base_url == "https://tg.proxy.local"

    status = svc.get_status()
    assert status == {
        "enabled": True,
        "running": False,
        "configured": True,
        "bot_username": None,
        "allowed_chat_count": 2,
        "api_base_url": "https://tg.proxy.local",
        "last_error": None,
    }


def test_telegram_service_start_skips_when_disabled_or_unconfigured():
    disabled = _make_service({"enabled": False, "bot_token": "123:token"})
    disabled.start()
    assert disabled._running is False
    assert disabled._thread is None

    no_token = _make_service({"enabled": True, "bot_token": "   "})
    no_token.start()
    assert no_token._running is False


def test_telegram_access_control_blocks_unauthorized_empty_allowlist_and_bots():
    async def _run():
        client = AsyncMock()

        # 1. Unauthorized sender
        svc = _make_service()
        svc._send_message = AsyncMock()
        await svc._process_update(client, {
            "message": {"chat": {"id": 9999}, "from": {"id": 9999, "is_bot": False}, "text": "/status"}
        })
        assert "Доступ запрещен" in svc._send_message.call_args[0][2]

        # 2. Empty allowed_chat_ids blocks execution with warning
        svc_empty = _make_service({"enabled": True, "bot_token": "t", "allowed_chat_ids": []})
        svc_empty._send_message = AsyncMock()
        await svc_empty._process_update(client, {
            "message": {"chat": {"id": 1001}, "from": {"id": 1001, "is_bot": False}, "text": "/status"}
        })
        assert "список разрешённых Chat ID пуст" in svc_empty._send_message.call_args[0][2]

        # 3. Bot messages are ignored completely
        svc._send_message.reset_mock()
        await svc._process_update(client, {
            "message": {"chat": {"id": 1001}, "from": {"id": 555, "is_bot": True}, "text": "/status"}
        })
        svc._send_message.assert_not_awaited()

    asyncio.run(_run())


def test_telegram_commands_and_callbacks_dispatch():
    async def _run():
        svc = _make_service()
        svc._send_message = AsyncMock()
        svc._send_photo = AsyncMock()
        svc._answer_callback_query = AsyncMock()
        client = AsyncMock()

        # /start
        await svc._process_update(client, {
            "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/start@mybot"}
        })
        assert "Kirieshcka v2 Remote Control" in svc._send_message.call_args[0][2]

        # /status
        with (
            patch("modules.telegram.handlers.get_system_telemetry", return_value={
                "cpu_percent": 15,
                "ram": {"percent": 40, "used": 6 * 1024**3, "total": 16 * 1024**3},
                "gpus": [{"name": "RX 6500 XT", "load_percent": 10, "temperature_c": 45}],
            }),
            patch("modules.telegram.handlers.get_vpn_manager") as mock_vpn,
        ):
            mock_vpn.return_value.status.return_value = {
                "zapret": {"running": True},
                "clients": {"happ": {"vpn_running": True}, "flclash": {"gui_running": True}},
            }
            await svc._process_update(client, {
                "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/status"}
            })
            msg = svc._send_message.call_args[0][2]
            assert "15%" in msg
            assert "RX 6500 XT" in msg
            assert "winws запущен" in msg

        # /screen
        with patch("modules.telegram.handlers.take_screenshot", return_value={"success": True, "path": "shot.png"}):
            await svc._process_update(client, {
                "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/screen"}
            })
            svc._send_photo.assert_awaited_once()

        # /shutdown invalid arg and valid shutdown + cancel
        with patch("modules.telegram.handlers.subprocess.run") as mock_run:
            await svc._process_update(client, {
                "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/shutdown abc"}
            })
            assert "Некорректный аргумент" in svc._send_message.call_args[0][2]
            mock_run.assert_not_called()

            await svc._process_update(client, {
                "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/shutdown 5"}
            })
            mock_run.assert_called_with(["shutdown", "/s", "/t", "300"], check=False)

            await svc._process_update(client, {
                "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/shutdown_cancel"}
            })
            mock_run.assert_called_with(["shutdown", "/a"], check=False)

        # Callback query shutdown:reboot and unauthorized callback
        with patch("modules.telegram.handlers.subprocess.run") as mock_run:
            await svc._process_update(client, {
                "callback_query": {
                    "id": "cb1",
                    "data": "shutdown:reboot",
                    "from": {"id": 1002},
                    "message": {"chat": {"id": 1002}},
                }
            })
            svc._answer_callback_query.assert_awaited_with(client, "cb1")
            mock_run.assert_called_with(["shutdown", "/r", "/t", "60"], check=False)

            svc._answer_callback_query.reset_mock()
            await svc._process_update(client, {
                "callback_query": {
                    "id": "cb2",
                    "data": "shutdown:0",
                    "from": {"id": 7777},
                    "message": {"chat": {"id": 7777}},
                }
            })
            svc._answer_callback_query.assert_awaited_with(client, "cb2", text="⛔ Доступ запрещен", alert=True)

        # /ping
        fake_checker = Mock()
        fake_checker.check_all = AsyncMock(return_value={
            "services": [{"name": "Discord", "status": "ok", "ping_ms": 22}],
            "summary": {"ok_count": 1, "total": 1},
        })
        with patch("modules.telegram.handlers.get_network_checker", return_value=fake_checker):
            await svc._process_update(client, {
                "message": {"chat": {"id": 1001}, "from": {"id": 1001}, "text": "/ping"}
            })
            assert "Discord" in svc._send_message.call_args[0][2]

    asyncio.run(_run())
