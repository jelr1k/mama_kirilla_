from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request


HEALTH_URL = "http://127.0.0.1:8765/health"
TIMEOUT_SECS = 35


def _check_health() -> bool:
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "JarvisSplash/2.0"})
        with urllib.request.urlopen(req, timeout=0.6) as response:
            if response.status == 200:
                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") == "ok":
                    return True
    except Exception:
        pass
    return False


def wait_for_gateway(timeout: int = TIMEOUT_SECS) -> int:
    """Wait until Python backend gateway is ready on port 8765."""
    if "--dry-run" in sys.argv:
        return 0

    t0 = time.time()
    dots = 0
    if sys.stdout is not None:
        sys.stdout.write("[Jarvis] Ожидание запуска ядра и шлюза API (127.0.0.1:8765)")
        sys.stdout.flush()

    while time.time() - t0 < timeout:
        if _check_health():
            if sys.stdout is not None:
                sys.stdout.write(" [ГОТОВО]\n")
                sys.stdout.flush()
            return 0
        time.sleep(0.3)
        dots += 1
        if dots % 3 == 0 and sys.stdout is not None:
            sys.stdout.write(".")
            sys.stdout.flush()

    if sys.stdout is not None:
        sys.stdout.write(" [ТАЙМАУТ]\n")
        sys.stdout.flush()
    if sys.stderr is not None:
        sys.stderr.write("[ERROR] Шлюз ядра не ответил вовремя на http://127.0.0.1:8765/health\n")
        sys.stderr.flush()
    return 1


if __name__ == "__main__":
    sys.exit(wait_for_gateway())
