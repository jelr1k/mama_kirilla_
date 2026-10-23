from __future__ import annotations

"""Современная тёмная кибер-тема для Jarvis (Kirieshcka v2).

Без эмодзи, со строгой палитрой: deep slate, neon cyan и emerald green.
"""

DARK_THEME_QSS = """
QWidget {
    background-color: #090d16;
    color: #e2e8f0;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}

/* Окно и контейнеры */
QMainWindow, QDialog {
    background-color: #090d16;
}

/* Вкладки */
QTabWidget::pane {
    border: 1px solid #1a2336;
    border-radius: 8px;
    background-color: #0f1728;
    padding: 8px;
}

QTabBar::tab {
    background-color: #0f1728;
    color: #94a3b8;
    border: 1px solid #1a2336;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 18px;
    margin-right: 3px;
    font-weight: 500;
}

QTabBar::tab:hover {
    background-color: #172238;
    color: #f1f5f9;
    border-color: #2a3b5c;
}

QTabBar::tab:selected {
    background-color: #162238;
    color: #00e5ff;
    border: 1px solid #00e5ff;
    border-bottom: 2px solid #00e5ff;
    font-weight: 600;
}

/* Кнопки */
QPushButton {
    background-color: #162032;
    border: 1px solid #24334f;
    border-radius: 6px;
    color: #f1f5f9;
    padding: 6px 14px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #1d2c45;
    border-color: #00d0f0;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #0d1522;
    border-color: #0099bb;
}

QPushButton:checked {
    background-color: #0d283d;
    border-color: #00e5ff;
    color: #00e5ff;
    font-weight: 600;
}

QPushButton:disabled {
    background-color: #0e1420;
    border-color: #172030;
    color: #475569;
}

/* Поля ввода и текст */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0b101c;
    border: 1px solid #1e2b42;
    border-radius: 6px;
    color: #f1f5f9;
    padding: 6px 8px;
    selection-background-color: #0077aa;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00e5ff;
    background-color: #0d1424;
}

/* Группировки */
QGroupBox {
    border: 1px solid #1a253a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: bold;
    color: #00e5ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #090d16;
}

/* Выпадающие списки и счетчики */
QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0f1728;
    border: 1px solid #1e2b42;
    border-radius: 6px;
    padding: 5px 8px;
    color: #f1f5f9;
    min-height: 20px;
}

QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #00e5ff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid #1e2b42;
}

QComboBox QAbstractItemView {
    background-color: #0f1728;
    border: 1px solid #1e2b42;
    color: #f1f5f9;
    selection-background-color: #17243c;
    selection-color: #00e5ff;
    outline: none;
}

/* Чекбоксы и радиокнопки */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #e2e8f0;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #253550;
    border-radius: 4px;
    background-color: #0b101c;
}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #00e5ff;
}

QCheckBox::indicator:checked {
    background-color: #00e5ff;
    border-color: #00e5ff;
}

/* Скроллбары */
QScrollBar:vertical {
    background-color: #090d16;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #24334f;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00e5ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #090d16;
    height: 8px;
    border-radius: 4px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #24334f;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #00e5ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Списки и таблицы */
QListWidget, QTableWidget, QTreeWidget {
    background-color: #0b101c;
    border: 1px solid #1a2336;
    border-radius: 6px;
    color: #f1f5f9;
    gridline-color: #162032;
    outline: none;
}

QListWidget::item, QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #121927;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #142238;
    color: #00e5ff;
    border-left: 2px solid #00e5ff;
}

QListWidget::item:hover, QTableWidget::item:hover {
    background-color: #101a2b;
}

QHeaderView::section {
    background-color: #0f1728;
    color: #94a3b8;
    border: none;
    border-bottom: 1px solid #1a2336;
    padding: 6px 8px;
    font-weight: 600;
}

/* Метки и тултипы */
QLabel {
    color: #e2e8f0;
}

QToolTip {
    background-color: #0d1524;
    color: #f1f5f9;
    border: 1px solid #00e5ff;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
}
"""


def apply_theme(app) -> None:
    """Применяет тёмную кибер-тему к переданному приложению QApplication."""
    if app is not None:
        app.setStyleSheet(DARK_THEME_QSS)
