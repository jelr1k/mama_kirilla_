from __future__ import annotations

import logging
import webbrowser
from typing import Any

from fastapi import APIRouter, Depends

from services.gateway.deps import get_gateway
from tools.registry import TOOLS

logger = logging.getLogger("jarvis.gateway.settings")

router = APIRouter(tags=["settings"])

TOOL_NAMES = {
    "search_files": "Поиск файлов",
    "read_file": "Чтение файла",
    "create_file": "Создание файла",
    "write_file": "Запись файла",
    "delete_file": "Удаление файла",
    "rename_file": "Переименование файла",
    "copy_file": "Копирование файла",
    "move_file": "Перемещение файла",
    "create_folder": "Создание папки",
    "file_info": "Информация о файле",
    "find_application": "Поиск приложения",
    "get_process_status": "Проверка состояния процесса",
    "launch_application": "Запуск приложения",
    "minimize_application": "Сворачивание приложения",
    "close_application": "Закрытие приложения",
    "open_url": "Открытие ссылки",
    "get_system_telemetry": "Системная телеметрия",
    "control_media": "Управление медиа и звуком",
    "empty_recycle_bin": "Очистка корзины",
    "get_current_time_date": "Текущее время и дата",
    "lock_pc": "Блокировка ПК",
    "open_system_folder": "Открытие системных папок",
    "take_screenshot": "Снимок экрана",
    "fibonacci_calculator": "Калькулятор Фибоначчи",
    "apply_mouse_settings": "Настройки мыши ZET Gaming Fury",
}


