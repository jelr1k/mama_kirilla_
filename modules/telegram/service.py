from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

import httpx

from modules.telegram.client import TelegramClientMixin
from modules.telegram.handlers import TelegramCommandHandlerMixin
from modules.telegram.keyboards import (
    get_cancel_shutdown_keyboard,
    get_main_keyboard,
    get_shutdown_keyboard,
    get_vpn_keyboard,
)

logger = logging.getLogger("jarvis.telegram_bot")


class TelegramBotService(TelegramClientMixin, TelegramCommandHandlerMixin):
    """Lightweight asynchronous Telegram Bot service for remote PC monitoring and management."""

    # Re-export keyboard helpers as static methods for backwards compatibility
    get_main_keyboard = staticmethod(get_main_keyboard)
    get_vpn_keyboard = staticmethod(get_vpn_keyboard)
    get_shutdown_keyboard = staticmethod(get_shutdown_keyboard)
    get_cancel_shutdown_keyboard = staticmethod(get_cancel_shutdown_keyboard)

    def __init__(self, config_manager=None, app_context=None):
        self.config_manager = config_manager
        self.app_context = app_context
        self._running = False
        self._session_id: int = 0
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None
        self._bot_username: str | None = None
        self._last_error: str | None = None
        self._lock = threading.Lock()
        self._cancel_task = None

    def _is_session_active(self, session_id: int, stop_event: threading.Event) -> bool:
        return self._running and self._session_id == session_id and not stop_event.is_set()

    def _get_config(self) -> dict[str, Any]:
        if self.config_manager and hasattr(self.config_manager, "get"):
            return self.config_manager.get("telegram", {})
        return {}

    @property
    def is_enabled(self) -> bool:
        return bool(self._get_config().get("enabled", False))

    @property
    def bot_token(self) -> str:
        return str(self._get_config().get("bot_token", "")).strip()

    @property
    def allowed_chat_ids(self) -> set[int]:
        raw_ids = self._get_config().get("allowed_chat_ids", [])
        parsed = set()
        for item in raw_ids:
            try:
                parsed.add(int(item))
            except (ValueError, TypeError):
                continue
        return parsed

    @property
    def notify_on_startup(self) -> bool:
        return bool(self._get_config().get("notify_on_startup", False))

    @property
    def api_base_url(self) -> str:
        base = (self._get_config().get("api_base_url") or "").strip()
        if not base:
            base = "https://api.telegram.org"
        return base.rstrip("/")

    def get_status(self) -> dict[str, Any]:
        return {
            "enabled": self.is_enabled,
            "running": self._running,
            "configured": bool(self.bot_token),
            "bot_username": self._bot_username,
            "allowed_chat_count": len(self.allowed_chat_ids),
            "api_base_url": self.api_base_url,
            "last_error": self._last_error,
        }

    def start(self) -> None:
        """Start Telegram bot poller thread if enabled and configured."""
        thread_to_join = None
        with self._lock:
            if self._running:
                return
            if self._thread and self._thread.is_alive():
                thread_to_join = self._thread

        if thread_to_join:
            thread_to_join.join(timeout=5.0)

        with self._lock:
            if self._running:
                return
            if self._thread and self._thread.is_alive():
                logger.warning("telegram_bot_cannot_start_old_thread_still_alive")
                return
            if not self.is_enabled or not self.bot_token:
                logger.info("telegram_bot_disabled_or_not_configured")
                return

            self._session_id += 1
            current_session = self._session_id
            self._running = True
            self._stop_event = threading.Event()
            self._thread = threading.Thread(
                target=self._run_thread,
                args=(current_session, self._stop_event),
                name=f"TelegramBotThread-{current_session}",
                daemon=True,
            )
            self._thread.start()
            logger.info("telegram_bot_thread_started session=%d", current_session)

    def stop(self) -> None:
        """Stop Telegram bot polling cleanly."""
        thread_to_join = None
        with self._lock:
            if not self._running and (not self._thread or not self._thread.is_alive()):
                return
            self._running = False
            self._session_id += 1
            if self._stop_event:
                self._stop_event.set()
            if self._cancel_task:
                try:
                    self._cancel_task()
                except Exception as exc:
                    logger.debug("telegram_bot_cancel_task_failed: %s", exc)
                self._cancel_task = None
            if self._thread and self._thread.is_alive():
                thread_to_join = self._thread

        if thread_to_join:
            thread_to_join.join(timeout=5.0)
        logger.info("telegram_bot_stopped")

    def _run_thread(self, session_id: int, stop_event: threading.Event) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self._polling_loop(session_id, stop_event))

        def _cancel():
            if not task.done():
                loop.call_soon_threadsafe(task.cancel)

        with self._lock:
            if self._session_id == session_id and not stop_event.is_set():
                self._cancel_task = _cancel

        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
        finally:
            with self._lock:
                if self._session_id == session_id:
                    self._running = False
                if self._cancel_task == _cancel:
                    self._cancel_task = None
            try:
                pending = asyncio.all_tasks(loop)
                for t in pending:
                    t.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            try:
                loop.run_until_complete(loop.shutdown_default_executor())
            except Exception:
                pass
            loop.close()

    async def _polling_loop(self, session_id: int, stop_event: threading.Event) -> None:
        offset = 0

        if not self._is_session_active(session_id, stop_event):
            return

        # Validate token first and get bot info
        check = await self.test_token(self.bot_token)
        if not check.get("success"):
            if self._session_id == session_id and not stop_event.is_set():
                self._last_error = check.get("error", "Неверный токен")
                logger.error("telegram_bot_init_failed error=%s", self._last_error)
                self._running = False
            return

        if not self._is_session_active(session_id, stop_event):
            return

        self._bot_username = check.get("username")
        self._last_error = None
        logger.info("telegram_bot_authorized username=@%s session=%s", self._bot_username, session_id)

        async with httpx.AsyncClient(timeout=35.0) as client:
            if not self._is_session_active(session_id, stop_event):
                return

            # Drop stale pending updates accumulated while bot/PC was offline
            try:
                await client.post(
                    f"{self.api_base_url}/bot{self.bot_token}/deleteWebhook",
                    json={"drop_pending_updates": True},
                    timeout=10.0,
                )
                logger.info("telegram_stale_updates_dropped")
            except Exception as exc:
                logger.warning("telegram_drop_pending_updates_failed: %s", exc)

            if not self._is_session_active(session_id, stop_event):
                return

            # Probe latest update to ensure offset starts ahead
            try:
                probe = await client.get(
                    f"{self.api_base_url}/bot{self.bot_token}/getUpdates",
                    params={"offset": -1, "limit": 1},
                    timeout=10.0,
                )
                if probe.status_code == 200:
                    res = probe.json().get("result", [])
                    if res:
                        offset = res[-1].get("update_id", 0) + 1
            except Exception:
                pass

            if not self._is_session_active(session_id, stop_event):
                return

            # Startup notification
            if self.notify_on_startup and self.allowed_chat_ids:
                for cid in self.allowed_chat_ids:
                    if not self._is_session_active(session_id, stop_event):
                        return
                    await self._send_message(
                        client,
                        cid,
                        f"🟢 <b>Kirieshcka v2 запущена на ПК</b>\nБот <code>@{self._bot_username}</code> готов к командам. Отправьте /status"
                    )

            while self._is_session_active(session_id, stop_event):
                url = f"{self.api_base_url}/bot{self.bot_token}/getUpdates"
                params = {"offset": offset, "timeout": 20}
                try:
                    resp = await client.get(url, params=params)
                    if not self._is_session_active(session_id, stop_event):
                        break

                    if resp.status_code == 200:
                        data = resp.json()
                        updates = data.get("result", [])
                        for upd in updates:
                            if not self._is_session_active(session_id, stop_event):
                                break
                            offset = max(offset, upd.get("update_id", 0) + 1)
                            await self._process_update(client, upd)
                    elif resp.status_code == 409:
                        logger.warning("telegram_bot_conflict_another_instance_running")
                        await asyncio.sleep(5.0)
                    elif resp.status_code in (401, 403):
                        if self._session_id == session_id and not stop_event.is_set():
                            self._last_error = f"Ошибка авторизации Telegram (HTTP {resp.status_code}): неверный или отозванный токен"
                            logger.error("telegram_bot_unauthorized status=%d", resp.status_code)
                            self._running = False
                        break
                    else:
                        logger.warning("telegram_bot_get_updates_status=%d", resp.status_code)
                        await asyncio.sleep(3.0)
                except httpx.TimeoutException:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    if not self._is_session_active(session_id, stop_event):
                        break
                    self._last_error = str(exc)
                    logger.debug("telegram_bot_poll_error: %s", exc)
                    await asyncio.sleep(3.0)
