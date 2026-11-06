from __future__ import annotations

import asyncio
import datetime
import logging
import re
import subprocess
import threading
from typing import Any

import httpx

from core.vpn_manager import get_vpn_manager
from llm.request import ChatRequest
from modules.network_checker import get_network_checker
from modules.telegram.keyboards import (
    get_cancel_shutdown_keyboard,
    get_main_keyboard,
    get_shutdown_keyboard,
    get_vpn_keyboard,
)
from tools.system_actions import lock_pc, take_screenshot
from tools.system_info import get_system_telemetry

logger = logging.getLogger("jarvis.telegram_bot")
_router_route_lock = threading.Lock()


class TelegramCommandHandlerMixin:
    """Command dispatching and update processing logic for Telegram bot."""

    async def _handle_command_status(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            telemetry = await asyncio.to_thread(get_system_telemetry)
            vpn_stat = await asyncio.to_thread(get_vpn_manager().status, force=False)

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
            res = await asyncio.to_thread(take_screenshot)
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
            st = await asyncio.to_thread(mgr.status, force=True)
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
            await self._send_message(client, chat_id, msg, reply_markup=self.get_vpn_keyboard())
            return

        if arg == "zapret":
            await self._send_message(client, chat_id, "🚀 Запускаю service.bat Запрета...")
            res = await asyncio.to_thread(mgr.launch_zapret)
            status_text = "✅ Запущен" if res.get("success") else "❌ Ошибка"
            desc = res.get("message") or res.get("error") or ""
            await self._send_message(client, chat_id, f"{status_text}\n{desc}")
            return

        if arg in ("happ", "flclash"):
            label = "Happ" if arg == "happ" else "FlClashX"
            await self._send_message(client, chat_id, f"🚀 Запускаю и подключаю {label}...")
            res = await asyncio.to_thread(mgr.connect, arg)
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
            await asyncio.to_thread(
                subprocess.Popen,
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                shell=False,
            )
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Ошибка перехода в сон: {exc}")

    async def _handle_command_shutdown(self, client: httpx.AsyncClient, chat_id: int, arg: str = "") -> None:
        arg = arg.strip()
        seconds = 60
        display_time = "60 секунд"
        if arg:
            try:
                val = int(arg)
                if val <= 0:
                    seconds = 0
                    display_time = "прямо сейчас"
                else:
                    seconds = val * 60
                    display_time = f"{val} мин ({seconds} сек)"
            except ValueError:
                await self._send_message(
                    client,
                    chat_id,
                    f"⚠️ Некорректный аргумент времени: «{arg}». Укажите количество минут (например, <code>/shutdown 10</code>) или 0 для немедленного выключения."
                )
                return

        try:
            await asyncio.to_thread(
                subprocess.run,
                ["shutdown", "/s", "/t", str(seconds)],
                check=False,
            )
            if seconds == 0:
                await self._send_message(client, chat_id, "⚠️ <b>Компьютер выключается прямо сейчас...</b>")
            else:
                await self._send_message(
                    client,
                    chat_id,
                    f"⚠️ <b>Внимание!</b> Компьютер будет выключен через <b>{display_time}</b>.\n"
                    f"Чтобы отменить выключение, нажмите кнопку ниже или отправьте: /shutdown_cancel",
                    reply_markup=self.get_cancel_shutdown_keyboard(),
                )
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Не удалось запланировать выключение: {exc}")

    async def _handle_command_shutdown_cancel(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            await asyncio.to_thread(subprocess.run, ["shutdown", "/a"], check=False)
            await self._send_message(client, chat_id, "✅ Выключение или перезагрузка компьютера отменена.")
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Ошибка отмены: {exc}")

    async def _handle_command_reboot(self, client: httpx.AsyncClient, chat_id: int, arg: str = "") -> None:
        arg = arg.strip()
        seconds = 60
        display_time = "60 секунд"
        if arg:
            try:
                val = int(arg)
                if val <= 0:
                    seconds = 0
                    display_time = "прямо сейчас"
                else:
                    seconds = val * 60
                    display_time = f"{val} мин ({seconds} сек)"
            except ValueError:
                await self._send_message(
                    client,
                    chat_id,
                    f"⚠️ Некорректный аргумент времени: «{arg}». Укажите количество минут (например, <code>/reboot 5</code>) или 0 для немедленной перезагрузки."
                )
                return

        try:
            await asyncio.to_thread(
                subprocess.run,
                ["shutdown", "/r", "/t", str(seconds)],
                check=False,
            )
            if seconds == 0:
                await self._send_message(client, chat_id, "🔄 <b>Компьютер перезагружается прямо сейчас...</b>")
            else:
                await self._send_message(
                    client,
                    chat_id,
                    f"🔄 <b>Внимание!</b> Перезагрузка компьютера через <b>{display_time}</b>.\n"
                    f"Чтобы отменить перезагрузку, нажмите кнопку ниже или отправьте: /shutdown_cancel",
                    reply_markup=self.get_cancel_shutdown_keyboard(),
                )
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Не удалось запланировать перезагрузку: {exc}")

    async def _handle_command_lock(self, client: httpx.AsyncClient, chat_id: int) -> None:
        try:
            await asyncio.to_thread(lock_pc)
            await self._send_message(client, chat_id, "🔒 Рабочий стол заблокирован.")
        except Exception as exc:
            await self._send_message(client, chat_id, f"❌ Не удалось заблокировать: {exc}")

    async def _handle_text_query(self, client: httpx.AsyncClient, chat_id: int, text: str) -> None:
        query_text = text.lstrip("/").strip() if text.startswith("/") else text.strip()

        # Reject choice selectors (e.g. "1", "2", "первый") from Telegram to avoid consuming
        # stateful pending launch choices initiated in the UI/voice session.
        choice_pattern = r"(?:\d+|перв(?:ый|ая)|втор(?:ой|ая)|трет(?:ий|ья)|четверт(?:ый|ая)|четвёрт(?:ый|ая)|пят(?:ый|ая))\.?"
        if re.fullmatch(choice_pattern, query_text.casefold()):
            await self._send_message(
                client,
                chat_id,
                "🤖 Выбор варианта по номеру поддерживается только в локальном интерфейсе.",
                parse_mode=None,
            )
            return

        # Pass plain text to assistant command router if available
        chat_service = getattr(self.app_context, "chat_service", None)
        router = getattr(chat_service, "router", None) if chat_service else None

        if router:
            try:
                def _safe_route(t: str) -> str | None:
                    from tools import applications
                    with _router_route_lock:
                        saved_pending = list(getattr(applications, "_PENDING_LAUNCH_CHOICES", []))
                        try:
                            if hasattr(applications, "_PENDING_LAUNCH_CHOICES"):
                                applications._PENDING_LAUNCH_CHOICES = []
                            return router.route(t)
                        finally:
                            if hasattr(applications, "_PENDING_LAUNCH_CHOICES"):
                                applications._PENDING_LAUNCH_CHOICES = saved_pending

                direct = await asyncio.to_thread(_safe_route, text)
                if not direct and query_text != text:
                    direct = await asyncio.to_thread(_safe_route, query_text)

                if direct:
                    if chat_service and hasattr(chat_service, "conversation"):
                        try:
                            chat_service.conversation.add("user", f"[Telegram] {text}")
                            chat_service.conversation.add("assistant", direct)
                        except Exception:
                            pass
                    # Return command router result to Telegram exactly as would be shown in chat
                    await self._send_message(client, chat_id, f"🤖 {direct}", parse_mode=None)
                    return
            except Exception as exc:
                logger.error("router_execution_failed text=%r error=%s", text, exc)
                await self._send_message(client, chat_id, f"❌ Ошибка выполнения команды: {exc}", parse_mode=None)
                return

        # 2. Fallback to LLM if available and not in router_only_mode
        if chat_service and getattr(chat_service, "provider", None):
            cfg = getattr(chat_service, "config", {}) or {}
            if not cfg.get("router_only_mode", False):
                await self._send_chat_action(client, chat_id, action="typing")
                try:
                    def _generate_llm_response() -> str:
                        if getattr(chat_service, "ollama_manager", None) and not chat_service.ollama_manager.is_running():
                            chat_service.ollama_manager.start()

                        system_prompt = ""
                        if hasattr(chat_service, "_build_system_prompt"):
                            system_prompt = chat_service._build_system_prompt()

                        messages = []
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": text})

                        model_name = cfg.get("model") or "qwen3:1.7b"
                        req = ChatRequest(
                            model=model_name,
                            messages=messages,
                            temperature=float(cfg.get("temperature", 0.7)),
                            max_tokens=int(cfg.get("max_tokens", 1024)),
                        )
                        reply = ""
                        for item in chat_service.provider.stream_chat(req):
                            if item.text:
                                reply += item.text
                        return reply.strip()

                    llm_answer = await asyncio.to_thread(_generate_llm_response)
                    if llm_answer:
                        if hasattr(chat_service, "conversation"):
                            try:
                                chat_service.conversation.add("user", f"[Telegram] {text}")
                                chat_service.conversation.add("assistant", llm_answer)
                            except Exception:
                                pass
                        await self._send_message(client, chat_id, f"🤖 {llm_answer}", parse_mode=None)
                        return
                except Exception as exc:
                    logger.warning("telegram_llm_generation_failed: %s", exc)

        # 3. Fallback or acknowledgment
        await self._send_message(
            client,
            chat_id,
            f"🤖 Команда «{text}» не распознана роутером быстрых действий.\n"
            f"Языковая модель сейчас недоступна или выключена. Отправьте /help для списка доступных команд.",
            parse_mode=None,
            reply_markup=self.get_main_keyboard(),
        )

    async def _process_callback_query(self, client: httpx.AsyncClient, cq: dict[str, Any]) -> None:
        cq_id = str(cq.get("id") or "")
        from_user = cq.get("from", {})
        sender_id = from_user.get("id")
        msg = cq.get("message", {})
        chat_id = msg.get("chat", {}).get("id") or sender_id
        data = str(cq.get("data") or "").strip()

        allowed = self.allowed_chat_ids
        if not allowed or (sender_id not in allowed and chat_id not in allowed):
            await self._answer_callback_query(client, cq_id, text="⛔ Доступ запрещен", alert=True)
            return

        if not chat_id:
            return

        await self._answer_callback_query(client, cq_id)

        if data.startswith("vpn:"):
            sub = data.split(":", 1)[1]
            await self._handle_command_vpn(client, chat_id, sub)
        elif data == "shutdown:cancel":
            await self._handle_command_shutdown_cancel(client, chat_id)
        elif data == "shutdown:reboot":
            await self._handle_command_reboot(client, chat_id, "1")
        elif data.startswith("shutdown:"):
            sub = data.split(":", 1)[1]
            await self._handle_command_shutdown(client, chat_id, sub)

    async def _process_update(self, client: httpx.AsyncClient, update: dict[str, Any]) -> None:
        callback_query = update.get("callback_query")
        if callback_query:
            await self._process_callback_query(client, callback_query)
            return

        message = update.get("message")
        if not message:
            return

        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return

        from_user = message.get("from", {})
        if from_user.get("is_bot"):
            logger.debug("telegram_bot_ignoring_bot_message from_id=%s", from_user.get("id"))
            return

        from_id = from_user.get("id")
        sender_id = from_id or chat_id

        text = (message.get("text") or "").strip()
        allowed = self.allowed_chat_ids

        # Access check: verify sender or chat id is authorized
        if allowed and (sender_id not in allowed and chat_id not in allowed):
            logger.warning("telegram_bot_unauthorized chat_id=%s from_id=%s text=%r", chat_id, from_id, text)
            await self._send_message(
                client,
                chat_id,
                f"⛔ <b>Доступ запрещен.</b>\nВаш ID: <code>{sender_id}</code> (Chat ID: <code>{chat_id}</code>)\n"
                f"Добавьте этот ID в настройки Kirieshcka в секцию Telegram."
            )
            return

        if not allowed:
            logger.warning("telegram_bot_no_allowed_ids chat_id=%s from_id=%s", chat_id, from_id)
            await self._send_message(
                client,
                chat_id,
                f"⚠️ <b>Внимание:</b> бот активен, но список разрешённых Chat ID пуст.\n"
                f"Ваш ID: <code>{sender_id}</code> (Chat ID: <code>{chat_id}</code>)\n"
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

        # Map reply keyboard quick buttons to internal commands
        button_map = {
            "📊 статус пк": ("/status", ""),
            "📸 скриншот": ("/screen", ""),
            "📡 сеть / пинг": ("/ping", ""),
            "🛡️ vpn / запрет": ("/vpn", ""),
            "🔒 блокировка": ("/lock", ""),
            "💤 сон": ("/sleep", ""),
            "🔌 выключение": ("/shutdown_menu", ""),
        }
        text_lower = text.casefold()
        if text_lower in button_map:
            cmd, arg = button_map[text_lower]

        if cmd in ("/start", "/help"):
            help_text = (
                "🤖 <b>Kirieshcka v2 Remote Control</b>\n\n"
                "Быстрые кнопки внизу экрана доступны всегда.\n\n"
                "Команды управления компьютером:\n"
                "📊 /status — Состояние ПК (CPU, RAM, GPU, VPN)\n"
                "📸 /screen — Скриншот основного монитора\n"
                "📡 /ping — Проверка доступности Discord, YouTube, Steam и др.\n"
                "🛡️ /vpn — Меню и статус Запрета / Happ / FlClashX\n"
                "🔒 /lock — Заблокировать рабочий стол\n"
                "💤 /sleep — Перевести ПК в спящий режим\n"
                "🔌 /shutdown [мин] — Выключить ПК (по умолчанию 60 сек)\n"
                "🔄 /reboot [мин] — Перезагрузить ПК\n"
                "🚫 /shutdown_cancel — Отменить выключение или перезагрузку\n\n"
                "Также можно писать ассистенту обычным текстом (вопросы, запуск программ, алиасы)."
            )
            await self._send_message(client, chat_id, help_text, reply_markup=self.get_main_keyboard())
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
        elif cmd == "/shutdown_menu":
            await self._send_message(
                client,
                chat_id,
                "🔌 <b>Управление питанием ПК:</b>\nВыберите вариант или введите <code>/shutdown 10</code> вручную:",
                reply_markup=self.get_shutdown_keyboard(),
            )
        elif cmd == "/shutdown":
            if not arg:
                await self._send_message(
                    client,
                    chat_id,
                    "🔌 <b>Управление питанием ПК:</b>\nВыберите таймер или введите время в минутах (например, <code>/shutdown 15</code>):",
                    reply_markup=self.get_shutdown_keyboard(),
                )
            else:
                await self._handle_command_shutdown(client, chat_id, arg)
        elif cmd == "/reboot":
            await self._handle_command_reboot(client, chat_id, arg)
        elif cmd == "/shutdown_cancel":
            await self._handle_command_shutdown_cancel(client, chat_id)
        elif cmd == "/lock":
            await self._handle_command_lock(client, chat_id)
        elif text:
            await self._handle_text_query(client, chat_id, text)
