import os
import math
from urllib.parse import unquote
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox,
                             QFileDialog, QInputDialog, QFrame, QGraphicsDropShadowEffect,
                             QStackedWidget, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from network.client_core import StorageClient
from ui.worker_threads import ActionWorker, TransferWorker
from ui.history_dialog import HistoryDialog
from utils.formatters import format_size


class LiquidButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("loginBtn")

        self._hover_progress = 0.0
        self._wave_phase = 0.0
        self._is_pressed = False
        self._is_hovered = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.setInterval(30)

    def animate(self):
        self._wave_phase += 0.15
        target = 1.0 if self._is_hovered else 0.0
        self._hover_progress += (target - self._hover_progress) * 0.15

        if not self._is_hovered and self._hover_progress < 0.01:
            self._hover_progress = 0.0
            self.timer.stop()
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self.timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._is_pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        push_offset = 5 if self._is_pressed else 0
        radius = 12.0

        shadow_rect = QRectF(0, 6, rect.width(), rect.height() - 6)
        btn_rect = QRectF(0, push_offset, rect.width(), rect.height() - 6)

        if not self._is_pressed:
            painter.setBrush(QColor("#3A2E85"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(shadow_rect, radius, radius)

        painter.setBrush(QColor("#241F3E"))
        painter.drawRoundedRect(btn_rect, radius, radius)

        if self._hover_progress > 0:
            painter.save()
            path = QPainterPath()
            path.addRoundedRect(btn_rect, radius, radius)
            painter.setClipPath(path)
            painter.setBrush(QColor("#6C5DD3"))
            painter.setPen(Qt.PenStyle.NoPen)

            wave_height = 5.0
            fill_height = btn_rect.height() * self._hover_progress
            base_y = btn_rect.bottom() - fill_height

            wave_path = QPainterPath()
            wave_path.moveTo(0, btn_rect.bottom())
            wave_path.lineTo(0, base_y)

            for x in range(0, int(btn_rect.width()) + 6, 5):
                y = base_y + math.sin(x * 0.05 + self._wave_phase) * wave_height * self._hover_progress
                wave_path.lineTo(x, y)

            wave_path.lineTo(btn_rect.width(), btn_rect.bottom())
            wave_path.closeSubpath()

            painter.drawPath(wave_path)
            painter.restore()

        painter.setPen(QColor("#FFFFFF"))
        font = self.font()
        font.setBold(True)
        font.setPointSize(14)
        painter.setFont(font)
        painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, self.text())


PERFECT_DARK_STYLE = """
* {
    font-family: -apple-system, BlinkMacSystemFont, "San Francisco", "Segoe UI", "Inter", sans-serif;
}
QMainWindow {
    background-color: #0B0914;
}
QLabel {
    color: #E2E0EE;
    font-size: 13px;
    font-weight: 500;
}
QLineEdit {
    background-color: #161326;
    border: 1px solid #2A2542;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #FFFFFF;
}
QLineEdit:focus {
    border: 1px solid #6C5DD3;
    background-color: #1A162D;
}
QPushButton {
    background-color: #241F3E;
    border: none;
    border-bottom: 3px solid #110E1F; 
    border-radius: 8px;
    padding: 8px 16px;
    color: #E2E0EE;
    font-size: 13px;
    font-weight: 600;
    margin-top: 0px;
    margin-bottom: 3px; 
}
QPushButton:hover { 
    background-color: #2E284F; 
    border-bottom: 3px solid #161326; 
    color: #FFFFFF;
}
QPushButton:pressed { 
    background-color: #1C1830; 
    border-bottom: 0px solid transparent; 
    margin-top: 3px; 
    margin-bottom: 0px;
}
QPushButton:disabled { 
    color: #554F70; 
    background-color: #161326; 
    border-bottom: 3px solid #0B0914; 
}
QPushButton#primaryBtn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6C5DD3, stop:1 #897BFA);
    border-bottom: 3px solid #4A3E9C;
    color: #FFFFFF;
}
QPushButton#primaryBtn:hover { 
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7D6DF2, stop:1 #9A8DFF); 
    border-bottom: 3px solid #5A4CAD;
}
QPushButton#primaryBtn:pressed { 
    background-color: #5545B8; 
    border-bottom: 0px;
    margin-top: 3px;
    margin-bottom: 0px;
}
QPushButton#dangerBtn { 
    background-color: transparent; 
    border: 1px solid #FF4B63; 
    border-bottom: 3px solid #8C2937; 
    color: #FF4B63; 
}
QPushButton#dangerBtn:hover { 
    background-color: #FF4B63; 
    border-bottom: 3px solid #B33445; 
    color: #FFFFFF; 
}
QPushButton#dangerBtn:pressed { 
    background-color: #D72D43; 
    border: 1px solid #D72D43;
    border-bottom: 0px;
    margin-top: 3px;
    margin-bottom: 0px;
}
QPushButton#loginBtn {
    border: none;
    margin: 0px;
    padding: 0px;
    background-color: transparent;
}
QPushButton#loginBtn:hover, QPushButton#loginBtn:pressed {
    background-color: transparent; border: none; margin: 0px;
}
QTableWidget {
    background-color: #161326;
    border: none;
    border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #2A2542;
    selection-color: #FFFFFF;
    font-size: 13px;
    color: #E2E0EE;
    outline: none;
}
QTableWidget::item {
    padding: 8px 12px;
    border-bottom: 1px solid #1E1A33;
}
QTableWidget::item:selected {
    background-color: #2A2542;
    border-radius: 8px;
}
QHeaderView::section {
    background-color: #161326;
    border: none;
    border-bottom: 2px solid #0B0914;
    padding: 12px;
    font-weight: 700;
    font-size: 11px;
    color: #837CA6;
    text-transform: uppercase;
}
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #241F3E;
    text-align: center;
    color: transparent;
    height: 6px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6C5DD3, stop:1 #897BFA);
    border-radius: 4px;
}
QFrame#card { 
    background-color: #161326; 
    border-radius: 16px; 
}
QScrollBar:vertical { border: none; background: #0B0914; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #2A2542; min-height: 20px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #3B3459; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileVault")
        self.setStyleSheet(PERFECT_DARK_STYLE)

        self.client = StorageClient()
        self.connected = False
        self._workers = set()

        # Таймер для фонового автообновления списка
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(3000)
        self.poll_timer.timeout.connect(self.silent_poll)

        self._init_ui()
        self._set_login_mode()

    def _add_shadow(self, widget, blur=20, y_offset=8):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(blur)
        shadow.setXOffset(0)
        shadow.setYOffset(y_offset)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)

    def _center_window(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def _set_login_mode(self):
        self.stacked_widget.setCurrentIndex(0)
        self.page_workspace.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.page_login.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setMinimumSize(420, 520)
        self.setMaximumSize(420, 520)
        self.resize(420, 520)
        self._center_window()

    def _set_workspace_mode(self):
        self.stacked_widget.setCurrentIndex(1)
        self.page_login.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.page_workspace.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(900, 600)
        self.resize(1050, 700)
        self._center_window()

    def _init_ui(self):
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.page_login = QWidget()
        self.page_workspace = QWidget()
        self._build_login_screen()
        self._build_workspace_screen()
        self.stacked_widget.addWidget(self.page_login)
        self.stacked_widget.addWidget(self.page_workspace)

    def _build_login_screen(self):
        layout = QVBoxLayout(self.page_login)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setFixedSize(360, 460)
        card.setStyleSheet("background-color: #161326; border-radius: 16px;")
        self._add_shadow(card, blur=30, y_offset=10)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 40, 32, 40)
        card_layout.setSpacing(16)

        title = QLabel("FileVault")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFFFFF;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        card_layout.addSpacing(10)

        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QLineEdit("5050")
        self.user_input = QLineEdit("Admin")

        card_layout.addWidget(QLabel("IP-адрес"))
        card_layout.addWidget(self.host_input)
        card_layout.addWidget(QLabel("Порт"))
        card_layout.addWidget(self.port_input)
        card_layout.addWidget(QLabel("Пользователь"))
        card_layout.addWidget(self.user_input)
        card_layout.addStretch()

        self.btn_connect = LiquidButton("Подключиться")
        self.btn_connect.clicked.connect(self.action_connect)
        card_layout.addWidget(self.btn_connect)

        layout.addWidget(card)

    def _build_workspace_screen(self):
        layout = QVBoxLayout(self.page_workspace)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        toolbar_card = QFrame()
        toolbar_card.setObjectName("card")
        self._add_shadow(toolbar_card)

        toolbar_layout = QHBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(16, 16, 16, 16)
        toolbar_layout.setSpacing(10)

        self.btn_refresh = QPushButton("Обновить")
        self.btn_upload = QPushButton("Загрузить файл")
        self.btn_upload.setObjectName("primaryBtn")
        self.btn_download = QPushButton("Скачать")
        self.btn_download_bak = QPushButton("Скачать .bak")
        self.btn_rename = QPushButton("Переименовать")
        self.btn_history_file = QPushButton("История файла")
        self.btn_history_all = QPushButton("Журнал (общий)")
        self.btn_delete = QPushButton("Удалить")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_disconnect = QPushButton("Отключиться")

        self.btn_refresh.clicked.connect(self.load_file_list)
        self.btn_upload.clicked.connect(self.upload_action)

        # Исправленные lambda-выражения для корректной передачи параметров
        self.btn_download.clicked.connect(lambda checked=False: self.download_action(False))
        self.btn_download_bak.clicked.connect(lambda checked=False: self.download_action(True))

        self.btn_rename.clicked.connect(self.rename_action)
        self.btn_delete.clicked.connect(self.delete_action)
        self.btn_history_file.clicked.connect(self.history_file_action)
        self.btn_history_all.clicked.connect(lambda checked=False: self.history_action(""))
        self.btn_disconnect.clicked.connect(self.action_disconnect)

        buttons = [self.btn_refresh, self.btn_upload, self.btn_download, self.btn_download_bak,
                   self.btn_rename, self.btn_history_file, self.btn_history_all,
                   self.btn_delete, self.btn_disconnect]

        toolbar_layout.addStretch()
        for btn in buttons:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toolbar_layout.addWidget(btn)
        toolbar_layout.addStretch()
        layout.addWidget(toolbar_card)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Имя файла", "Размер", "Дата изменения", "Резервная копия"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._add_shadow(self.table, blur=30, y_offset=12)
        layout.addWidget(self.table)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(10, 0, 10, 0)
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #00E676; font-weight: 600;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_bar.setFixedWidth(250)

        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_bar)
        layout.addLayout(status_layout)

    def _run_worker(self, worker):
        self._workers.add(worker)
        worker.finished.connect(lambda *args: self._workers.discard(worker))
        worker.error.connect(lambda *args: self._workers.discard(worker))
        worker.start()

    def action_connect(self):
        host, port, user = self.host_input.text(), int(self.port_input.text()), self.user_input.text()
        try:
            self.client.connect(host, port, user)
            self.connected = True
            self.status_label.setText(f"Подключено как {user}")
            self._set_workspace_mode()
            self.load_file_list()
            self.poll_timer.start()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def action_disconnect(self):
        self.poll_timer.stop()
        self.client.disconnect()
        self.connected = False
        self.table.setRowCount(0)
        self._set_login_mode()

    def silent_poll(self):
        if len(self._workers) > 0:
            return
        worker = ActionWorker(self.client.get_list)
        worker.finished.connect(self._populate_table)
        self._workers.add(worker)
        worker.finished.connect(lambda *args: self._workers.discard(worker))
        worker.error.connect(lambda *args: self._workers.discard(worker))
        worker.start()

    def load_file_list(self):
        worker = ActionWorker(self.client.get_list)
        worker.finished.connect(self._populate_table)
        worker.error.connect(self.show_error)
        self._run_worker(worker)

    def _populate_table(self, data: str):
        selected_filename = self.get_selected_filename()

        self.table.setRowCount(0)
        if not data: return

        lines = data.strip().split('\n')
        self.table.setRowCount(len(lines))
        for row, line in enumerate(lines):
            parts = line.split('|')
            if len(parts) == 4:
                safe_name = unquote(parts[0])
                exact_bytes = int(parts[1])

                item_name = QTableWidgetItem(safe_name)
                item_size = QTableWidgetItem(format_size(exact_bytes))
                item_size.setData(Qt.ItemDataRole.UserRole, exact_bytes)
                item_date = QTableWidgetItem(parts[2])

                has_bak = parts[3] == "has_bak"
                item_bak = QTableWidgetItem("• Доступна" if has_bak else "-")
                item_bak.setForeground(QColor("#00E676") if has_bak else QColor("#554F70"))

                muted_color = QColor("#837CA6")
                item_size.setForeground(muted_color)
                item_date.setForeground(muted_color)
                item_size.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

                self.table.setItem(row, 0, item_name)
                self.table.setItem(row, 1, item_size)
                self.table.setItem(row, 2, item_date)
                self.table.setItem(row, 3, item_bak)

        if selected_filename:
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0).text() == selected_filename:
                    self.table.selectRow(row)
                    break

    def get_selected_filename(self) -> str:
        row = self.table.currentRow()
        if row >= 0: return self.table.item(row, 0).text()
        return None

    def upload_action(self):
        local_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для загрузки")
        if not local_path: return
        filename = os.path.basename(local_path)
        offset = 0

        # Умная проверка на докачку (Resumable Upload)
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == filename:
                remote_bytes = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                local_bytes = os.path.getsize(local_path)

                if remote_bytes > 0:
                    reply = QMessageBox.question(
                        self, "Файл существует",
                        f"Файл {filename} уже есть на сервере.\nРазмер на сервере: {format_size(remote_bytes)}\nРазмер на клиенте: {format_size(local_bytes)}\n\nХотите докачать файл (Да) или перезаписать с нуля (Нет)?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                    )
                    if reply == QMessageBox.StandardButton.Cancel:
                        return
                    elif reply == QMessageBox.StandardButton.Yes:
                        if remote_bytes >= local_bytes:
                            QMessageBox.warning(self, "Ошибка",
                                                "Размер файла на сервере больше или равен локальному. Докачка невозможна.")
                            return
                        offset = remote_bytes
                break

        self._start_transfer("upload", local_path, filename, is_bak=False, offset=offset)

    def download_action(self, is_bak: bool = False):
        filename = self.get_selected_filename()
        if not filename:
            QMessageBox.warning(self, "Внимание", "Выберите файл в списке.")
            return

        if is_bak and self.table.item(self.table.currentRow(), 3).text() == "-":
            QMessageBox.warning(self, "Внимание", "У этого файла нет резервной копии.")
            return

        default_name = filename + ".bak" if is_bak else filename
        local_path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл как", default_name)
        if not local_path: return

        self._start_transfer("download", local_path, filename, is_bak=is_bak, offset=0)

    def _start_transfer(self, action: str, local_path: str, remote_name: str, is_bak: bool = False, offset: int = 0):
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.setText("Синхронизация..." if action == "upload" else "Загрузка...")
        self.status_label.setStyleSheet("color: #6C5DD3; font-weight: 600;")

        transfer_worker = TransferWorker(action, self.client, local_path, remote_name, is_bak, offset)
        transfer_worker.progress.connect(self._update_progress)
        transfer_worker.finished.connect(self._transfer_finished)
        transfer_worker.error.connect(self._transfer_error)
        self._run_worker(transfer_worker)

    def _update_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def _transfer_finished(self):
        self.progress_bar.hide()
        self.status_label.setText(f"Подключено как {self.user_input.text()}")
        self.status_label.setStyleSheet("color: #00E676; font-weight: 600;")
        self.load_file_list()

    def _transfer_error(self, err_msg: str):
        self.progress_bar.hide()
        self.status_label.setText(f"Подключено как {self.user_input.text()}")
        self.status_label.setStyleSheet("color: #00E676; font-weight: 600;")
        self.show_error(err_msg)

    def delete_action(self):
        filename = self.get_selected_filename()
        if not filename:
            QMessageBox.warning(self, "Внимание", "Выберите файл в списке для удаления.")
            return

        if QMessageBox.question(self, "Подтверждение", f"Удалить файл {filename} (включая бэкапы)?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            worker = ActionWorker(self.client.delete_file, filename)
            worker.finished.connect(self.load_file_list)
            worker.error.connect(self.show_error)
            self._run_worker(worker)

    def rename_action(self):
        old_name = self.get_selected_filename()
        if not old_name:
            QMessageBox.warning(self, "Внимание", "Выберите файл в списке для переименования.")
            return

        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя файла:", text=old_name)
        if ok and new_name and new_name != old_name:
            worker = ActionWorker(self.client.rename_file, old_name, new_name)
            worker.finished.connect(self.load_file_list)
            worker.error.connect(self.show_error)
            self._run_worker(worker)

    def history_action(self, target_file=""):
        worker = ActionWorker(self.client.get_history, target_file)
        worker.finished.connect(self.show_history_dialog)
        worker.error.connect(self.show_error)
        self._run_worker(worker)

    def history_file_action(self):
        filename = self.get_selected_filename()
        if not filename:
            QMessageBox.warning(self, "Внимание", "Выберите файл для просмотра его истории.")
            return
        self.history_action(filename)

    def show_history_dialog(self, text: str):
        lines = [line for line in text.split('\n') if line.strip()]
        if len(lines) <= 1:
            QMessageBox.information(self, "Журнал операций", "История операций для данного файла пуста.")
            return

        dialog = HistoryDialog(text, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def show_error(self, message: str):
        QMessageBox.critical(self, "Ошибка", message)