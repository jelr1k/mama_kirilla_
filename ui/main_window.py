from __future__ import annotations

import logging
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ui.animations import (
    AnimatedTabWidget,
    PulsingEffect,
    fade_in_window,
    animate_cards_entrance,
    install_button_micro_interactions,
)
from ui.alias_page import AliasPage
from ui.chat_page import ChatPage
from ui.commands_window import CommandsWindow
from ui.home_page import HomePage
from ui.icons import get_icon
from ui.ollama_page import OllamaPage
from ui.settings_page import SettingsPage
from ui.statistics_page import StatisticsPage
from ui.tools_page import ToolsPage
from ui.workspace_tab import WorkspaceTab
from ui.websites_page import WebsitesPage

logger = logging.getLogger("jarvis.ui")


class MainWindow(QWidget):
    settings_applied = Signal()

    def __init__(
        self,
        application_controller,
        chat_controller,
        voice_controller,
        wake_word_controller,
        dependency_controller,
        settings_controller,
        alias_controller,
        tools_controller,
        ollama_controller,
        statistics_controller,
        workspace_controller,
        websites_controller=None,
    ):
        super().__init__()
        self.application_controller = application_controller
        self.chat_controller = chat_controller
        self.voice_controller = voice_controller
        self.wake_word_detector = wake_word_controller
        self.settings_controller = settings_controller
        self.alias_controller = alias_controller
        self.tools_controller = tools_controller
        self.ollama_controller = ollama_controller
        self.statistics_controller = statistics_controller

        if websites_controller is None:
            from core.website_manager import WebsiteManager
            from presentation.websites_controller import WebsitesController

            mgr = getattr(getattr(application_controller, "app", None), "website_manager", None)
            if not isinstance(mgr, WebsiteManager):
                mgr = WebsiteManager()
            websites_controller = WebsitesController(mgr)
        self.websites_controller = websites_controller

        # Страницы интерфейса
        self.home_page = HomePage(getattr(self.settings_controller, "config", None), self.statistics_controller)
        self.home_page.navigate_requested.connect(self._on_home_navigate)
        self.home_page.command_requested.connect(self._on_home_command)

        self.chat_page = ChatPage(self.settings_controller)
        self.stats_page = StatisticsPage(statistics_controller)
        self.websites_page = WebsitesPage(self.websites_controller)
        self.alias_page = AliasPage(alias_controller)
        self.workspace_page = WorkspaceTab(workspace_controller)
        self.tools_page = ToolsPage(tools_controller)
        self.ollama_page = OllamaPage(ollama_controller, settings_controller)
        self.settings_page = SettingsPage(settings_controller)

        # Анимированный стек вкладок с векторными иконками
        self.tabs = AnimatedTabWidget()
        tab_items = (
            (self.home_page, get_icon("home", color="#00e5ff", size=16), "Главная"),
            (self.chat_page, get_icon("chat", color="#00e5ff", size=16), "Чат"),
            (self.stats_page, get_icon("cpu", color="#00e5ff", size=16), "Система"),
            (self.websites_page, get_icon("globe", color="#00e5ff", size=16), "Ссылки"),
            (self.alias_page, get_icon("tag", color="#00e5ff", size=16), "Алиасы"),
            (self.workspace_page, get_icon("folder", color="#00e5ff", size=16), "Workspace"),
            (self.tools_page, get_icon("tool", color="#00e5ff", size=16), "Инструменты"),
            (self.ollama_page, get_icon("brain", color="#00e5ff", size=16), "Ollama"),
            (self.settings_page, get_icon("settings", color="#00e5ff", size=16), "Настройки"),
        )
        for page, icon, title in tab_items:
            self.tabs.addTab(page, icon, title)

        from ui.theme import DARK_THEME_QSS
        self.setStyleSheet(DARK_THEME_QSS)

        # Верхняя панель управления (Top Bar)
        self.logo_label = QLabel("KIRIESHKA // JARVIS")
        self.logo_label.setStyleSheet("color: #00e5ff; font-weight: 800; font-size: 13px; letter-spacing: 1px;")

        self.commands_window = None
        self.commands_button = QPushButton("Команды")
        self.commands_button.setIcon(get_icon("terminal", color="#f1f5f9", size=14))
        self.commands_button.setStyleSheet(
            "background: #162032; color: #f1f5f9; border: 1px solid #24334f; border-radius: 5px; padding: 5px 12px; font-weight: 600;"
        )
        self.commands_button.clicked.connect(self.show_commands_window)

        self.cpu_badge = QPushButton("CPU: …")
        self.cpu_badge.setStyleSheet(
            "color: #00e5ff; font-weight: 600; background: #0c1424; border: 1px solid #1a2a44; border-radius: 5px; padding: 4px 10px;"
        )
        self.cpu_badge.setToolTip("Нагрузка процессора. Нажми для перехода в мониторинг")
        self.cpu_badge.clicked.connect(lambda: self.tabs.setCurrentWidget(self.stats_page))

        self.ram_badge = QPushButton("RAM: …")
        self.ram_badge.setStyleSheet(
            "color: #10b981; font-weight: 600; background: #0c1424; border: 1px solid #1a2a44; border-radius: 5px; padding: 4px 10px;"
        )
        self.ram_badge.setToolTip("Использование ОЗУ. Нажми для перехода в мониторинг")
        self.ram_badge.clicked.connect(lambda: self.tabs.setCurrentWidget(self.stats_page))

        self.statistics_controller.system_status.connect(self._on_top_system_status)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(4, 2, 4, 2)
        top_layout.setSpacing(10)
        top_layout.addWidget(self.logo_label)
        top_layout.addSpacing(10)
        top_layout.addWidget(self.cpu_badge)
        top_layout.addWidget(self.ram_badge)
        top_layout.addStretch()
        top_layout.addWidget(self.commands_button)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(8)
        root.addLayout(top_layout)
        root.addWidget(self.tabs)

        # Привязка UI-действий к чат-контроллеру
        self.chat_controller.set_ui_actions({
            "shutdown": self.shutdown,
            "minimize": self.minimize_window,
            "maximize": self.maximize_window,
            "restore": self.restore_window,
            "clear_chat": self.chat_page.clear_chat,
        })

        # Сигналы генерации чата
        self.chat_controller.chunk_received.connect(self.chat_page.on_chunk)
        self.chat_controller.direct_response.connect(self.chat_page.on_direct_response)
        self.chat_controller.rofl_response.connect(self.chat_page.on_rofl_response)
        self.chat_controller.generation_finished.connect(self.on_generation_finished)
        self.chat_controller.error.connect(self.on_error)

        self.settings_page.settings_changed.connect(self._on_settings_changed)
        self.tools_page.tools_changed.connect(self.chat_controller.refresh_tools)

        model = self.settings_controller.get("model")
        name = self.settings_controller.get("assistant_name", "JARVIS")
        wake = self.settings_controller.get("voice", {}).get("wake_word", "Jarvis")

        self.chat_page.update_model_label(model)
        self.chat_page.update_wake_word(wake)
        self.chat_page.update_assistant_name(name)
        self.chat_page.set_voice_controller(self.voice_controller)
        self.chat_page.send_requested.connect(self.chat_controller.send)
        self.chat_page.voice_recording_requested.connect(self.wake_word_detector.stop)

        self.wake_word_detector.detected.connect(self._on_wake_word_detected)
        self.wake_word_detector.recognized.connect(self.chat_page.update_wake_word_recognition)
        self.wake_word_detector.status.connect(self._on_wake_word_status)
        self.wake_word_detector.error.connect(self._on_wake_word_error)

        self.voice_controller.listening_changed.connect(self._on_voice_listening_changed)
        self.voice_controller.transcript_ready.connect(self._on_voice_command_finished)
        self.voice_controller.error.connect(self._on_voice_command_error)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        install_button_micro_interactions(self)

        self.setWindowTitle(name or "JARVIS")
        self.resize(1120, 760)

    def _on_tab_changed(self, index):
        w = self.tabs.widget(index)
        if w:
            animate_cards_entrance(w)

    def _on_home_navigate(self, target: str):
        if target == "chat":
            self.tabs.setCurrentWidget(self.chat_page)

    def _on_home_command(self, cmd: str):
        self.tabs.setCurrentWidget(self.chat_page)
        self.chat_controller.send(cmd)

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, "_has_faded_in"):
            self._has_faded_in = True
            fade_in_window(self, 240)

    def show_commands_window(self):
        if self.commands_window is None:
            self.commands_window = CommandsWindow(self.chat_controller, self)
        else:
            self.commands_window.refresh()
        self.commands_window.show()
        self.commands_window.raise_()
        self.commands_window.activateWindow()

    def _on_top_system_status(self, result):
        cpu = result.get("cpu", 0)
        ram_used = result.get("ram_used", 0)
        ram_total = result.get("ram_total", 0)
        ram_percent = result.get("ram_percent", 0)

        self.cpu_badge.setText(f"CPU: {cpu:.0f}%")
        if cpu > 80:
            self.cpu_badge.setStyleSheet(
                "color: #f43f5e; font-weight: 600; background: #261118; border: 1px solid #7f1d1d; border-radius: 5px; padding: 4px 10px;"
            )
        else:
            self.cpu_badge.setStyleSheet(
                "color: #00e5ff; font-weight: 600; background: #0c1424; border: 1px solid #1a2a44; border-radius: 5px; padding: 4px 10px;"
            )

        if ram_total:
            self.ram_badge.setText(f"RAM: {ram_used / 1024**3:.1f}/{ram_total / 1024**3:.0f} ГБ ({ram_percent:.0f}%)")
            if ram_percent > 85:
                self.ram_badge.setStyleSheet(
                    "color: #f43f5e; font-weight: 600; background: #261118; border: 1px solid #7f1d1d; border-radius: 5px; padding: 4px 10px;"
                )
            else:
                self.ram_badge.setStyleSheet(
                    "color: #10b981; font-weight: 600; background: #0c1424; border: 1px solid #1a2a44; border-radius: 5px; padding: 4px 10px;"
                )

    def _on_settings_changed(self, model, name):
        self.application_controller.apply_settings()
        self.chat_page.update_model_label(model)
        self.chat_page.update_wake_word(self.settings_controller.get("voice", {}).get("wake_word", "Jarvis"))
        self.chat_page.update_assistant_name(name)
        self.setWindowTitle(name or "JARVIS")
        self.logo_label.setText(f"{(name or 'JARVIS').upper()} // v2")
        self.chat_page.update_wake_word_recognition("")
        self.settings_applied.emit()

    def _on_wake_word_detected(self, wake_word):
        logger.info("wake_word_triggered wake_word=%r", wake_word)
        self.wake_word_detector.stop()
        self.chat_page.voice_status.setText("Голос: [wake word] услышан, говори…")
        self.chat_page.voice_status.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 12px;")
        QTimer.singleShot(120, self.voice_controller.start)

    def _on_wake_word_status(self, status):
        self.chat_page.voice_status.setText(status)

    def _on_wake_word_error(self, error):
        logger.error(error)
        self.chat_page.voice_status.setText("Голос: ошибка wake word")
        self.chat_page.voice_status.setStyleSheet("color: #f43f5e; font-weight: 700; font-size: 12px;")

    def _on_voice_listening_changed(self, listening):
        if listening:
            self.wake_word_detector.stop()

    def _on_voice_command_finished(self, text):
        QTimer.singleShot(250, self.wake_word_detector.start)

    def _on_voice_command_error(self, error):
        QTimer.singleShot(250, self.wake_word_detector.start)

    def on_generation_finished(self, stats):
        self.statistics_controller.add(stats)
        self.stats_page.refresh(stats)
        self.chat_page.finish_generation()

    def on_error(self, error):
        self.chat_page.finish_generation()
        QMessageBox.critical(self, "Ошибка", error)

    def minimize_window(self):
        self.showMinimized()

    def maximize_window(self):
        self.showMaximized()

    def restore_window(self):
        self.showNormal()

    def shutdown(self):
        self.hide()
        self.application_controller.shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event):
        self.hide()
        event.accept()
        self.application_controller.shutdown()
        super().closeEvent(event)
