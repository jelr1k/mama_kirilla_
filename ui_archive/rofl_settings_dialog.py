from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox, QVBoxLayout
from ui.animations import fade_in_window, install_button_micro_interactions


class RoflSettingsDialog(QDialog):
    """Секретное окно настройки вероятностей рофлов."""

    DEFAULT_ROFL_CHANCE = 0.12
    DEFAULT_DEMON_CHANCE = 0.15

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Настройки рофлов")
        self.setModal(True)
        self.resize(420, 180)

        settings = controller.get_rofl_settings()

        self.chance = QDoubleSpinBox()
        self.chance.setRange(0.0, 100.0)
        self.chance.setDecimals(1)
        self.chance.setSingleStep(1.0)
        self.chance.setSuffix(" %")
        self.chance.setValue(float(settings.get("chance", self.DEFAULT_ROFL_CHANCE)) * 100.0)

        self.demon_chance = QDoubleSpinBox()
        self.demon_chance.setRange(0.0, 100.0)
        self.demon_chance.setDecimals(1)
        self.demon_chance.setSingleStep(1.0)
        self.demon_chance.setSuffix(" %")
        self.demon_chance.setValue(float(settings.get("demon_chance", self.DEFAULT_DEMON_CHANCE)) * 100.0)

        form = QFormLayout()
        form.addRow("Шанс рофла:", self.chance)
        form.addRow("Шанс демонического рофла:", self.demon_chance)

        box = QGroupBox("Служебные настройки")
        box.setLayout(form)

        buttons = QDialogButtonBox()
        reset = buttons.addButton("Сбросить до дефолта", QDialogButtonBox.ResetRole)
        save = buttons.addButton("Сохранить рофлы", QDialogButtonBox.AcceptRole)
        buttons.addButton(QDialogButtonBox.Cancel)
        reset.clicked.connect(self._reset_defaults)
        save.clicked.connect(self._save)
        buttons.rejected.connect(self.reject)

        install_button_micro_interactions(self)
        root = QVBoxLayout(self)
        root.addWidget(box)
        root.addWidget(buttons)

    def showEvent(self, event):
        super().showEvent(event)
        fade_in_window(self, 180)

    def _reset_defaults(self):
        self.chance.setValue(self.DEFAULT_ROFL_CHANCE * 100.0)
        self.demon_chance.setValue(self.DEFAULT_DEMON_CHANCE * 100.0)

    def _save(self):
        self.controller.save_rofl_settings(
            self.chance.value() / 100.0,
            self.demon_chance.value() / 100.0,
        )
        self.accept()
