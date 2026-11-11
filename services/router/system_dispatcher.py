from __future__ import annotations

import logging
from typing import Callable, Any

from services.command_catalog import match_command_definition, command_definition_display
from tools.executor import ToolExecutor

logger = logging.getLogger("jarvis.router.system")


def dispatch_system_command(
    text: str,
    executor: ToolExecutor,
    reply_fn: Callable[[dict], str],
    ui_actions: dict[str, Callable] | None,
) -> str | None:
    """Обрабатывает системные команды: мышь, VPN, Запрет, очистка чата, скриншот, блокировка, дата/время, папки, корзина."""
    actions = ui_actions or {}

    # Настройки мыши (ZET Gaming Fury)
    if match_command_definition("apply_mouse_settings", text):
        return reply_fn(executor.execute("apply_mouse_settings", {}))

    # VPN-клиенты и Запрет Discord/YouTube
    if match_command_definition("zapret_start", text) or match_command_definition("vpn_connect", text) or match_command_definition("vpn_status", text):
        from core.vpn_manager import get_vpn_manager

        manager = get_vpn_manager()
        if match_command_definition("zapret_start", text):
            return manager.launch_zapret().get("message") or "Запускаю Запрет."
        if match_command_definition("vpn_status", text):
            status = manager.status()
            lines = [status.get("zapret", {}).get("message", "")]
            for client_status in (status.get("clients") or {}).values():
                lines.append(client_status.get("message", ""))
            return "\n".join(line for line in lines if line)
        match = match_command_definition("vpn_connect", text)
        client = match.group(1) if match and match.groups() else None
        return manager.connect(client).get("message") or "Запускаю VPN."

    # Очистить чат
    if match_command_definition("clear_chat", text):
        if actions and "clear_chat" in actions:
            try:
                actions["clear_chat"]()
            except Exception as exc:
                logger.warning("clear_chat action failed: %s", exc)
            return "История чата очищена."
        return "Чат очищен."

    # Скриншот
    if match_command_definition("take_screenshot", text):
        return reply_fn(executor.execute("take_screenshot", {}))

    # Блокировка экрана
    if match_command_definition("lock_pc", text):
        return reply_fn(executor.execute("lock_pc", {}))

    # Калькулятор Фибоначчи в окне PowerShell
    if match_command_definition("fibonacci_calculator", text):
        return reply_fn(executor.execute("fibonacci_calculator", {}))

    # Текущее время и дата
    if match_command_definition("date_time", text):
        return reply_fn(executor.execute("get_current_time_date", {}))

    # Системные папки
    match = match_command_definition("open_system_folder", text)
    if match:
        folder = match.group(1).strip()
        return reply_fn(executor.execute("open_system_folder", {"folder_name": folder}))

    # Очистка корзины
    match = match_command_definition("empty_recycle_bin", text)
    if match:
        return reply_fn(executor.execute("empty_recycle_bin", {}))

    return None


def _build_assistant_aliases(assistant_name: str) -> set[str]:
    aliases = {"джарвис", "джарвиса", "jarvis", "кириешка", "кириешку", "кириэшка", "кириэшку"}
    name = str(assistant_name).strip().casefold()
    if name:
        aliases.add(name)
        if name.endswith("а"):
            aliases.add(name[:-1] + "у")
    return aliases


def dispatch_jarvis_window_command(
    text: str,
    ui_actions: dict[str, Callable] | None,
    assistant_name: str = "Kirieshcka",
) -> str | None:
    """Обрабатывает команды управления окном и завершения Jarvis."""
    lower = " ".join(text.lower().split())
    actions = ui_actions or {}
    aliases = _build_assistant_aliases(assistant_name)

    shutdown_commands = {
        "закрой себя",
        "закрой приложение",
        "выключись",
        "закройся",
        "заверши работу",
    }
    for alias in aliases:
        shutdown_commands.add(f"закрой {alias}")
        shutdown_commands.add(f"выключи {alias}")

    if lower in shutdown_commands:
        action = actions.get("shutdown")
        if action:
            action()
        return "Полностью закрываю приложение."

    parts = lower.split(maxsplit=1)
    verb = parts[0] if len(parts) == 2 else ""
    obj = parts[1] if len(parts) == 2 else ""

    if match_command_definition("jarvis_minimize", lower) or (
        verb in {"сверни", "свернуть", "скрой", "скрыть", "спрячь", "спрятать", "убери", "убрать"}
        and obj in aliases
    ):
        if any(tok in lower for tok in ("трей", "скрой", "скрыть", "спрячь", "спрятать", "убери", "убрать")):
            action = actions.get("hide") or actions.get("minimize")
        else:
            action = actions.get("minimize")
        if action:
            action()
        return "Сворачиваю окно."

    if match_command_definition("jarvis_maximize", lower) or (
        verb in {"разверни", "развернуть", "покажи", "показать", "открой", "открыть"}
        and obj in aliases
    ):
        action = actions.get("maximize")
        if action:
            action()
        return "Разворачиваю окно."

    if match_command_definition("jarvis_restore", lower) or (
        verb in {"восстанови", "восстановить", "верни", "вернуть"}
        and obj in aliases
    ):
        action = actions.get("restore")
        if action:
            action()
        return "Восстанавливаю обычный размер окна."

    return None