@router.get("/api/settings")
def get_settings(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    cfg = getattr(gateway.app_context, "config", None)
    return {"settings": cfg.data if cfg and hasattr(cfg, "data") else {}}


@router.post("/api/settings")
def update_settings(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    app_context = gateway.app_context
    cfg = getattr(app_context, "config", None)
    if not cfg:
        return {"success": False, "error": "ConfigManager unavailable"}
    old_tg = cfg.get("telegram", {}) if "telegram" in payload else None
    for k, v in payload.items():
        cfg.set(k, v)
    cfg.save()
    if hasattr(app_context, "apply_settings"):
        app_context.apply_settings()
    if old_tg is not None and cfg.get("telegram", {}) != old_tg:
        try:
            from modules.telegram_bot import get_telegram_bot
            t_bot = get_telegram_bot(config_manager=cfg, app_context=app_context)
            t_bot.stop()
            if t_bot.is_enabled and t_bot.bot_token:
                t_bot.start()
        except Exception as t_err:
            logger.warning("telegram_bot_reload_failed: %s", t_err)
    name = cfg.get("assistant_name", "Kirieshcka")
    model = cfg.get("model", "")
    app_title = cfg.get("app_title", "Kirieshcka v2")
    gateway.hub.broadcast({
        "type": "state",
        "assistant_name": name,
        "model": model,
        "app_title": app_title,
    })
    return {"success": True}


@router.get("/api/rofl")
def get_rofl_settings(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    cfg = getattr(gateway.app_context, "config", None)
    rofl_cfg = cfg.get("rofl", {}) if cfg else {}
    return {
        "chance": float(rofl_cfg.get("chance", 0.12)),
        "demon_chance": float(rofl_cfg.get("demon_chance", 0.15)),
    }


@router.post("/api/rofl/verify")
def verify_rofl_secret(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    secret = str(payload.get("secret", "")).strip().casefold()
    if secret in ("джарвис", "кириешка", "kirieshcka"):
        cfg = getattr(gateway.app_context, "config", None)
        rofl_cfg = cfg.get("rofl", {}) if cfg else {}
        return {
            "success": True,
            "unlocked": True,
            "chance": float(rofl_cfg.get("chance", 0.12)),
            "demon_chance": float(rofl_cfg.get("demon_chance", 0.15)),
        }
    return {"success": False, "unlocked": False, "error": "Неверное служебное слово"}


@router.post("/api/rofl")
def update_rofl_settings(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    secret = str(payload.get("secret", "")).strip().casefold()
    if secret not in ("джарвис", "кириешка", "kirieshcka"):
        return {"success": False, "error": "Неверное служебное слово"}
    chance = max(0.0, min(1.0, float(payload.get("chance", 0.12))))
    demon_chance = max(0.0, min(1.0, float(payload.get("demon_chance", 0.15))))
    cfg = getattr(gateway.app_context, "config", None)
    if cfg:
        rofl_dict = cfg.data.setdefault("rofl", {})
        rofl_dict["chance"] = chance
        rofl_dict["demon_chance"] = demon_chance
        cfg.save()
    events = getattr(gateway.app_context, "events", None)
    if events:
        events.emit("rofl.settings_changed", {"chance": chance, "demon_chance": demon_chance})
    return {
        "success": True,
        "chance": chance,
        "demon_chance": demon_chance,
    }


@router.get("/api/tools")
def list_tools(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    perm = getattr(gateway.app_context, "permission_manager", None)
    items = []
    for name, tool in TOOLS.items():
        enabled = perm.is_enabled(name) if perm else True
        items.append({
            "name": name,
            "title": TOOL_NAMES.get(name, name),
            "description": tool.get("description", ""),
            "enabled": enabled,
            "requires_confirmation": bool(tool.get("requires_confirmation", False)),
        })
    return {"tools": items}


@router.post("/api/tools/permission")
def set_tool_permission(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    tool_name = payload.get("tool", "").strip()
    enabled = bool(payload.get("enabled", True))
    perm = getattr(gateway.app_context, "permission_manager", None)
    if not perm:
        return {"success": False, "error": "PermissionManager not available"}
    try:
        perm.update(tool_name, enabled)
        return {"success": True, "tool": tool_name, "enabled": enabled}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/api/aliases")
def get_aliases(category: str | None = None, gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    alias_mgr = getattr(gateway.app_context, "alias_manager", None)
    if not alias_mgr:
        return {"aliases": []}
    return {"aliases": alias_mgr.list_objects(category)}


@router.post("/api/aliases")
def save_aliases(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    alias_mgr = getattr(gateway.app_context, "alias_manager", None)
    if not alias_mgr:
        return {"success": False, "error": "AliasManager unavailable"}
    category = payload.get("category", "applications")
    target = payload.get("target", "").strip()
    aliases = payload.get("aliases", [])
    if not target:
        return {"success": False, "error": "Target is required"}
    alias_mgr.set_aliases(category, target, aliases)
    alias_mgr.save()
    return {"success": True}


@router.delete("/api/aliases")
def delete_alias(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    alias_mgr = getattr(gateway.app_context, "alias_manager", None)
    if not alias_mgr:
        return {"success": False, "error": "AliasManager unavailable"}
    category = payload.get("category", "applications")
    target = payload.get("target", "").strip()
    alias_mgr.remove_object(category, target)
    alias_mgr.save()
    return {"success": True}


@router.get("/api/websites")
def list_websites(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    mgr = getattr(gateway.app_context, "website_manager", None)
    if not mgr:
        return {"websites": []}
    return {"websites": mgr.get_websites()}


@router.post("/api/websites")
def create_website(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    mgr = getattr(gateway.app_context, "website_manager", None)
    if not mgr:
        return {"success": False, "error": "WebsiteManager not available"}
    name = payload.get("name", "").strip()
    url = payload.get("url", "").strip()
    aliases = payload.get("aliases", [])
    auto_aliases = bool(payload.get("auto_aliases", True))
    if not name or not url:
        return {"success": False, "error": "Name and URL are required"}
    try:
        entry = mgr.add_website(name, url, aliases=aliases, auto_aliases=auto_aliases)
        return {"success": True, "website": entry}
    except Exception as exc:
        logger.exception("create_website_failed")
        return {"success": False, "error": str(exc)}


@router.put("/api/websites/{site_id}")
def update_website(site_id: str, payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    mgr = getattr(gateway.app_context, "website_manager", None)
    if not mgr:
        return {"success": False, "error": "WebsiteManager not available"}
    name = payload.get("name", "").strip()
    url = payload.get("url", "").strip()
    aliases = payload.get("aliases", [])
    success = mgr.update_website(site_id, name, url, aliases)
    return {"success": success}


@router.delete("/api/websites/{site_id}")
def delete_website(site_id: str, gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    mgr = getattr(gateway.app_context, "website_manager", None)
    if not mgr:
        return {"success": False, "error": "WebsiteManager not available"}
    success = mgr.delete_website(site_id)
    return {"success": success}


@router.post("/api/websites/open")
def open_website(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    url = payload.get("url", "").strip()
    site_id = payload.get("site_id", "").strip()
    mgr = getattr(gateway.app_context, "website_manager", None)
    if site_id and mgr:
        for s in mgr.get_websites():
            if s.get("id") == site_id:
                url = s.get("url", "")
                break
    if not url:
        return {"success": False, "error": "URL or site_id is required"}
    try:
        webbrowser.open(url)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/api/websites/reset")
def reset_websites(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    mgr = getattr(gateway.app_context, "website_manager", None)
    if mgr:
        mgr.reset_to_defaults()
        return {"success": True, "websites": mgr.get_websites()}
    return {"success": False}
