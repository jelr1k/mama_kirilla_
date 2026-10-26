from __future__ import annotations

import webbrowser
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class WebsitesPage(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._editing_id = None

        title = QLabel("Ссылки и быстрые сайты")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00e5ff;")

        hint = QLabel(
            "Здесь настраиваются сайты и сервисы для голосовых и текстовых команд «открой <название>».\n"
            "Джарвис мгновенно откроет их в браузере без обращения к нейросети."
        )
        hint.setStyleSheet("color: #94a3b8;")
        hint.setWordWrap(True)

        self.items = QListWidget()
        self.items.currentItemChanged.connect(self._load_selected)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: YouTube или Мой Проект")
        self.name_input.textChanged.connect(self._on_input_changed)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.textChanged.connect(self._on_input_changed)

        self.auto_alias_btn = QPushButton("Сгенерировать автоалиасы")
        self.auto_alias_btn.setStyleSheet(
            "background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 4px 10px;"
        )
        self.auto_alias_btn.clicked.connect(self._generate_aliases)

        self.aliases_input = QTextEdit()
        self.aliases_input.setPlaceholderText("По одному названию/алиасу на строку:\nютуб\nyoutube\nвидео")
        self.aliases_input.setMinimumHeight(140)

        form = QFormLayout()
        form.addRow("Название сайта:", self.name_input)
        form.addRow("URL адрес:", self.url_input)
        form.addRow("", self.auto_alias_btn)
        form.addRow("Голосовые имена:", self.aliases_input)

        self.new_button = QPushButton("Новый")
        self.save_button = QPushButton("Сохранить")
        self.save_button.setStyleSheet(
            "background: #0284c7; color: #ffffff; font-weight: bold; border-radius: 4px; padding: 6px 14px;"
        )
        self.test_button = QPushButton("Открыть")
        self.delete_button = QPushButton("Удалить")
        self.reset_button = QPushButton("По умолчанию")

        self.new_button.clicked.connect(self._new)
        self.save_button.clicked.connect(self._save)
        self.test_button.clicked.connect(self._test_open)
        self.delete_button.clicked.connect(self._delete)
        self.reset_button.clicked.connect(self._reset_defaults)

        buttons = QHBoxLayout()
        buttons.addWidget(self.new_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.reset_button)

        editor_box = QVBoxLayout()
        editor_title = QLabel("Параметры сайта")
        editor_title.setStyleSheet("font-weight: 600; color: #f1f5f9; font-size: 14px;")
        editor_box.addWidget(editor_title)
        editor_box.addLayout(form)
        editor_box.addLayout(buttons)
        editor_box.addStretch()

        editor_widget = QWidget()
        editor_widget.setLayout(editor_box)

        content = QHBoxLayout()
        content.addWidget(self.items, 1)
        content.addWidget(editor_widget, 2)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(10)
        root.addWidget(title)
        root.addWidget(hint)
        root.addLayout(content)

        self.refresh()
        self._new()

    def refresh(self):
        current_id = self._editing_id
        self.items.blockSignals(True)
        self.items.clear()
        for site in self.controller.get_websites():
            name = site.get("name", "Без названия")
            url = site.get("url", "")
            item = QListWidgetItem(f"{name} — {url}")
            item.setData(Qt.ItemDataRole.UserRole, site.get("id"))
            self.items.addItem(item)
        self.items.blockSignals(False)

        if current_id:
            self._select_id(current_id)

    def _select_id(self, site_id: str):
        for row in range(self.items.count()):
            item = self.items.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == site_id:
                self.items.setCurrentItem(item)
                break

    def _on_input_changed(self):
        # Если создаем новый сайт и пользователь вбивает URL, можно подсказывать автоалиасы
        pass

    def _generate_aliases(self):
        url = self.url_input.text().strip()
        name = self.name_input.text().strip()
        if not url and not name:
            QMessageBox.information(self, "Автоалиасы", "Введи сначала название или URL сайта.")
            return
        current_aliases = [x.strip() for x in self.aliases_input.toPlainText().splitlines() if x.strip()]
        auto = self.controller.generate_auto_aliases(url, name)
        merged = list(current_aliases)
        for a in auto:
            if a not in merged:
                merged.append(a)
        self.aliases_input.setPlainText("\n".join(merged))

    def _load_selected(self, current, _previous=None):
        if current is None:
            return
        site_id = current.data(Qt.ItemDataRole.UserRole)
        if not site_id:
            return
        for site in self.controller.get_websites():
            if site.get("id") == site_id:
                self._editing_id = site_id
                self.name_input.setText(site.get("name", ""))
                self.url_input.setText(site.get("url", ""))
                aliases = site.get("aliases", [])
                self.aliases_input.setPlainText("\n".join(aliases))
                break

    def _new(self):
        self._editing_id = None
        self.items.clearSelection()
        self.name_input.clear()
        self.url_input.clear()
        self.aliases_input.clear()
        self.name_input.setFocus()

    def _save(self):
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        aliases = [x.strip() for x in self.aliases_input.toPlainText().splitlines() if x.strip()]

        if not url:
            QMessageBox.warning(self, "Ошибка", "Укажи URL адрес сайта.")
            return

        if not aliases:
            aliases = self.controller.generate_auto_aliases(url, name)
            self.aliases_input.setPlainText("\n".join(aliases))

        if self._editing_id:
            self.controller.update_website(self._editing_id, name, url, aliases)
        else:
            new_item = self.controller.add_website(name, url, aliases, auto_aliases=False)
            self._editing_id = new_item.get("id")

        self.refresh()
        if self._editing_id:
            self._select_id(self._editing_id)

    def _test_open(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "URL адрес не указан.")
            return
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        try:
            webbrowser.open(url)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка открытия", f"Не удалось открыть браузер: {exc}")

    def _delete(self):
        if not self._editing_id:
            return
        name = self.name_input.text().strip() or "сайт"
        confirm = QMessageBox.question(
            self,
            "Удаление сайта",
            f"Удалить сайт «{name}» из быстрого списка?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.controller.delete_website(self._editing_id)
            self.refresh()
            self._new()

    def _reset_defaults(self):
        confirm = QMessageBox.question(
            self,
            "Сброс к стандартным",
            "Сбросить список сайтов к стандартным (YouTube, VK, GitHub, Twitch и др.)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.controller.reset_to_defaults()
            self.refresh()
            self._new()
