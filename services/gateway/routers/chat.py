from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from services.gateway.deps import get_gateway

logger = logging.getLogger("jarvis.gateway.chat")

router = APIRouter(tags=["chat"])


@router.get("/api/commands")
def commands_catalog(gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    chat_service = getattr(gateway.app_context, "chat_service", None)
    if chat_service and hasattr(chat_service, "router"):
        return {"commands": chat_service.router.command_catalog()}
    return {"commands": []}


@router.post("/api/chat")
def send_chat(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    text = payload.get("text", "").strip()
    if not text:
        return {"success": False, "error": "Empty message"}
    chat_service = getattr(gateway.app_context, "chat_service", None)
    if not chat_service:
        return {"success": False, "error": "ChatService unavailable"}
    chat_service.send(text)
    return {"success": True}


@router.post("/api/commands/execute")
def execute_command(payload: dict[str, Any], gateway: Any = Depends(get_gateway)) -> dict[str, Any]:
    cmd = payload.get("command", "").strip()
    if not cmd:
        return {"success": False, "error": "Empty command"}
    chat_service = getattr(gateway.app_context, "chat_service", None)
    if chat_service:
        chat_service.send(cmd)
        return {"success": True}
    return {"success": False, "error": "ChatService unavailable"}
