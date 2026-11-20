from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent


def _find_project_root() -> Path:
    for candidate in (APP_DIR, APP_DIR.parent):
        if (candidate / "core").is_dir():
            return candidate
    return APP_DIR


PROJECT_ROOT = _find_project_root()
project_root = str(PROJECT_ROOT)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.application import JarvisApplication
from core.logging_config import setup_logging
from core.update_health import UPDATE_HEALTH_ENV, write_startup_health_marker
from core.version import APP_VERSION


def main() -> int:
    if sys.stdout is None:
        class _NullStream:
            encoding = "utf-8"
            errors = "replace"
            def write(self, *a, **k): pass
            def writelines(self, lines): pass
            def flush(self): pass
            def isatty(self): return False
        sys.stdout = _NullStream()
    if sys.stderr is None:
        sys.stderr = sys.stdout

    logger = setup_logging()

    if "--legacy-gui" in sys.argv or "--pyside" in sys.argv:
        msg = "Legacy PySide6 GUI has been archived in ui_archive/ and is no longer supported in runtime."
        logger.error(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)

    logger.info("Starting Jarvis headless backend...")

    # Single instance guard 1: atomic file lock via msvcrt on Windows
    _lock_handle = None
    if sys.platform == "win32":
        try:
            import msvcrt
            from core.app_paths import LOCAL_DATA_DIR
            lock_path = LOCAL_DATA_DIR / "assistant.lock"
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            _lock_handle = open(lock_path, "a+")
            _lock_handle.seek(0)
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        except (OSError, IOError):
            logger.warning("Another Assistant instance holds the process lock. Exiting.")
            if _lock_handle:
                try:
                    _lock_handle.close()
                except Exception:
                    pass
            return 0

    # Single instance guard 2: don't start duplicate headless backend if gateway is already active
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:8765/health", headers={"User-Agent": "Jarvis-Single-Instance"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            if resp.status == 200:
                logger.warning("Another Jarvis backend instance is already running on 127.0.0.1:8765. Exiting.")
                if _lock_handle:
                    try:
                        import msvcrt
                        _lock_handle.seek(0)
                        msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    except Exception:
                        pass
                    finally:
                        try:
                            _lock_handle.close()
                        except Exception:
                            pass
                return 0
    except Exception:
        pass

    backend = None
    stop_event = threading.Event()

    def _signal_handler(signum, _frame):
        logger.info("Received termination signal %s, shutting down...", signum)
        stop_event.set()

    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except (ValueError, AttributeError):
        pass

    try:
        import atexit
        backend = JarvisApplication()
        atexit.register(backend.shutdown)
        backend.start()

        try:
            write_startup_health_marker(APP_VERSION)
        except Exception:
            logger.exception("Could not write updater startup health marker")

        logger.info("Jarvis headless backend running (gateway on 127.0.0.1:8765)")

        # Listen for application shutdown event
        if hasattr(backend, "events"):
            backend.events.subscribe("application.shutdown", lambda *_: stop_event.set())

        # Main thread blocks until signal or stop_event is set
        while not stop_event.is_set():
            stop_event.wait(timeout=1.0)

    except Exception:
        logger.exception("Jarvis headless startup or runtime failed")
        sys.exit(1)
    finally:
        if backend is not None:
            logger.info("Shutting down Jarvis backend...")
            try:
                backend.shutdown()
            except Exception:
                logger.exception("Error during backend shutdown")
        if _lock_handle:
            try:
                import msvcrt
                _lock_handle.seek(0)
                msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
            finally:
                try:
                    _lock_handle.close()
                except Exception:
                    pass

    logger.info("Jarvis headless backend stopped successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
