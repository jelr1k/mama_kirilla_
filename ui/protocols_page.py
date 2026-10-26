from __future__ import annotations

from typing import Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from presentation.protocols_controller import ProtocolsController


class ProtocolsPage(QWidget):
    """Страница управления фирменными и пользовательскими протоколами JARVIS."""

    def __init__(self, controller: ProtocolsController):
        super().__init__()
        self.controller = controller
        self._current_protocol_id: str | None = None
        self._is_updating_ui = False

        self._setup_ui()
        self._connect_signals()
        self._reload_profiles()
        self._reload_protocols_list()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Заголовок
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Протоколы и сценарии JARVIS")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00e5ff;")
        hint = QLabel(
            "Создание и настройка сценариев автоматизации для разных людей и задач: "
            "какие программы запускать, что закрывать и какими фразами активировать."
        )
        hint.setStyleSheet("color: #94a3b8;")
        hint.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(hint)
        header_layout.addLayout(title_box)

        # Выбор профиля человека/пользователя
        profile_box = QHBoxLayout()
        profile_lbl = QLabel("Профиль:")
        profile_lbl.setStyleSheet("font-weight: 600; color: #f1f5f9;")
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(160)

        self.btn_add_profile = QPushButton("+ Профиль")
        self.btn_add_profile.setStyleSheet("background: #1e293b; color: #38bdf8; border: 1px solid #0284c7; border-radius: 4px; padding: 4px 10px;")
        self.btn_del_profile = QPushButton("Удалить")
        self.btn_del_profile.setStyleSheet("background: #271216; color: #fb7185; border: 1px solid #881337; border-radius: 4px; padding: 4px 8px;")

        profile_box.addWidget(profile_lbl)
        profile_box.addWidget(self.profile_combo)
        profile_box.addWidget(self.btn_add_profile)
        profile_box.addWidget(self.btn_del_profile)
        header_layout.addStretch()
        header_layout.addLayout(profile_box)
        main_layout.addLayout(header_layout)

        # 2. Разделитель: Слева список, справа редактор
        splitter = QSplitter(Qt.Horizontal)

        # Левая панель: Список протоколов
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        list_label = QLabel("Список протоколов:")
        list_label.setStyleSheet("font-weight: 600; color: #cbd5e1;")
        self.protocols_list = QListWidget()
        self.btn_create_protocol = QPushButton("+ Новый протокол")
        self.btn_create_protocol.setStyleSheet("background: #0284c7; color: #ffffff; font-weight: 600; padding: 8px; border-radius: 5px;")

        left_layout.addWidget(list_label)
        left_layout.addWidget(self.protocols_list)
        left_layout.addWidget(self.btn_create_protocol)
        splitter.addWidget(left_widget)

        # Правая панель: Детальный редактор (с полосой прокрутки)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_widget = QWidget()
        self.editor_layout = QVBoxLayout(right_widget)
        self.editor_layout.setContentsMargins(12, 8, 12, 12)
        self.editor_layout.setSpacing(12)

        # Базовая информация
        info_group = QGroupBox("Параметры протокола")
        info_form = QFormLayout(info_group)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Доброе утро, Стрим, Работа...")
        self.phrases_input = QLineEdit()
        self.phrases_input.setPlaceholderText("Фразы активации через запятую (например: стрим, протокол стрим, погнали стримить)")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Краткое описание, что делает этот протокол...")
        self.desc_input.setMaximumHeight(65)

        info_form.addRow("Название:", self.name_input)
        info_form.addRow("Фразы вызова:", self.phrases_input)
        info_form.addRow("Описание:", self.desc_input)
        self.editor_layout.addWidget(info_group)

        # Запуск программ
        open_group = QGroupBox("Запуск программ (открыть)")
        open_vbox = QVBoxLayout(open_group)
        open_vbox.setSpacing(8)

        self.open_apps_input = QLineEdit()
        self.open_apps_input.setPlaceholderText("Ключи программ или пути к .exe (например: opera, discord, steam)")
        open_vbox.addWidget(self.open_apps_input)

        # Быстрые кнопки добавления популярных программ
        quick_apps_layout = QHBoxLayout()
        quick_label = QLabel("Быстрое добавление:")
        quick_label.setStyleSheet("color: #64748b; font-size: 11px;")
        quick_apps_layout.addWidget(quick_label)
        for app_title, app_key in (
            ("Opera GX", "opera"),
            ("Discord", "discord"),
            ("Steam", "steam"),
            ("Antigravity", "antigravity"),
            ("Unlocker", "unlocker"),
            ("Telegram", "telegram"),
            ("Spotify", "spotify"),
        ):
            btn = QPushButton(f"+ {app_title}")
            btn.setStyleSheet("background: #1e293b; color: #94a3b8; font-size: 11px; padding: 2px 6px; border-radius: 3px;")
            btn.clicked.connect(lambda _, k=app_key: self._add_app_to_open_list(k))
            quick_apps_layout.addWidget(btn)
        quick_apps_layout.addStretch()

        self.btn_browse_exe = QPushButton("Обзор файла (.exe)...")
        self.btn_browse_exe.setStyleSheet("background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 3px 8px; border-radius: 4px;")
        self.btn_browse_exe.clicked.connect(self._browse_executable)
        quick_apps_layout.addWidget(self.btn_browse_exe)
        open_vbox.addLayout(quick_apps_layout)
        self.editor_layout.addWidget(open_group)

        # Закрытие программ
        close_group = QGroupBox("Закрытие программ")
        close_form = QFormLayout(close_group)
        self.close_mode_combo = QComboBox()
        self.close_mode_combo.addItem("Не закрывать программы", "none")
        self.close_mode_combo.addItem("Закрывать запущенные игры Steam (обои Wallpaper Engine сохраняются)", "steam_games")
        self.close_mode_combo.addItem("Режим Кино (закрыть игры и сторонний софт, Discord и Steam оставить)", "cinema")
        self.close_mode_combo.addItem("Режим Игра (закрыть браузер и программы, оставить только Steam и Discord)", "game")

        self.custom_close_input = QLineEdit()
        self.custom_close_input.setPlaceholderText("Дополнительные программы для закрытия (через запятую)...")
        close_form.addRow("Режим закрытия:", self.close_mode_combo)
        close_form.addRow("Доп. закрытие:", self.custom_close_input)
        self.editor_layout.addWidget(close_group)

        # Звук и действия Windows
        sys_group = QGroupBox("Звук и системные действия")
        sys_vbox = QVBoxLayout(sys_group)
        vol_layout = QHBoxLayout()
        vol_label = QLabel("Громкость Windows:")
        self.volume_mode_combo = QComboBox()
        self.volume_mode_combo.addItem("Не изменять", "none")
        self.volume_mode_combo.addItem("100% (Максимум)", "max")
        self.volume_mode_combo.addItem("Без звука (Mute)", "mute")
        vol_layout.addWidget(vol_label)
        vol_layout.addWidget(self.volume_mode_combo)
        vol_layout.addStretch()
        sys_vbox.addLayout(vol_layout)

        self.chk_pause_media = QCheckBox("Поставить музыку / видео на паузу")
        self.chk_lock_screen = QCheckBox("Заблокировать компьютер (Win + L)")
        self.chk_clean_recycle = QCheckBox("Очистить корзину Windows")
        self.chk_briefing = QCheckBox("Озвучить утренний брифинг (время, день недели и погода вслух)")
        sys_vbox.addWidget(self.chk_pause_media)
        sys_vbox.addWidget(self.chk_lock_screen)
        sys_vbox.addWidget(self.chk_clean_recycle)
        sys_vbox.addWidget(self.chk_briefing)
        self.editor_layout.addWidget(sys_group)

        # Ответ Джарвиса
        resp_group = QGroupBox("Ответ Джарвиса")
        resp_vbox = QVBoxLayout(resp_group)
        self.response_input = QLineEdit()
        self.response_input.setPlaceholderText("Оставь пустым — и JARVIS придумает остроумный ответ сам (через ИИ)...")
        resp_hint = QLabel("Если поле пустое, JARVIS придумывает ответ сам под ситуацию через нейросеть или фирменные реплики Старка.")
        resp_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        resp_vbox.addWidget(self.response_input)
        resp_vbox.addWidget(resp_hint)
        self.editor_layout.addWidget(resp_group)

        # Кнопки действий
        actions_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить протокол")
        self.btn_save.setStyleSheet("background: #0284c7; color: white; font-weight: bold; padding: 9px 18px; border-radius: 5px;")
        self.btn_test = QPushButton("Запустить сейчас (Тест)")
        self.btn_test.setStyleSheet("background: #059669; color: white; font-weight: bold; padding: 9px 16px; border-radius: 5px;")
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.setStyleSheet("background: #991b1b; color: white; padding: 9px 14px; border-radius: 5px;")

        actions_layout.addWidget(self.btn_save)
        actions_layout.addWidget(self.btn_test)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_delete)
        self.editor_layout.addLayout(actions_layout)

        right_scroll.setWidget(right_widget)
        splitter.addWidget(right_scroll)
        splitter.setSizes([260, 640])
        main_layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        self.profile_combo.currentIndexChanged.connect(self._on_profile_selected)
        self.btn_add_profile.clicked.connect(self._on_add_profile_clicked)
        self.btn_del_profile.clicked.connect(self._on_delete_profile_clicked)
        self.protocols_list.currentItemChanged.connect(self._on_protocol_selected)
        self.btn_create_protocol.clicked.connect(self._on_create_protocol_clicked)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_test.clicked.connect(self._on_test_clicked)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        self.controller.changed.connect(self._on_controller_changed)

    def _reload_profiles(self) -> None:
        self._is_updating_ui = True
        try:
            self.profile_combo.clear()
            profiles = self.controller.list_profiles()
            active_id = self.controller.get_active_profile()
            for pid, pname in profiles.items():
                self.profile_combo.addItem(pname, pid)
            idx = self.profile_combo.findData(active_id)
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
        finally:
            self._is_updating_ui = False

    def _reload_protocols_list(self) -> None:
        self._is_updating_ui = True
        try:
            self.protocols_list.clear()
            protocols = self.controller.get_protocols()
            for p in protocols:
                item = QListWidgetItem(p.get("name", "Без названия"))
                item.setData(Qt.UserRole, p.get("id"))
                self.protocols_list.addItem(item)

            if protocols:
                self.protocols_list.setCurrentRow(0)
            else:
                self._clear_editor()
        finally:
            self._is_updating_ui = False
            self._load_selected_protocol()

    def _load_selected_protocol(self) -> None:
        current_item = self.protocols_list.currentItem()
        if not current_item:
            self._clear_editor()
            return

        proto_id = current_item.data(Qt.UserRole)
        proto = self.controller.get_protocol(proto_id)
        if not proto:
            return

        self._current_protocol_id = proto_id
        self.name_input.setText(proto.get("name", ""))
        self.phrases_input.setText(", ".join(proto.get("phrases", [])))
        self.desc_input.setText(proto.get("description", ""))
        self.open_apps_input.setText(", ".join(proto.get("open_apps", [])))

        close_mode = proto.get("close_mode", "none")
        idx = self.close_mode_combo.findData(close_mode)
        self.close_mode_combo.setCurrentIndex(max(0, idx))
        self.custom_close_input.setText(", ".join(proto.get("close_apps", [])))

        vol_mode = proto.get("volume_mode", "none")
        vol_idx = self.volume_mode_combo.findData(vol_mode)
        self.volume_mode_combo.setCurrentIndex(max(0, vol_idx))

        self.chk_pause_media.setChecked(bool(proto.get("pause_media")))
        self.chk_lock_screen.setChecked(bool(proto.get("lock_screen")))
        self.chk_clean_recycle.setChecked(bool(proto.get("clean_recycle_bin")))
        self.chk_briefing.setChecked(bool(proto.get("briefing")))
        self.response_input.setText(proto.get("response_text", ""))

    def _clear_editor(self) -> None:
        self._current_protocol_id = None
        self.name_input.clear()
        self.phrases_input.clear()
        self.desc_input.clear()
        self.open_apps_input.clear()
        self.close_mode_combo.setCurrentIndex(0)
        self.custom_close_input.clear()
        self.volume_mode_combo.setCurrentIndex(0)
        self.chk_pause_media.setChecked(False)
        self.chk_lock_screen.setChecked(False)
        self.chk_clean_recycle.setChecked(False)
        self.chk_briefing.setChecked(False)
        self.response_input.clear()

    def _add_app_to_open_list(self, app_key: str) -> None:
        current_text = self.open_apps_input.text().strip()
        items = [x.strip() for x in current_text.split(",") if x.strip()]
        if app_key not in items:
            items.append(app_key)
            self.open_apps_input.setText(", ".join(items))

    def _browse_executable(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите исполняемый файл или ярлык", "", "Исполняемые файлы (*.exe *.lnk);;Все файлы (*.*)"
        )
        if file_path:
            self._add_app_to_open_list(file_path)

    def _on_profile_selected(self, index: int) -> None:
        if self._is_updating_ui or index < 0:
            return
        pid = self.profile_combo.itemData(index)
        if pid:
            self.controller.set_active_profile(pid)
            self._reload_protocols_list()

    def _on_add_profile_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый профиль", "Введите имя профиля (например: Кирилл, Рабочий, Стрим):")
        if ok and name.strip():
            self.controller.add_profile(name.strip())
            self._reload_profiles()
            self._reload_protocols_list()

    def _on_delete_profile_clicked(self) -> None:
        profiles = self.controller.list_profiles()
        if len(profiles) <= 1:
            QMessageBox.information(self, "Профиль", "Нельзя удалить единственный оставшийся профиль.")
            return
        active_id = self.controller.get_active_profile()
        active_name = profiles.get(active_id, active_id)
        reply = QMessageBox.question(
            self, "Удаление профиля", f"Вы уверены, что хотите удалить профиль «{active_name}»?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.controller.delete_profile(active_id)
            self._reload_profiles()
            self._reload_protocols_list()

    def _on_protocol_selected(self) -> None:
        if not self._is_updating_ui:
            self._load_selected_protocol()

    def _on_create_protocol_clicked(self) -> None:
        self.protocols_list.clearSelection()
        self._clear_editor()
        self.name_input.setText("Новый протокол")
        self.phrases_input.setText("команда, протокол новый")
        self.name_input.setFocus()
        self.name_input.selectAll()

    def _on_save_clicked(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Укажите название протокола.")
            return

        phrases_raw = self.phrases_input.text().strip()
        phrases = [p.strip().lower() for p in phrases_raw.split(",") if p.strip()]
        if not phrases:
            QMessageBox.warning(self, "Ошибка", "Укажите хотя бы одну фразу активации.")
            return

        open_raw = self.open_apps_input.text().strip()
        open_apps = [a.strip() for a in open_raw.split(",") if a.strip()]

        close_raw = self.custom_close_input.text().strip()
        close_apps = [c.strip() for c in close_raw.split(",") if c.strip()]

        data = {
            "id": self._current_protocol_id or "",
            "name": name,
            "description": self.desc_input.toPlainText().strip(),
            "phrases": phrases,
            "open_apps": open_apps,
            "close_mode": self.close_mode_combo.currentData(),
            "close_apps": close_apps,
            "volume_mode": self.volume_mode_combo.currentData(),
            "pause_media": self.chk_pause_media.isChecked(),
            "lock_screen": self.chk_lock_screen.isChecked(),
            "clean_recycle_bin": self.chk_clean_recycle.isChecked(),
            "briefing": self.chk_briefing.isChecked(),
            "response_text": self.response_input.text().strip(),
        }

        saved_id = self.controller.save_protocol(data)
        self._reload_protocols_list()

        # Выделить сохраненный
        for idx in range(self.protocols_list.count()):
            item = self.protocols_list.item(idx)
            if item.data(Qt.UserRole) == saved_id:
                self.protocols_list.setCurrentItem(item)
                break

        QMessageBox.information(self, "Сохранено", f"Протокол «{name}» успешно сохранен и готов к использованию!")

    def _on_test_clicked(self) -> None:
        name = self.name_input.text().strip() or "Протокол"
        data = {
            "id": self._current_protocol_id or "temp",
            "name": name,
            "description": self.desc_input.toPlainText().strip(),
            "phrases": [p.strip().lower() for p in self.phrases_input.text().split(",") if p.strip()],
            "open_apps": [a.strip() for a in self.open_apps_input.text().split(",") if a.strip()],
            "close_mode": self.close_mode_combo.currentData(),
            "close_apps": [c.strip() for c in self.custom_close_input.text().split(",") if c.strip()],
            "volume_mode": self.volume_mode_combo.currentData(),
            "pause_media": self.chk_pause_media.isChecked(),
            "lock_screen": self.chk_lock_screen.isChecked(),
            "clean_recycle_bin": self.chk_clean_recycle.isChecked(),
            "briefing": self.chk_briefing.isChecked(),
            "response_text": self.response_input.text().strip(),
        }
        resp = self.controller.execute_protocol(data)
        QMessageBox.information(self, "Тест протокола", f"Ответ JARVIS:\n\n{resp}")

    def _on_delete_clicked(self) -> None:
        if not self._current_protocol_id:
            return
        name = self.name_input.text().strip() or "протокол"
        reply = QMessageBox.question(
            self, "Удаление", f"Удалить протокол «{name}»?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.controller.delete_protocol(self._current_protocol_id)
            self._reload_protocols_list()

    def _on_controller_changed(self) -> None:
        self._reload_protocols_list()
