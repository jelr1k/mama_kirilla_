from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any
from urllib.parse import urlparse

from fastapi import WebSocket

logger = logging.getLogger("jarvis.gateway.hub")


def is_allowed_ws_origin(origin: str | None) -> bool:
    """Проверяет Origin заголовка WebSocket для защиты от Cross-Site WebSocket Hijacking (CSWSH)."""
    if not origin or origin == "null":
        return True
    try:
        parsed = urlparse(origin)
        scheme = (parsed.scheme or "").lower()
        hostname = (parsed.hostname or "").lower()
        if scheme == "tauri":
            return True
        if hostname in ("127.0.0.1", "localhost", "tauri.localhost", "testserver"):
            return True
        return False
    except Exception:
        return False


_is_allowed_ws_origin = is_allowed_ws_origin


class WebSocketHub:
    """Thread-safe WebSocket manager broadcasting events to connected UI clients."""

    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._disconnect_timer: threading.Timer | None = None
        self.on_all_disconnected: Any = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            if self._disconnect_timer:
                self._disconnect_timer.cancel()
                self._disconnect_timer = None
            self._connections.add(websocket)
        logger.info("ui_client_connected clients=%d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.discard(websocket)
            has_remaining = bool(self._connections)
            if not has_remaining and self.on_all_disconnected:
                if self._disconnect_timer:
                    self._disconnect_timer.cancel()
                self._disconnect_timer = threading.Timer(4.0, self.on_all_disconnected)
                self._disconnect_timer.daemon = True
                self._disconnect_timer.start()
        logger.info("ui_client_disconnected clients=%d", len(self._connections))

    @property
    def has_clients(self) -> bool:
        with self._lock:
            return bool(self._connections)

    def broadcast(self, payload: dict[str, Any]) -> None:
        """Thread-safe broadcast called from any worker thread."""
        if not self._connections or self._loop is None or self._loop.is_closed():
            return

        message = json.dumps(payload, ensure_ascii=False)

        async def _send_all():
            with self._lock:
                targets = list(self._connections)
            dead = []
            for ws in targets:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            if dead:
                with self._lock:
                    for d in dead:
                        self._connections.discard(d)

        try:
            asyncio.run_coroutine_threadsafe(_send_all(), self._loop)
        except Exception as exc:
            logger.debug("broadcast_enqueue_failed error=%s", exc)
