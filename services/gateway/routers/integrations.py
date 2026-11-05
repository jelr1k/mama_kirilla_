from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends

from core.app_paths import WORKSPACE_DIR
from services.gateway.deps import get_gateway

logger = logging.getLogger("jarvis.gateway.integrations")

router = APIRouter(tags=["integrations"])


# --- Workspace API ---

@router.get("/api/workspace")
def get_workspace(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    from core.workspace_view_model import WorkspaceViewModel
    alias_mgr = getattr(gateway.app_context, "alias_manager", None)
    vm = WorkspaceViewModel(WORKSPACE_DIR, alias_mgr)
    items = []
    try:
        for obj in vm.refresh():
            items.append({
                "name": obj.entry.name,
                "path": obj.entry.relative_path,
                "category": obj.entry.category,
                "exists": obj.entry.path.exists(),
                "is_dir": obj.entry.is_dir,
                "user_aliases": list(obj.user_aliases),
                "automatic_aliases": list(obj.automatic_aliases),
            })
    except Exception as exc:
        logger.debug("workspace_refresh_failed: %s", exc)
    return {"workspace_dir": str(WORKSPACE_DIR), "items": items}


@router.post("/api/workspace/open")
def open_workspace() -> dict[str, Any]:
    try:
        os.startfile(WORKSPACE_DIR)
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# --- VPN / Zapret API ---

@router.get("/api/vpn/status")
def vpn_status(force: bool = False) -> dict[str, Any]:
    from core.vpn_manager import get_vpn_manager

    return get_vpn_manager().status(force=force)


@router.post("/api/vpn/zapret")
def vpn_launch_zapret() -> dict[str, Any]:
    from core.vpn_manager import get_vpn_manager

    return get_vpn_manager().launch_zapret()


@router.post("/api/vpn/connect")
def vpn_connect(payload: dict[str, Any]) -> dict[str, Any]:
    from core.vpn_manager import get_vpn_manager

    return get_vpn_manager().connect(payload.get("client"))


# --- Telegram Bot API ---

@router.get("/api/telegram/status")
def get_telegram_status(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    from modules.telegram_bot import get_telegram_bot

    bot = get_telegram_bot(
        config_manager=getattr(gateway.app_context, "config", None),
        app_context=gateway.app_context,
    )
    return bot.get_status()


@router.post("/api/telegram/test")
async def test_telegram_token(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    from modules.telegram_bot import get_telegram_bot

    bot = get_telegram_bot(
        config_manager=getattr(gateway.app_context, "config", None),
        app_context=gateway.app_context,
    )
    token = payload.get("token") or bot.bot_token
    base_url = payload.get("api_base_url") or None
    return await bot.test_token(token, base_url=base_url)


@router.post("/api/telegram/restart")
def restart_telegram_bot(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    from modules.telegram_bot import get_telegram_bot

    bot = get_telegram_bot(
        config_manager=getattr(gateway.app_context, "config", None),
        app_context=gateway.app_context,
    )
    bot.stop()
    if bot.is_enabled and bot.bot_token:
        bot.start()
    return {"success": True, "status": bot.get_status()}


# --- Protocols API ---

@router.get("/api/protocols")
def get_protocols(profile_id: str | None = None, gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    pm = getattr(gateway.app_context, "protocols_manager", None)
    if not pm:
        return {"active_profile": "default", "profiles": {}, "protocols": []}
    return {
        "active_profile": pm.get_active_profile(),
        "profiles": pm.list_profiles(),
        "protocols": pm.get_protocols(profile_id),
    }


@router.post("/api/protocols/profile/select")
def select_protocol_profile(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    pm = getattr(gateway.app_context, "protocols_manager", None)
    if not pm:
        return {"success": False, "error": "Protocols manager not initialized"}
    profile_id = str(payload.get("profile_id", "")).strip()
    ok = pm.set_active_profile(profile_id)
    if ok:
        gateway.hub.broadcast({
            "type": "protocols.changed",
            "data": {
                "active_profile": pm.get_active_profile(),
                "profiles": pm.list_profiles(),
                "protocols": pm.get_protocols(),
            },
        })
        return {"success": True, "active_profile": profile_id, "protocols": pm.get_protocols()}
    return {"success": False, "error": f"Профиль '{profile_id}' не найден."}


@router.post("/api/protocols/profile")
def create_protocol_profile(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    pm = getattr(gateway.app_context, "protocols_manager", None)
    if not pm:
        return {"success": False, "error": "Protocols manager not initialized"}
    name = str(payload.get("name", "")).strip() or "Новый профиль"
    copy_from_active = bool(payload.get("copy_from_active", True))
    profile_id = pm.add_profile(name, copy_from_active=copy_from_active)
    gateway.hub.broadcast({
        "type": "protocols.changed",
        "data": {
            "active_profile": pm.get_active_profile(),
            "profiles": pm.list_profiles(),
            "protocols": pm.get_protocols(),
        },
    })
    return {"success": True, "profile_id": profile_id, "profiles": pm.list_profiles()}


@router.delete("/api/protocols/profile/{profile_id}")
def delete_protocol_profile(profile_id: str, gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    pm = getattr(gateway.app_context, "protocols_manager", None)
    if not pm:
        return {"success": False, "error": "Protocols manager not initialized"}
    ok = pm.delete_profile(profile_id)
    if ok:
        gateway.hub.broadcast({
            "type": "protocols.changed",
            "data": {
                "active_profile": pm.get_active_profile(),
                "profiles": pm.list_profiles(),
                "protocols": pm.get_protocols(),
            },
        })
        return {"success": True, "profiles": pm.list_profiles(), "active_profile": pm.get_active_profile()}
    return {"success": False, "error": "Нельзя удалить основной профиль или профиль не найден."}


@router.post("/api/protocols")
def save_protocol_entry(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    pm = getattr(gateway.app_context, "protocols_manager", None)
    if not pm:
        return {"success": False, "error": "Protocols manager not initialized"}
    proto_data = payload.get("protocol") if isinstance(payload.get("protocol"), dict) else payload
    profile_id = payload.get("profile_id")
    saved_id = pm.save_protocol(proto_data, profile_id=profile_id)
    gateway.hub.broadcast({
        "type": "protocols.changed",
        "data": {
            "active_profile": pm.get_active_profile(),
            "profiles": pm.list_profiles(),
            "protocols": pm.get_protocols(),
        },
    })
    return {"success": True, "protocol_id": saved_id, "protocols": pm.get_protocols(profile_id)}


@router.delete("/api/protocols/{protocol_id}")
def delete_protocol_entry(protocol_id: str, profile_id: str | None = None, gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    pm = getattr(gateway.app_context, "protocols_manager", None)
    if not pm:
        return {"success": False, "error": "Protocols manager not initialized"}
    ok = pm.delete_protocol(protocol_id, profile_id=profile_id)
    if ok:
        gateway.hub.broadcast({
            "type": "protocols.changed",
            "data": {
                "active_profile": pm.get_active_profile(),
                "profiles": pm.list_profiles(),
                "protocols": pm.get_protocols(),
            },
        })
        return {"success": True, "protocols": pm.get_protocols(profile_id)}
    return {"success": False, "error": f"Протокол '{protocol_id}' не найден."}


@router.post("/api/protocols/execute")
def execute_protocol_endpoint(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    from services.stark_protocols import StarkProtocols

    proto_id = str(payload.get("protocol_id", "")).strip()
    profile_id = payload.get("profile_id")
    pm = getattr(gateway.app_context, "protocols_manager", None)
    cfg = getattr(gateway.app_context, "config", None)
    ollama_url = getattr(cfg, "ollama_url", None)
    model = cfg.get("model") if hasattr(cfg, "get") else None

    proto = None
    if pm:
        proto = pm.get_protocol_by_id(proto_id, profile_id=profile_id)

    res = StarkProtocols.execute_protocol(proto or proto_id, ollama_url=ollama_url, model=model)
    return {"success": True, "protocol_id": proto_id, "result": res}


# --- Steam API ---

@router.get("/api/steam")
def get_steam_info(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    sm = getattr(gateway.app_context, "steam_manager", None)
    if not sm:
        return {"installed": False, "steam_path": None, "games": []}
    steam_root = sm.find_steam_root() if hasattr(sm, "find_steam_root") else None
    is_installed = sm.is_steam_installed() if hasattr(sm, "is_steam_installed") else (steam_root is not None)
    return {
        "installed": is_installed,
        "steam_path": str(steam_root) if steam_root else None,
        "games": sm.scan_installed_games(),
    }


@router.post("/api/steam/launch")
def launch_steam_game(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    sm = getattr(gateway.app_context, "steam_manager", None)
    if not sm:
        return {"success": False, "error": "Steam manager not initialized"}
    target = payload.get("appid") or payload.get("game") or payload.get("name")
    if target is None:
        return {"success": False, "error": "AppID или имя игры обязательны"}
    return sm.launch_game(target)


# --- Apps Indexer API ---

@router.get("/api/apps")
def get_installed_apps(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    indexer = getattr(gateway.app_context, "app_indexer", None)
    if not indexer:
        try:
            from core.app_indexer import AppIndexer
            indexer = AppIndexer.get_instance()
        except Exception:
            indexer = None
    if not indexer:
        return {"apps": [], "total": 0}
    apps = indexer.scan_installed_apps()
    return {"apps": apps, "total": len(apps)}


@router.post("/api/apps/launch")
def launch_installed_app(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    indexer = getattr(gateway.app_context, "app_indexer", None)
    if not indexer:
        try:
            from core.app_indexer import AppIndexer
            indexer = AppIndexer.get_instance()
        except Exception:
            indexer = None
    if not indexer:
        return {"success": False, "error": "App indexer not initialized"}
    target = payload.get("app") or payload.get("name") or payload.get("path")
    if not target:
        return {"success": False, "error": "Имя или путь приложения обязательны"}
    return indexer.launch_app(target)


@router.post("/api/apps/refresh")
def refresh_installed_apps(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    indexer = getattr(gateway.app_context, "app_indexer", None)
    if not indexer:
        try:
            from core.app_indexer import AppIndexer
            indexer = AppIndexer.get_instance()
        except Exception:
            indexer = None
    if not indexer:
        return {"success": False, "error": "App indexer not initialized", "apps": []}
    apps = indexer.scan_installed_apps(force=True)
    return {"success": True, "apps": apps, "total": len(apps)}
