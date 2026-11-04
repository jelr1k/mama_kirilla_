from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("jarvis.network_checker")

DEFAULT_TARGETS = [
    {
        "id": "discord",
        "name": "Discord Gateway",
        "url": "https://discord.com/api/v10/gateway",
        "icon": "discord",
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "url": "https://www.youtube.com/generate_204",
        "icon": "youtube",
    },
    {
        "id": "steam",
        "name": "Steam Store",
        "url": "https://store.steampowered.com",
        "icon": "steam",
    },
    {
        "id": "telegram",
        "name": "Telegram API",
        "url": "https://api.telegram.org",
        "icon": "telegram",
    },
    {
        "id": "github",
        "name": "GitHub",
        "url": "https://github.com",
        "icon": "github",
    },
]


class NetworkChecker:
    """Async availability & latency checker for major online services."""

    def __init__(self, targets: list[dict[str, str]] | None = None, cache_ttl: float = 15.0):
        self.targets = targets or DEFAULT_TARGETS
        self.cache_ttl = cache_ttl
        self._cached_result: dict[str, Any] | None = None
        self._last_check: float = 0.0
        self._lock = asyncio.Lock()

    async def _check_single(self, client: httpx.AsyncClient, target: dict[str, str]) -> dict[str, Any]:
        item_id = target["id"]
        name = target["name"]
        url = target["url"]
        icon = target.get("icon", "globe")
        follow_redirects = target.get("follow_redirects", True)

        if item_id == "telegram":
            follow_redirects = False
            try:
                from core.config_manager import ConfigManager
                cfg = ConfigManager().get("telegram", {})
                base = (cfg.get("api_base_url") or "").strip().rstrip("/")
                if base:
                    if not base.startswith(("http://", "https://")):
                        base = f"https://{base}"
                    url = base
            except Exception:
                pass

        t0 = time.perf_counter()
        try:
            resp = await client.get(url, follow_redirects=follow_redirects)
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            code = resp.status_code

            if 200 <= code < 400:
                status = "ok" if elapsed_ms < 350 else "slow"
                msg = f"{code} OK"
            elif 400 <= code < 500:
                # Even if 403 or 404, server is reachable and responded through the network
                status = "ok" if elapsed_ms < 350 else "slow"
                msg = f"{code} Ответ получен"
            else:
                status = "down"
                msg = f"{code} Ошибка сервера"

            return {
                "id": item_id,
                "name": name,
                "url": url,
                "icon": icon,
                "status": status,
                "ping_ms": elapsed_ms,
                "http_code": code,
                "message": msg,
            }
        except httpx.TimeoutException:
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            return {
                "id": item_id,
                "name": name,
                "url": url,
                "icon": icon,
                "status": "blocked",
                "ping_ms": None,
                "http_code": None,
                "message": "Таймаут (DPI / блокировка)",
            }
        except httpx.ConnectError:
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            return {
                "id": item_id,
                "name": name,
                "url": url,
                "icon": icon,
                "status": "down",
                "ping_ms": None,
                "http_code": None,
                "message": "Сброс / отказ соединения",
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            logger.debug("check_single_failed id=%s error=%s", item_id, exc)
            return {
                "id": item_id,
                "name": name,
                "url": url,
                "icon": icon,
                "status": "error",
                "ping_ms": None,
                "http_code": None,
                "message": f"Ошибка: {type(exc).__name__}",
            }

    async def check_all(self, force: bool = False) -> dict[str, Any]:
        """Check all targets in parallel with caching."""
        async with self._lock:
            now = time.time()
            if not force and self._cached_result is not None and (now - self._last_check) < self.cache_ttl:
                return self._cached_result

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "*/*",
            }
            # Short timeout so all 5 parallel checks resolve in ~3.0s max
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True, headers=headers, limits=limits) as client:
                tasks = [self._check_single(client, target) for target in self.targets]
                results = await asyncio.gather(*tasks)

            ok_count = sum(1 for r in results if r["status"] in ("ok", "slow"))
            total = len(results)

            if ok_count == total:
                overall = "all_ok"
            elif ok_count > 0:
                overall = "issues_detected"
            else:
                overall = "offline"

            payload = {
                "timestamp": round(now, 1),
                "summary": {
                    "status": overall,
                    "ok_count": ok_count,
                    "total": total,
                },
                "services": list(results),
            }
            self._cached_result = payload
            self._last_check = now
            return payload


_global_network_checker: NetworkChecker | None = None


def get_network_checker() -> NetworkChecker:
    global _global_network_checker
    if _global_network_checker is None:
        _global_network_checker = NetworkChecker()
    return _global_network_checker
