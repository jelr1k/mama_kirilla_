from __future__ import annotations

import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui_archive.icons import get_icon

logger = logging.getLogger("jarvis.ui.home")


class HomePage(QWidget):
    """Главная обзорная страница (Dashboard) JARVIS."""

    navigate_requested = Signal(str)
    command_requested = Signal(str)

    def __init__(
        self,
        config_manager,
        statistics_controller,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.config = config_manager
        self.stats_controller = statistics_controller

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 1. Приветственный баннер
        banner = self._create_banner()
        layout.addWidget(banner)

        # 2. Карточки статуса
        status_grid = self._create_status_cards()
        layout.addLayout(status_grid)

        # 3. Быстрые действия
        actions_box = self._create_quick_actions()
        layout.addWidget(actions_box)

        # 4. Подсказки и частые команды
        hints_box = self._create_quick_hints()
        layout.addWidget(hints_box)

        layout.addStretch()
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

        # Подписка на обновление статуса системы
        if self.stats_controller:
            self.stats_controller.system_status.connect(self._on_system_status)

    def _create_banner(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("homeBanner")
        frame.setStyleSheet("""
            #homeBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1c30, stop:1 #14223d);
                border: 1px solid #1e3a5f;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        h_layout = QHBoxLayout(frame)
        h_layout.setContentsMargins(16, 12, 16, 12)

        v_text = QVBoxLayout()
        title = QLabel("JARVIS // KIRIESHKA v2")
        title.setStyleSheet("color: #00e5ff; font-size: 18px; font-weight: 800; letter-spacing: 1px;")
        subtitle = QLabel("Локальный персональный ассистент • Windows 11 • Автономная работа")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 4px;")
        v_text.addWidget(title)
        v_text.addWidget(subtitle)
        h_layout.addLayout(v_text)

        h_layout.addStretch()

        btn_chat = QPushButton("Перейти в чат")
        btn_chat.setIcon(get_icon("chat", color="#0f172a", size=16))
        btn_chat.setStyleSheet("""
            QPushButton {
                background-color: #00e5ff;
                color: #0f172a;
                font-weight: 700;
                font-size: 13px;
                border-radius: 8px;
                padding: 8px 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #38bdf8;
            }
        """)
        btn_chat.clicked.connect(lambda: self.navigate_requested.emit("chat"))
        h_layout.addWidget(btn_chat)

        return frame

    def _create_status_cards(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(12)

        model_name = self.config.get("model", "qwen2.5:7b") if self.config else "Ollama"
        voice_cfg = self.config.get("voice", {}) if self.config else {}
        whisper_m = voice_cfg.get("model", "small")
        wake_enabled = voice_cfg.get("wake_word_enabled", True)

        self.card_model_val = QLabel(str(model_name))
        self.card_voice_val = QLabel(f"Whisper ({whisper_m}) • Vosk {'[ВКЛ]' if wake_enabled else '[ВЫКЛ]'}")
        self.card_cpu_val = QLabel("CPU: опрос…")
        self.card_ram_val = QLabel("RAM: опрос…")

        cards = [
            ("Модель нейросети", self.card_model_val, "brain", "#a855f7"),
            ("Голосовой модуль", self.card_voice_val, "mic", "#00e5ff"),
            ("Процессор (CPU)", self.card_cpu_val, "cpu", "#10b981"),
            ("Оперативная память", self.card_ram_val, "zap", "#f59e0b"),
        ]

        for idx, (title_text, val_label, icon_name, accent) in enumerate(cards):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #0f1728;
                    border: 1px solid #1e293b;
                    border-radius: 10px;
                    padding: 10px;
                }}
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(12, 10, 12, 10)
            c_layout.setSpacing(4)

            top_row = QHBoxLayout()
            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_icon(icon_name, color=accent, size=16).pixmap(16, 16))
            lbl_title = QLabel(title_text)
            lbl_title.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase;")
            top_row.addWidget(icon_lbl)
            top_row.addWidget(lbl_title)
            top_row.addStretch()

            val_label.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: 700;")
            val_label.setWordWrap(True)

            c_layout.addLayout(top_row)
            c_layout.addWidget(val_label)

            row = idx // 2
            col = idx % 2
            grid.addWidget(card, row, col)

        return grid

    def _create_quick_actions(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0f1728;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QLabel("БЫСТРЫЕ ДЕЙСТВИЯ")
        header.setStyleSheet("color: #00e5ff; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(header)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        actions = [
            ("Скриншот экрана", "camera", "сделай скриншот"),
            ("Открыть загрузки", "folder", "открой загрузки"),
            ("Текущее время", "clock", "сколько времени"),
            ("Заблокировать ПК", "lock", "заблокируй пк"),
            ("Очистить чат", "trash", "очисти чат"),
        ]

        for label_text, icon_name, cmd in actions:
            btn = QPushButton(f"  {label_text}")
            btn.setIcon(get_icon(icon_name, color="#00e5ff", size=15))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #162032;
                    color: #cbd5e1;
                    font-size: 12px;
                    font-weight: 600;
                    border: 1px solid #22324b;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #1e2e47;
                    border-color: #00e5ff;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda _, c=cmd: self.command_requested.emit(c))
            btn_row.addWidget(btn)

        layout.addLayout(btn_row)
        return frame

    def _create_quick_hints(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #0f1728;
                border: 1px solid #1e293b;
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QLabel("ГОЛОСОВЫЕ КОМАНДЫ (НАЖМИ ЧТОБЫ ВЫПОЛНИТЬ)")
        header.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(header)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(8)

        chips = [
            "телеметрия",
            "сделай погромче",
            "открой рабочий стол",
            "пауза",
            "следующий трек",
            "открой ютуб",
        ]

        for chip_text in chips:
            chip_btn = QPushButton(chip_text)
            chip_btn.setStyleSheet("""
                QPushButton {
                    background-color: #131b2e;
                    color: #00e5ff;
                    font-size: 11px;
                    font-weight: 500;
                    border: 1px dashed #1e3a5f;
                    border-radius: 6px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #1a2742;
                    border-style: solid;
                    color: #ffffff;
                }
            """)
            chip_btn.clicked.connect(lambda _, c=chip_text: self.command_requested.emit(c))
            h_layout.addWidget(chip_btn)

        h_layout.addStretch()
        layout.addLayout(h_layout)
        return frame

    def _on_system_status(self, data: dict):
        if not data:
            return
        cpu = data.get("cpu", 0)
        ram_used = data.get("ram_used", 0)
        ram_total = data.get("ram_total", 0)
        ram_percent = data.get("ram_percent", 0)

        self.card_cpu_val.setText(f"{cpu:.0f}%" if cpu else "Норма")
        if ram_total:
            self.card_ram_val.setText(f"{ram_used/1024**3:.1f} / {ram_total/1024**3:.1f} ГБ ({ram_percent:.0f}%)")
