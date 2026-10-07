from urllib.parse import unquote
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

DIALOG_STYLE = """
QDialog {
    background-color: #0B0914; /* Принудительно убираем серый системный фон */
}
QLabel#title {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
}
QTableWidget {
    background-color: #161326;
    border: 1px solid #1E1A33; /* Тонкая элегантная рамка */
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #2A2542;
    selection-color: #FFFFFF;
    font-size: 13px;
    color: #E2E0EE;
    outline: none;
}
QTableWidget::item {
    padding: 4px 12px;
    border-bottom: 1px solid #1E1A33;
}
QTableWidget::item:selected {
    border-radius: 8px;
}
QHeaderView::section {
    background-color: transparent;
    border: none;
    border-bottom: 1px solid #2A2542;
    padding: 16px 12px 12px 12px;
    font-weight: 700;
    font-size: 11px;
    color: #837CA6;
    text-transform: uppercase;
}
QPushButton#closeBtn {
    background-color: #241F3E;
    border: none;
    border-radius: 8px;
    padding: 8px 24px;
    color: #E2E0EE;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#closeBtn:hover { background-color: #2D274D; }
QPushButton#closeBtn:pressed { background-color: #1C1830; }

/* Скроллбары */
QScrollBar:vertical { border: none; background: transparent; width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #2A2542; min-height: 20px; border-radius: 6px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #3B3459; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
"""


class HistoryDialog(QDialog):
    def __init__(self, history_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Журнал операций")
        self.resize(800, 500)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Заголовок
        title = QLabel("История изменений")
        title.setObjectName("title")
        layout.addWidget(title)

        # Таблица
        self.table = QTableWidget()
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

        # Нижняя панель с кнопкой закрытия
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Закрыть")
        btn_close.setObjectName("closeBtn")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        self._populate_table(history_text)

    def _populate_table(self, text: str):
        lines = [line for line in text.split('\n') if line.strip()]
        if not lines: return

        headers = lines[0].split('\t')
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setRowCount(len(lines) - 1)
        for row_idx, line in enumerate(lines[1:]):
            cols = line.split('\t')
            for col_idx, col_val in enumerate(cols):
                decoded_val = unquote(col_val)
                item = QTableWidgetItem(decoded_val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                # Стилизация текста в зависимости от колонки
                if col_idx in [0, 1]:  # Date, User
                    item.setForeground(QColor("#837CA6"))

                elif col_idx == 2:  # Action
                    action = decoded_val.upper()
                    if "UPLOAD" in action:
                        item.setForeground(QColor("#00E676"))  # Зеленый
                    elif "DOWNLOAD" in action:
                        item.setForeground(QColor("#6C5DD3"))  # Фиолетовый
                    elif "DELETE" in action:
                        item.setForeground(QColor("#FF4B63"))  # Красный
                    elif "RENAME" in action:
                        item.setForeground(QColor("#FFB020"))  # Желтый
                    else:
                        item.setForeground(QColor("#FFFFFF"))

                    # Делаем действие жирным шрифтом
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                elif col_idx == 3:  # File
                    item.setForeground(QColor("#FFFFFF"))

                self.table.setItem(row_idx, col_idx, item)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)