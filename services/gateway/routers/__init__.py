from __future__ import annotations

from services.gateway.routers.chat import router as chat_router
from services.gateway.routers.integrations import router as integrations_router
from services.gateway.routers.settings import router as settings_router
from services.gateway.routers.system import router as system_router
from services.gateway.routers.voice import router as voice_router

__all__ = [
    "chat_router",
    "integrations_router",
    "settings_router",
    "system_router",
    "voice_router",
]
