from __future__ import annotations

import logging
import os
import sys
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


from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from core.application import JarvisApplication
from core.app_paths import WORKSPACE_DIR
from core.update_health import UPDATE_HEALTH_ENV, write_startup_health_marker
from core.version import APP_VERSION
from services.model_service import ModelService
from services.statistics_service import StatisticsService
from services.update_downloader import UpdateDownloader
from services.update_validator import UpdateValidator
from services.update_backup import UpdateBackupService
from tools.registry import TOOLS
from presentation.application_controller import ApplicationController
from presentation.alias_controller import AliasController
from presentation.websites_controller import WebsitesController
from presentation.chat_controller import ChatController
from presentation.dependency_controller import DependencyController
from presentation.ollama_controller import OllamaController
from presentation.settings_controller import SettingsController
from presentation.statistics_controller import StatisticsController
from presentation.tools_controller import ToolsController
from presentation.voice_controller import VoiceController
from presentation.wake_word_controller import WakeWordController
from presentation.workspace_controller import WorkspaceController
from core.logging_config import setup_logging
try:
    from ui_archive.main_window import MainWindow
    from ui_archive.splash_screen import SplashScreen
except ImportError:
    MainWindow = None
    SplashScreen = None
from presentation.tray_icon import create_system_tray


def main():
    if sys.stdout is None:
        class _NullStream:
            def write(self, *a, **k): pass
            def flush(self): pass
            def isatty(self): return False
        sys.stdout = _NullStream()
    if sys.stderr is None:
        sys.stderr = sys.stdout

    logger = setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis")

    is_headless = "--headless" in sys.argv or os.environ.get("JARVIS_HEADLESS", "").lower() in ("1", "true", "yes")

    backend = None
    tray = None
    splash = None

    if is_headless:
        app.setQuitOnLastWindowClosed(False)
        try:
            backend = JarvisApplication()
            app.setApplicationName(backend.config.get("assistant_name", "JARVIS"))
            backend.start()
            tray = create_system_tray(app, backend)
            logger.info("Jarvis headless backend running (gateway on 127.0.0.1:8765)")
        except Exception as exc:
            logger.exception("Jarvis headless startup failed")
            if backend is not None:
                backend.shutdown()
            sys.exit(1)
    else:
        if not hasattr(app, "_mock_return_value") and not type(app).__name__.startswith("Mock"):
            try:
                splash = SplashScreen(min_duration_ms=1600)
                splash.show()
                app.processEvents()
            except Exception:
                splash = None

        try:
            backend = JarvisApplication()
            application_controller = ApplicationController(backend)
            chat_controller = ChatController(backend.chat_service, backend.events)
            voice_controller = VoiceController(backend.voice_service, backend.events)
            wake_word_controller = WakeWordController(backend.wake_word_detector, backend.events)
            dependency_controller = DependencyController(backend.dependency_manager, backend.events)
            settings_controller = SettingsController(
                backend.config,
                ModelService(backend.provider),
                dependency_controller,
                backend.tasks,
                backend.events,
                backend.voice_service,
                update_checker=backend.update_checker,
                update_service=backend.update_service,
                update_downloader=UpdateDownloader(),
                update_validator=UpdateValidator(),
                update_backup=UpdateBackupService(),
                tts_service=backend.tts_service,
            )
            alias_controller = AliasController(backend.alias_manager)
            tools_controller = ToolsController(backend.permission_manager, TOOLS)
            ollama_controller = OllamaController(backend.ollama_manager, backend.tasks)
            statistics_controller = StatisticsController(backend.statistics_service, ollama_controller, backend.tasks, backend.events)
            workspace_controller = WorkspaceController(WORKSPACE_DIR, backend.alias_manager)
            websites_controller = WebsitesController(backend.website_manager)
            window = MainWindow(
                application_controller, chat_controller, voice_controller, wake_word_controller,
                dependency_controller, settings_controller, alias_controller, tools_controller,
                ollama_controller, statistics_controller, workspace_controller, websites_controller,
            )
            app.setApplicationName(backend.config.get("assistant_name", "JARVIS"))
            if splash is not None:
                splash.finish_loading(window)
            else:
                window.show()
            application_controller.start()
            logger.info("Jarvis frontend/backend initialized")
        except Exception as exc:
            if splash is not None:
                splash.close()
            logger.exception("Jarvis startup failed")
            if backend is not None:
                backend.shutdown()
            if os.environ.get(UPDATE_HEALTH_ENV):
                sys.exit(1)
            QMessageBox.critical(None, "Jarvis", str(exc))
            sys.exit(1)

    def mark_update_ready():
        try:
            write_startup_health_marker(APP_VERSION)
        except Exception:
            logger.exception("Could not write updater startup health marker")

    QTimer.singleShot(0, mark_update_ready)
    exit_code = app.exec()
    logging.getLogger("jarvis").info("Jarvis stopped")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
