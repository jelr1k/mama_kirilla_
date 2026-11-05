from __future__ import annotations

import re
from typing import Callable, Any

from services.command_catalog import match_command_definition, command_definition_display, GENERIC_APPLICATION_TARGETS
from tools.executor import ToolExecutor


def dispatch_file_command(
    text: str,
    executor: ToolExecutor,
    direct_tool_fn: Callable,
    confirmation_callback=None,
) -> str | None:
    """Обрабатывает явные файловые команды создания, записи, копирования, перемещения и информации."""
    # Создание файла/папки.
    match = match_command_definition("create_file", text)
    if match and executor._is_enabled("create_file"):
        path = match.group(1).strip().strip("\"'")
        return direct_tool_fn("create_file", {"path": path, "content": ""}, confirmation_callback)

    match = match_command_definition("create_folder", text)
    if match and executor._is_enabled("create_folder"):
        path = match.group(1).strip().strip("\"'")
        return direct_tool_fn("create_folder", {"path": path}, confirmation_callback)

    # Запись файла. Форматы: «запиши в файл X: текст» / «перезапиши файл X на текст».
    match = match_command_definition("write_file", text)
    if match and executor._is_enabled("write_file"):
        path, content = match.groups()
        return direct_tool_fn("write_file", {"path": path.strip().strip("\"'"), "content": content.strip()}, confirmation_callback)

    # Переименование/копирование/перемещение.
    match = match_command_definition("rename_file", text)
    if match and executor._is_enabled("rename_file"):
        path, new_name = match.groups()
        return direct_tool_fn("rename_file", {"path": path.strip().strip("\"'"), "new_name": new_name.strip().strip("\"'")}, confirmation_callback)

    match = match_command_definition("copy_file", text)
    if match and executor._is_enabled("copy_file"):
        path, destination = match.groups()
        return direct_tool_fn("copy_file", {"path": path.strip().strip("\"'"), "destination": destination.strip().strip("\"'")}, confirmation_callback)

    match = match_command_definition("move_file", text)
    if match and executor._is_enabled("move_file"):
        path, destination = match.groups()
        return direct_tool_fn("move_file", {"path": path.strip().strip("\"'"), "destination": destination.strip().strip("\"'")}, confirmation_callback)

    # Информация о файле.
    match = match_command_definition("file_info", text)
    if match and executor._is_enabled("file_info"):
        path = match.group(1).strip().strip("\"'")
        return direct_tool_fn("file_info", {"path": path}, confirmation_callback)

    return None


def dispatch_app_management_command(
    text: str,
    executor: ToolExecutor,
    direct_tool_fn: Callable,
    resolve_action_fn: Callable[[str], tuple[str, str] | None],
    resolve_target_fn: Callable,
    confirmation_callback=None,
    alias_confirmation_callback=None,
) -> str | None:
    """Обрабатывает поиск и сворачивание окон приложений."""
    # Поиск приложения
    match = match_command_definition("find_application", text)
    if match and executor._is_enabled("find_application"):
        name = match.group(1).strip()
        return direct_tool_fn("find_application", {"name": name}, confirmation_callback)

    # Сворачивание приложения
    lower = " ".join(text.lower().split())
    action = resolve_action_fn(lower)
    if action and action[0] == "minimize" and executor._is_enabled("minimize_application"):
        target = action[1]
        if target.strip().casefold() in GENERIC_APPLICATION_TARGETS:
            return "Какое приложение свернуть?"
        resolved, error = resolve_target_fn(target, ("applications",), alias_confirmation_callback)
        if error:
            return f"Не выполнено: {error}"
        result = executor.execute("minimize_application", {"name": resolved}, confirmation_callback=confirmation_callback)
        if result.get("success"):
            return f"{target} свернут."
        return f"Не удалось свернуть {target}: {result.get('error', 'неизвестная ошибка')}"

    return None


def dispatch_ollama_control_command(
    text: str,
    ollama_manager: Any,
    model_name: str,
) -> str | None:
    """Обрабатывает управление сервером Ollama и выгрузку моделей."""
    lower = " ".join(text.lower().split())
    model = str(model_name).strip()

    model_aliases = {
        "модель", "модел", "квен", "квэн", "квен 3", "квэн 3", "квен3", "квэн3",
        "qwen", "qwen 3", "qwen3", "qwen3 1.7b", "qwen 1.7b",
        "ллм", "ллмку", "ллам", "llm",
    }
    model_action = re.fullmatch(
        r"(?:выгрузи|выгрузить|освободи|освободить|закрой|закрыть|останови|остановить|выключи|выключить)"
        r"\s+(?:текущую\s+)?(.+)",
        lower,
    )
    if model_action:
        target = model_action.group(1).strip()
        if target in model_aliases or any(alias in target for alias in model_aliases if alias not in {"модель"}):
            result = ollama_manager.unload_model(model)
            return f"Модель {model} выгружена." if result.get("success") else f"Не удалось выгрузить модель: {result.get('error', 'неизвестная ошибка')}"

    ollama_aliases = {
        "оллама", "олламу", "олламы", "оллам", "оллама", "ollama",
        "сервер оллама", "сервер ollama", "сервер ламы", "сервер лам",
    }
    server_action = re.fullmatch(
        r"(?:закрой|закрыть|останови|остановить|выключи|выключить|заверши|завершить)"
        r"\s+(.+)",
        lower,
    )
    if server_action and server_action.group(1).strip() in ollama_aliases:
        result = ollama_manager.stop_server()
        return "Ollama Server остановлен." if result.get("success") else f"Не удалось остановить Ollama: {result.get('error', 'неизвестная ошибка')}"

    if lower in {item.casefold() for item in command_definition_display("model_unload")}:
        result = ollama_manager.unload_model(model)
        return f"Модель {model} выгружена." if result.get("success") else f"Не удалось выгрузить модель: {result.get('error', 'неизвестная ошибка')}"

    return None
