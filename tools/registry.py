from __future__ import annotations

from tools.applications import find_application, get_process_status, launch_application, minimize_application, open_url
from tools.application_closer import close_application
from tools.files import (
    copy_file,
    create_file,
    create_folder,
    delete_file,
    file_info,
    move_file,
    read_file,
    rename_file,
    search_files,
    write_file,
)
from tools.paths import TOOL_WORKSPACE
from tools.system_info import get_system_telemetry
from tools.media_control import control_media
from tools.system_actions import (
    empty_recycle_bin,
    get_current_time_date,
    lock_pc,
    open_system_folder,
    take_screenshot,
)


def _file_description(action: str) -> str:
    return (
        f"{action} только в рабочей папке Jarvis ({TOOL_WORKSPACE}) и её подпапках. "
        "Путь проходит отдельную проверку sandbox. Абсолютные пути вне workspace блокируются; "
        "несколько совпадений не выбираются автоматически."
    )


TOOLS = {
    "search_files": {
        "function": search_files,
        "description": _file_description("Ищет файлы по имени и расширению"),
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "extension": {"type": "string"}}, "required": ["name"]},
        "requires_confirmation": False,
    },
    "read_file": {
        "function": read_file,
        "description": _file_description("Читает небольшой UTF-8 текстовый файл"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        "requires_confirmation": False,
    },
    "create_file": {
        "function": create_file,
        "description": _file_description("Создаёт новый текстовый файл"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
        "requires_confirmation": False,
    },
    "write_file": {
        "function": write_file,
        "description": _file_description("Записывает или перезаписывает текстовый файл"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
        "requires_confirmation": True,
    },
    "delete_file": {
        "function": delete_file,
        "description": _file_description("Удаляет один файл"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        "requires_confirmation": True,
    },
    "rename_file": {
        "function": rename_file,
        "description": _file_description("Переименовывает один файл"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "new_name": {"type": "string"},}, "required": ["path", "new_name"]},
        "requires_confirmation": True,
    },
    "copy_file": {
        "function": copy_file,
        "description": _file_description("Копирует файл внутри workspace"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "destination": {"type": "string"}}, "required": ["path", "destination"]},
        "requires_confirmation": True,
    },
    "move_file": {
        "function": move_file,
        "description": _file_description("Перемещает файл внутри workspace"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "destination": {"type": "string"}}, "required": ["path", "destination"]},
        "requires_confirmation": True,
    },
    "create_folder": {
        "function": create_folder,
        "description": _file_description("Создаёт папку"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        "requires_confirmation": False,
    },
    "file_info": {
        "function": file_info,
        "description": _file_description("Получает информацию о файле"),
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        "requires_confirmation": False,
    },
    "find_application": {
        "function": find_application,
        "description": "Ищет установленное приложение по имени через ярлыки Windows и PATH, не выполняя shell-команды.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        "requires_confirmation": False,
    },
    "get_process_status": {
        "function": get_process_status,
        "description": "Проверяет, запущен ли процесс приложения.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        "requires_confirmation": False,
    },
    "launch_application": {
        "function": launch_application,
        "description": "Запускает найденное Windows-приложение/ярлык по целевому пути, проверенному sandbox. Не использует shell.",
        "parameters": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]},
        "requires_confirmation": False,
    },
    "minimize_application": {
        "function": minimize_application,
        "description": "Сворачивает главное окно Windows-приложения, находя его по имени/алиасу или имени executable.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        "requires_confirmation": False,
    },
    "close_application": {
        "function": close_application,
        "description": "Мягко завершает приложение. Запрашивает явное подтверждение.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        "requires_confirmation": True,
    },
    "get_system_telemetry": {
        "function": get_system_telemetry,
        "description": "Возвращает текущую нагрузку процессора (CPU), оперативной памяти (RAM), видеокарты, свободное место на дисках и время работы системы.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "requires_confirmation": False,
    },
    "control_media": {
        "function": control_media,
        "description": "Управляет системным звуком и медиаплеером Windows: volume_up, volume_down, volume_mute, play_pause, next_track, prev_track.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["volume_up", "volume_down", "volume_mute", "play_pause", "next_track", "prev_track"],
                },
                "steps": {"type": "integer"},
            },
            "required": ["action"],
        },
        "requires_confirmation": False,
    },
    "open_url": {
        "function": open_url,
        "description": "Открывает HTTP/HTTPS URL системным обработчиком Windows.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        "requires_confirmation": False,
    },
    "empty_recycle_bin": {
        "function": empty_recycle_bin,
        "description": "Очищает системную корзину Windows без подтверждения.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "requires_confirmation": False,
    },
    "take_screenshot": {
        "function": take_screenshot,
        "description": "Делает скриншот экрана и сохраняет его в папку workspace/screenshots.",
        "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": []},
        "requires_confirmation": False,
    },
    "lock_pc": {
        "function": lock_pc,
        "description": "Блокирует рабочий стол Windows.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "requires_confirmation": False,
    },
    "get_current_time_date": {
        "function": get_current_time_date,
        "description": "Возвращает текущую дату и системное время на русском языке.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "requires_confirmation": False,
    },
    "open_system_folder": {
        "function": open_system_folder,
        "description": "Открывает стандартную системную папку Windows (загрузки, рабочий стол, документы, проводник, скриншоты).",
        "parameters": {"type": "object", "properties": {"folder_name": {"type": "string"}}, "required": ["folder_name"]},
        "requires_confirmation": False,
    },
}


def ollama_tools(enabled_tools=None) -> list[dict]:
    names = set(enabled_tools) if enabled_tools is not None else set(TOOLS)
    return [
        {"type": "function", "function": {"name": name, "description": tool["description"], "parameters": tool["parameters"]}}
        for name, tool in TOOLS.items()
        if name in names
    ]
