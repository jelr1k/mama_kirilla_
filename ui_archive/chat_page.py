from __future__ import annotations

from html import escape
import re

from PySide6.QtCore import Signal, QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ui.animations import PulsingEffect, SmoothScroller, ThinkingIndicator, install_button_micro_interactions
from ui.icons import get_icon


class ChatPage(QWidget):
    send_requested = Signal(str, bool)
    voice_recording_requested = Signal()

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.answer = ""
        self.thinking = ""
        self.pending_answer = ""
        self.pending_thinking = ""
        self.thinking_started = False
        self.answer_started = False
        self.assistant_name = config.get("assistant_name", "JARVIS")

        # --- Верхний статус-HUD ---
        self.hud_frame = QFrame()
        self.hud_frame.setStyleSheet(
            "QFrame { background-color: #0b111e; border: 1px solid #1a273e; border-radius: 8px; padding: 4px 8px; }"
        )
        hud_layout = QHBoxLayout(self.hud_frame)
        hud_layout.setContentsMargins(6, 4, 6, 4)
        hud_layout.setSpacing(10)

        self.voice_status = QLabel("Голос: готов")
        self.voice_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")

        self.model_label = QLabel()
        self.model_label.setStyleSheet("color: #00e5ff; font-size: 12px; font-weight: 500;")

        self.wake_word_label = QLabel()
        self.wake_word_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        self.wake_word_recognition = QLabel("Vosk: —")
        self.wake_word_recognition.setStyleSheet("color: #64748b; font-size: 11.5px;")
        self.wake_word_recognition.setToolTip(
            "Последний текст, который распознал Vosk во время ожидания wake word."
        )

        self.clear_chat_button = QPushButton("Очистить")
        self.clear_chat_button.setProperty("chip", "true")
        self.clear_chat_button.setIcon(get_icon("trash_alt", color="#94a3b8", size=13))
        self.clear_chat_button.setToolTip("Очистить историю сообщений на экране")
        self.clear_chat_button.clicked.connect(self.clear_chat)

        hud_layout.addWidget(self.voice_status)
        hud_layout.addWidget(self.model_label)
        hud_layout.addWidget(self.wake_word_label)
        hud_layout.addWidget(self.wake_word_recognition, 1)
        hud_layout.addWidget(self.clear_chat_button)

        # --- Основное окно чата ---
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet(
            "QTextEdit { background-color: #090e18; border: 1px solid #162238; border-radius: 8px; padding: 10px; font-size: 13.5px; }"
        )

        # --- Панель быстрых подсказок (чипы с векторными иконками) ---
        chips_frame = QFrame()
        chips_layout = QHBoxLayout(chips_frame)
        chips_layout.setContentsMargins(2, 2, 2, 2)
        chips_layout.setSpacing(6)

        quick_prompts = [
            ("Нагрузка", "телеметрия", "cpu"),
            ("Скриншот", "сделай скриншот", "camera"),
            ("Корзина", "очисти корзину", "trash"),
            ("Время", "сколько времени", "clock"),
            ("YouTube", "открой ютуб", "globe"),
            ("Загрузки", "открой загрузки", "folder"),
            ("Блок ПК", "заблокируй пк", "lock"),
            ("Выгрузить", "выгрузи модель", "zap"),
        ]

        for label, cmd, icon_name in quick_prompts:
            btn = QPushButton(label)
            btn.setProperty("chip", "true")
            btn.setIcon(get_icon(icon_name, color="#00e5ff", size=13))
            btn.clicked.connect(lambda checked=False, c=cmd: self._quick_send(c))
            chips_layout.addWidget(btn)
        chips_layout.addStretch()

        # --- Панель ввода ---
        self.input = QTextEdit()
        self.input.setPlaceholderText("Спроси что угодно, введи команду или используй голосовой ввод…")
        self.input.setFixedHeight(75)

        self.send_button = QPushButton("Отправить")
        self.send_button.setIcon(get_icon("zap", color="#ffffff", size=13))
        self.send_button.setStyleSheet(
            "QPushButton { background-color: #0088cc; color: #ffffff; border: 1px solid #00aaff; border-radius: 6px; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0099e6; }"
            "QPushButton:pressed { background-color: #006699; }"
        )
        self.send_button.clicked.connect(self.send)

        self.thinking_button = QPushButton("Размышление")
        self.thinking_button.setCheckable(True)
        self.thinking_button.setStyleSheet(
            "QPushButton:checked { background-color: #3b0764; border-color: #a855f7; color: #e9d5ff; font-weight: 600; }"
        )
        self.thinking_button.setToolTip("Включает режим раздумывания для запросов, пока кнопка активна. Состояние не сохраняется.")

        self.voice_button = QPushButton("Голосовой ввод")
        self.voice_button.setToolTip("Нажми один раз, говори, затем нажми ещё раз для остановки")
        self.voice_button.setCheckable(True)
        self.voice_button.clicked.connect(self._voice_clicked)

        bottom = QHBoxLayout()
        bottom.addWidget(self.input, 1)

        btn_box = QVBoxLayout()
        btn_box.setSpacing(4)
        top_btn_row = QHBoxLayout()
        top_btn_row.addWidget(self.thinking_button)
        top_btn_row.addWidget(self.voice_button)
        btn_box.addLayout(top_btn_row)
        btn_box.addWidget(self.send_button)
        bottom.addLayout(btn_box)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        layout.addWidget(self.hud_frame)
        layout.addWidget(self.chat, 1)
        self.thinking_indicator = ThinkingIndicator(self)
        layout.addWidget(self.thinking_indicator)
        layout.addWidget(chips_frame)
        layout.addLayout(bottom)
        self.input.installEventFilter(self)

        self.stream_timer = QTimer(self)
        self.stream_timer.timeout.connect(self.flush_stream)
        self.stream_timer.start(33)
        self.voice_controller = None
        self.scroller = SmoothScroller(self.chat.verticalScrollBar(), duration_ms=130)
        self.voice_pulse = PulsingEffect(self.voice_button, min_opacity=0.45, max_opacity=1.0, period_ms=1000)
        self.status_pulse = PulsingEffect(self.voice_status, min_opacity=0.5, max_opacity=1.0, period_ms=1000)
        install_button_micro_interactions(self)

        self._show_welcome_message()

    def _show_welcome_message(self):
        welcome_html = (
            "<div style='margin: 8px 0; color: #475569; font-size: 12px;'>"
            "<b>Кириешка v2</b> готова к работе. Введите команду, выберите быстрый сценарий или нажмите «Голосовой ввод»."
            "</div>"
        )
        self.chat.append(welcome_html)

    def clear_chat(self):
        """Очищает историю переписки в окне чата."""
        self.chat.clear()
        self.answer = self.thinking = ""
        self.pending_answer = self.pending_thinking = ""
        self.thinking_started = self.answer_started = False
        self._show_welcome_message()

    def _quick_send(self, command_text: str):
        self._send_text(command_text, clear_input=True)

    def set_voice_controller(self, controller):
        self.voice_controller = controller
        controller.listening_changed.connect(self.on_voice_listening_changed)
        controller.transcribing_changed.connect(self.on_voice_transcribing_changed)
        controller.transcript_ready.connect(self.on_voice_transcript)
        controller.error.connect(self.on_voice_error)

    def update_model_label(self, model):
        self.model_label.setText(f"Модель: {model}")

    def update_wake_word(self, wake_word):
        self.wake_word_label.setText(f"Wake word: {wake_word}")

    def update_wake_word_recognition(self, text):
        text = " ".join(str(text or "").split())
        if text:
            words = text.split()
            text = " ".join(words[-8:])
            self.wake_word_recognition.setText(f"Vosk: «{text}»")
        else:
            self.wake_word_recognition.setText("Vosk: —")

    def update_assistant_name(self, name):
        self.assistant_name = name.strip() or "JARVIS"

    def update_settings(self, model, assistant_name):
        self.update_model_label(model)
        self.update_assistant_name(assistant_name)

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    return False
                self.send()
                return True
        return super().eventFilter(obj, event)

    def _voice_clicked(self):
        if self.voice_controller is None or self.voice_controller.transcribing():
            self.voice_button.setChecked(False)
            return
        if self.voice_controller.is_recording:
            self.voice_controller.stop()
        else:
            self.voice_recording_requested.emit()
            self.voice_controller.start()

    def send(self):
        self._send_text(self.input.toPlainText().strip())
        self.input.clear()

    def send_voice_text(self, text):
        self._send_text(text, clear_input=False)

    def _send_text(self, text, clear_input=True):
        text = text.strip()
        if not text:
            return

        bubble_html = (
            f"<div style='margin: 8px 0; background-color: #121e33; border: 1px solid #1e3557; "
            f"border-left: 3px solid #00e5ff; border-radius: 8px; padding: 8px 12px;'>"
            f"<span style='color: #00e5ff; font-weight: 700; font-size: 11px; text-transform: uppercase;'>Вы</span>"
            f"<div style='color: #f1f5f9; margin-top: 4px; font-size: 13.5px; line-height: 1.4;'>{escape(text)}</div>"
            f"</div>"
        )
        self.chat.append(bubble_html)

        if clear_input:
            self.input.clear()
        self.answer = self.thinking = ""
        self.pending_answer = self.pending_thinking = ""
        self.thinking_started = self.answer_started = False
        self.send_button.setEnabled(False)
        self.thinking_indicator.start()
        self.send_requested.emit(text, self.thinking_button.isChecked())

    def on_voice_listening_changed(self, listening):
        self.voice_button.setChecked(listening)
        if listening:
            self.voice_status.setText("Голос: [REC] слушаю…")
            self.voice_status.setStyleSheet("color: #f43f5e; font-weight: 700; font-size: 12px;")
            self.voice_button.setText("Остановить")
            self.voice_pulse.start()
            self.status_pulse.start()
        else:
            self.voice_status.setText("Голос: обрабатываю…")
            self.voice_status.setStyleSheet("color: #00e5ff; font-weight: 600; font-size: 12px;")
            self.voice_button.setText("Голосовой ввод")
            self.voice_pulse.stop()
            self.status_pulse.start()

    def on_voice_transcribing_changed(self, transcribing):
        if transcribing:
            self.voice_status.setText("Голос: [AI] распознаю…")
            self.voice_status.setStyleSheet("color: #a855f7; font-weight: 600; font-size: 12px;")
            self.voice_button.setChecked(False)
            self.voice_button.setEnabled(False)
            self.status_pulse.start()
        else:
            self.voice_button.setEnabled(True)
            self.voice_button.setChecked(False)
            self.status_pulse.stop()
            if self.voice_status.text().startswith("Голос: [AI]"):
                self.voice_status.setText("Голос: готов")
                self.voice_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")

    def on_voice_transcript(self, text):
        self.voice_status.setText(f"Голос: «{text}»")
        self.send_voice_text(text)

    def on_voice_error(self, error):
        self.voice_pulse.stop()
        self.status_pulse.stop()
        self.voice_status.setText("Голос: ошибка")
        self.voice_status.setStyleSheet("color: #f43f5e; font-weight: 700; font-size: 12px;")
        self.voice_button.setChecked(False)
        self.voice_button.setEnabled(True)
        err_html = (
            f"<div style='margin: 6px 0; background-color: #261118; border-left: 3px solid #f43f5e; border-radius: 6px; padding: 6px 10px; color: #fda4af;'>"
            f"<b>Ошибка:</b> {escape(error)}</div>"
        )
        self.chat.append(err_html)

    def on_direct_response(self, text):
        formatted = escape(text).replace("\n", "<br>")
        bubble_html = (
            f"<div style='margin: 8px 0; background-color: #0c1424; border: 1px solid #1a273e; "
            f"border-left: 3px solid #10b981; border-radius: 8px; padding: 8px 12px;'>"
            f"<span style='color: #10b981; font-weight: 700; font-size: 11px; text-transform: uppercase;'>{escape(self.assistant_name)}</span>"
            f"<div style='color: #e2e8f0; margin-top: 4px; font-size: 13.5px; line-height: 1.45;'>{formatted}</div>"
            f"</div>"
        )
        self.chat.append(bubble_html)
        self.thinking_indicator.stop()
        self.scroller.scroll_to_bottom()
        self.send_button.setEnabled(True)
        self.input.setFocus()

    def on_rofl_response(self, text):
        """Показывает шуточную реплику между целыми фрагментами ответа."""
        self.flush_stream()
        rofl_html = (
            f"<div style='margin: 4px 0 8px 14px; background-color: #1a1226; border-left: 3px solid #ec4899; "
            f"border-radius: 6px; padding: 6px 12px; font-style: italic; color: #f472b6; font-size: 12.5px;'>"
            f"<b>{escape(self.assistant_name)}:</b> {escape(text)}"
            f"</div>"
        )
        self.chat.append(rofl_html)

    def on_chunk(self, chunk):
        if chunk.thinking:
            self.thinking += chunk.thinking
            self.pending_thinking += chunk.thinking
        if chunk.text:
            self.answer += chunk.text
            self.pending_answer += chunk.text

    def flush_stream(self):
        if not self.pending_thinking and not self.pending_answer:
            return

        scrollbar = self.chat.verticalScrollBar()
        previous_value = scrollbar.value()
        was_at_bottom = previous_value >= scrollbar.maximum() - 2

        if self.pending_thinking:
            if not self.thinking_started:
                header_html = (
                    f"<div style='margin-top: 8px; color: #a855f7; font-weight: 700; font-size: 11px;'>"
                    f"{escape(self.assistant_name)} (РАЗМЫШЛЕНИЯ):</div>"
                    f"<div style='background-color: #080c14; border: 1px dashed #334155; border-radius: 6px; "
                    f"padding: 6px 10px; color: #94a3b8; font-family: Consolas, monospace; font-size: 12px; margin-bottom: 6px;'>"
                )
                self.chat.append(header_html)
                self.thinking_started = True

            cursor = self.chat.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(self.pending_thinking)
            self.pending_thinking = ""

        if self.pending_answer:
            if not self.answer_started:
                if self.thinking_started:
                    self.chat.append("</div>")
                header_html = (
                    f"<div style='margin-top: 8px; color: #10b981; font-weight: 700; font-size: 11px; text-transform: uppercase;'>"
                    f"{escape(self.assistant_name)}:</div>"
                )
                self.chat.append(header_html)
                self.answer_started = True

            cursor = self.chat.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(self.pending_answer)
            self.pending_answer = ""

        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(previous_value)

    def finish_generation(self):
        self.flush_stream()
        self.thinking_indicator.stop()
        self.status_pulse.stop()
        self.voice_pulse.stop()
        self.send_button.setEnabled(True)
        if self.voice_controller is None or not self.voice_controller.transcribing():
            self.voice_status.setText("Голос: готов")
            self.voice_status.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")
        self.input.setFocus()
