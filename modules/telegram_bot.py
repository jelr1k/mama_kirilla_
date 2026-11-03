from __future__ import annotations

import asyncio
import datetime
import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from core.vpn_manager import get_vpn_manager
from modules.network_checker import get_network_checker
from tools.system_actions import lock_pc, take_screenshot
from tools.system_info import get_system_telemetry

logger = logging.getLogger("jarvis.telegram_bot")


class TelegramBotModule:
    """Lightweight asynchronous Telegram Bot module for remote PC monitoring and management."""

    def __init__(self, config_manager=None, app_context=None):
        self.config_manager = config_manager
        self.app_context = app_context
        self._running = False
        self._stop_event = asyncio.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._bot_username: str | None = None
        self._last_error: str | None = None

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

    async def test_token(self, token: str, base_url: str | None = None) -> dict[str, Any]:
        token = token.strip()
        if not token:
            return {"success": False, "error": "Токен не указан"}
        root = (base_url.strip().rstrip("/") if base_url and base_url.strip() else self.api_base_url)
        url = f"{root}/bot{token}/getMe"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                data = resp.json()
                if data.get("ok"):
                    res = data.get("result", {})
                    return {
                        "success": True,
                        "bot_id": res.get("id"),
                        "username": res.get("username"),
                        "first_name": res.get("first_name"),
                    }
                return {"success": False, "error": data.get("description", "Неверный ответ Telegram")}
        except Exception as exc:
            return {"success": False, "error": f"Ошибка соединения: {exc}"}

    def start(self) -> None:
        """Start Telegram bot poller thread if enabled and configured."""
        if self._running:
            return
        if not self.is_enabled or not self.bot_token:
            logger.info("telegram_bot_disabled_or_not_configured")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_thread, name="TelegramBotThread", daemon=True)
        self._thread.start()
        logger.info("telegram_bot_thread_started")

    def stop(self) -> None:
        """Stop Telegram bot polling cleanly."""
        if not self._running:
            return
        self._running = False
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("telegram_bot_stopped")

    def _run_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._polling_loop())
        finally:
            self._loop.close()

    async def _send_message(self, client: httpx.AsyncClient, chat_id: int, text: str, parse_mode: str = "HTML") -> None:
        url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        try:
            await client.post(url, json=payload, timeout=10.0)
        except Exception as exc:
            logger.error("telegram_send_message_failed chat_id=%s error=%s", chat_id, exc)

    async def _send_photo(self, client: httpx.AsyncClient, chat_id: int, photo_path: str, caption: str = "") -> None:
        url = f"{self.api_base_url}/bot{self.bot_token}/sendPhoto"
        file_path = Path(photo_path)
        if not file_path.is_file():
            await self._send_message(client, chat_id, "❌ Файл скриншота не найден на диске.")
            return

        try:
            with open(file_path, "rb") as f:
                files = {"photo": (file_path.name, f, "image/png")}
                data = {"chat_id": str(chat_id), "caption": caption}
                await client.post(url, data=data, files=files, timeout=20.0)
        except Exception as exc:
            logger.error("telegram_send_photo_failed chat_id=%s error=%s", chat_id, exc)
            await self._send_message(client, chat_id, f"❌ Ошибка отправки фото: {exc}")

    async def _handle_command_status(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            telemetry = get_system_telemetry()
            vpn_stat = get_vpn_manager().status(force=False)

            cpu = telemetry.get("cpu_percent", 0)
            ram = telemetry.get("ram", {})
            ram_pct = ram.get("percent", 0)
            ram_used = round(ram.get("used", 0) / (1024**3), 1)
            ram_total = round(ram.get("total", 0) / (1024**3), 1)

            gpus = telemetry.get("gpus", [])
            gpu_info = ""
            if gpus:
                g = gpus[0]
                gpu_name = g.get("name", "GPU")
                gpu_load = g.get("load_percent", 0)
                gpu_temp = g.get("temperature_c")
                temp_str = f", {gpu_temp}°C" if gpu_temp else ""
                gpu_info = f"\n🎮 <b>GPU:</b> {gpu_name} ({gpu_load}%{temp_str})"

            zapret = vpn_stat.get("zapret", {})
            zapret_str = "🟢 winws запущен" if zapret.get("running") else "⚪ выключен"

            clients = vpn_stat.get("clients", {})
            happ = clients.get("happ", {})
            happ_str = "🟢 подключен" if happ.get("vpn_running") else ("🟡 окно открыто" if happ.get("gui_running") else "⚪ выключен")

            flclash = clients.get("flclash", {})
            flclash_str = "🟢 подключен" if flclash.get("vpn_running") else ("🟡 окно открыто" if flclash.get("gui_running") else "⚪ выключен")

            msg = (
                f"💻 <b>Состояние ПК:</b>\n"
                f"⚙️ <b>CPU:</b> {cpu}%\n"
                f"🧠 <b>RAM:</b> {ram_used} / {ram_total} GB ({ram_pct}%){gpu_info}\n\n"
                f"🛡️ <b>Защита и обход блокировок:</b>\n"
                f"• Запрет: {zapret_str}\n"
                f"• Happ: {happ_str}\n"
                f"• FlClashX: {flclash_str}"
            )
            await self._send_message(client, chat_id, msg)
        except Exception as exc:
            logger.exception("telegram_status_command_failed: %s", exc)
            await self._send_message(client, chat_id, f"❌ Ошибка сбора статуса: {exc}")

    async def _handle_command_screen(self, client: httpx.AsyncClient, chat_id: int) -> None:
        await self._send_message(client, chat_id, "📸 Делаю снимок экрана...")
        try:
            res = take_screenshot()
            if res.get("success") and res.get("path"):
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                await self._send_photo(client, chat_id, res["path"], caption=f"🖥️ Рабочий стол — {now_str}")
            else:
                err = res.get("error", "Не удалось сделать скриншот")
                await self._send_message(client, chat_id, f"❌ Ошибка: {err}")
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Исключение при снятии скриншота: {exc}")

    async def _handle_command_vpn(self, client: httpx.AsyncClient, chat_id: int, arg: str) -> None:
        mgr = get_vpn_manager()
        arg = arg.strip().lower()

        if not arg or arg == "status":
            st = mgr.status(force=True)
            zapret = st.get("zapret", {})
            clients = st.get("clients", {})
            msg = (
                f"🌐 <b>Статус VPN и Запрета:</b>\n"
                f"• Запрет (service.bat): {'🟢 winws активен' if zapret.get('running') else '⚪ не запущен'}\n"
                f"• Happ: {'🟢 VPN работает' if clients.get('happ', {}).get('vpn_running') else '⚪ не активен'}\n"
                f"• FlClashX: {'🟢 VPN работает' if clients.get('flclash', {}).get('vpn_running') else '⚪ не активен'}\n\n"
                f"Команды управления:\n"
                f"<code>/vpn zapret</code> — запуск service.bat\n"
                f"<code>/vpn happ</code> — запуск и подключение Happ\n"
                f"<code>/vpn flclash</code> — запуск и подключение FlClashX"
            )
            await self._send_message(client, chat_id, msg)
            return

        if arg == "zapret":
            await self._send_message(client, chat_id, "🚀 Запускаю service.bat Запрета...")
            res = mgr.launch_zapret()
            status_text = "✅ Запущен" if res.get("success") else "❌ Ошибка"
            desc = res.get("message") or res.get("error") or ""
            await self._send_message(client, chat_id, f"{status_text}\n{desc}")
            return

        if arg in ("happ", "flclash"):
            label = "Happ" if arg == "happ" else "FlClashX"
            await self._send_message(client, chat_id, f"🚀 Запускаю и подключаю {label}...")
            res = mgr.connect(arg)
            status_text = "✅ Команда выполнена" if res.get("success") else "❌ Ошибка"
            desc = res.get("message") or res.get("error") or ""
            await self._send_message(client, chat_id, f"{status_text}\n{desc}")
            return

        await self._send_message(client, chat_id, "⚠️ Неизвестный клиент. Доступно: <code>zapret</code>, <code>happ</code>, <code>flclash</code>")

    async def _handle_command_ping(self, client: httpx.AsyncClient, chat_id: int) -> None:
        await self._send_message(client, chat_id, "📡 Проверяю доступность сервисов...")
        checker = get_network_checker()
        res = await checker.check_all(force=True)
        services = res.get("services", [])

        lines = ["🌐 <b>Доступность ключевых сервисов:</b>\n"]
        for s in services:
            st = s.get("status")
            name = s.get("name")
            ms = s.get("ping_ms")
            if st == "ok":
                dot = "🟢"
                info = f"{ms} мс"
            elif st == "slow":
                dot = "🟡"
                info = f"{ms} мс (задержка)"
            elif st == "blocked":
                dot = "🔴"
                info = "Блокировка / DPI"
            else:
                dot = "⚪"
                info = s.get("message") or "Недоступен"
            lines.append(f"{dot} <b>{name}:</b> {info}")

        summary = res.get("summary", {})
        lines.append(f"\nИтог: {summary.get('ok_count')}/{summary.get('total')} сервисов доступно.")
        await self._send_message(client, chat_id, "\n".join(lines))

    async def _handle_command_sleep(self, client: httpx.AsyncClient, chat_id: int) -> None:
        await self._send_message(client, chat_id, "💤 Перевожу компьютер в спящий режим...")
        await asyncio.sleep(1.0)
        try:
            # Safe Windows sleep command via powrprof
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=False)
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Ошибка перехода в сон: {exc}")

    async def _handle_command_shutdown(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            subprocess.run(["shutdown", "/s", "/t", "60"], check=False)
            await self._send_message(
                client,
                chat_id,
                "⚠️ <b>Внимание!</b> Компьютер будет выключен через <b>60 секунд</b>.\n"
                "Чтобы отменить выключение, отправьте: /shutdown_cancel"
            )
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Не удалось запланировать выключение: {exc}")

    async def _handle_command_shutdown_cancel(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            subprocess.run(["shutdown", "/a"], check=False)
            await self._send_message(client, chat_id, "✅ Выключение компьютера отменено.")
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Ошибка отмены: {exc}")

    async def _handle_command_lock(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            lock_pc()
            await self._send_message(client, chat_id, "🔒 Рабочий стол заблокирован.")
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Не удалось заблокировать: {exc}")

    async def _handle_text_query(self, client: httpx.AsyncClient, chat_id: int, text: str) -> None:
        # Pass plain text to assistant command router if available
        chat_service = getattr(self.app_context, "chat_service", None)
        router = getattr(chat_service, "router", None) if chat_service else None

        if router:
            try:
                direct = router.route(text)
                if direct:
                    await self._send_message(client, chat_id, f"🤖 {direct}")
                    return
            except Exception as exc:
                logger.debug("router_execution_failed: %s", exc)

        # Fallback or acknowledgment
        await self._send_message(
            client,
            chat_id,
            f"🤖 Команда «{text}» не распознана роутером быстрых действий.\n"
            f"Отправьте /help для списка команд управления ПК."
        )

    async def _process_update(self, client: httpx.AsyncClient, update: dict[str, Any]) -> None:
        message = update.get("message")
        if not message:
            return

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return

        text = (message.get("text") or "").strip()
        allowed = self.allowed_chat_ids

        # Access check
        if allowed and chat_id not in allowed:
            logger.warning("telegram_bot_unauthorized chat_id=%s text=%r", chat_id, text)
            await self._send_message(
                client,
                chat_id,
                f"⛔ <b>Доступ запрещен.</b>\nВаш Chat ID: <code>{chat_id}</code>\n"
                f"Добавьте этот ID в настройки Kirieshcka в секцию Telegram."
            )
            return

        if not allowed:
            logger.warning("telegram_bot_no_allowed_ids chat_id=%s", chat_id)
            await self._send_message(
                client,
                chat_id,
                f"⚠️ <b>Внимание:</b> бот активен, но список разрешённых Chat ID пуст.\n"
                f"Ваш Chat ID: <code>{chat_id}</code>\n"
                f"Добавьте его в настройки программы, чтобы включить защиту."
            )
            return

        # Process command
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        # Remove bot username suffix if present (/status@mybot -> /status)
        if "@" in cmd:
            cmd = cmd.split("@")[0]

        if cmd in ("/start", "/help"):
            help_text = (
                "🤖 <b>Kirieshcka v2 Remote Control</b>\n\n"
                "Команды управления компьютером:\n"
                "📊 /status — Состояние ПК (CPU, RAM, GPU, VPN)\n"
                "📸 /screen — Скриншот основного монитора\n"
                "📡 /ping — Проверка доступности Discord, YouTube, Steam и др.\n"
                "🛡️ /vpn — Статус и запуск Запрета / Happ / FlClashX\n"
                "🔒 /lock — Заблокировать рабочий стол\n"
                "💤 /sleep — Перевести ПК в спящий режим\n"
                "🔌 /shutdown — Выключить ПК (с таймером 60 сек)\n"
                "🚫 /shutdown_cancel — Отменить выключение\n\n"
                "Также можно отправлять текстовые команды ассистенту (громкость, запуск программ)."
            )
            await self._send_message(client, chat_id, help_text)
        elif cmd == "/status":
            await self._handle_command_status(client, chat_id)
        elif cmd == "/screen":
            await self._handle_command_screen(client, chat_id)
        elif cmd == "/vpn":
            await self._handle_command_vpn(client, chat_id, arg)
        elif cmd == "/ping":
            await self._handle_command_ping(client, chat_id)
        elif cmd == "/sleep":
            await self._handle_command_sleep(client, chat_id)
        elif cmd == "/shutdown":
            await self._handle_command_shutdown(client, chat_id)
        elif cmd == "/shutdown_cancel":
            await self._handle_command_shutdown_cancel(client, chat_id)
        elif cmd == "/lock":
            await self._handle_command_lock(client, chat_id)
        elif text:
            await self._handle_text_query(client, chat_id, text)

    async def _polling_loop(self) -> None:
        self._stop_event.clear()
        offset = 0

        # Validate token first and get bot info
        check = await self.test_token(self.bot_token)
        if not check.get("success"):
            self._last_error = check.get("error", "Неверный токен")
            logger.error("telegram_bot_init_failed error=%s", self._last_error)
            self._running = False
            return

        self._bot_username = check.get("username")
        self._last_error = None
        logger.info("telegram_bot_authorized username=@%s", self._bot_username)

        async with httpx.AsyncClient(timeout=35.0) as client:
            # Startup notification
            if self.notify_on_startup and self.allowed_chat_ids:
                for cid in self.allowed_chat_ids:
                    await self._send_message(
                        client,
                        cid,
                        f"🟢 <b>Kirieshcka v2 запущена на ПК</b>\nБот <code>@{self._bot_username}</code> готов к командам. Отправьте /status"
                    )

            while self._running and not self._stop_event.is_set():
                url = f"{self.api_base_url}/bot{self.bot_token}/getUpdates"
                params = {"offset": offset, "timeout": 20}
                try:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        updates = data.get("result", [])
                        for upd in updates:
                            offset = max(offset, upd.get("update_id", 0) + 1)
                            await self._process_update(client, upd)
                    elif resp.status_code == 409:
                        logger.warning("telegram_bot_conflict_another_instance_running")
                        await asyncio.sleep(5.0)
                    else:
                        logger.warning("telegram_bot_get_updates_status=%d", resp.status_code)
                        await asyncio.sleep(3.0)
                except httpx.TimeoutException:
                    continue
                except Exception as exc:
                    self._last_error = str(exc)
                    logger.debug("telegram_bot_poll_error: %s", exc)
                    await asyncio.sleep(3.0)


_global_telegram_bot: TelegramBotModule | None = None


def get_telegram_bot(config_manager=None, app_context=None) -> TelegramBotModule:
    global _global_telegram_bot
    if _global_telegram_bot is None:
        _global_telegram_bot = TelegramBotModule(config_manager=config_manager, app_context=app_context)
    else:
        if config_manager and not _global_telegram_bot.config_manager:
            _global_telegram_bot.config_manager = config_manager
        if app_context and not _global_telegram_bot.app_context:
            _global_telegram_bot.app_context = app_context
    return _global_telegram_bot
