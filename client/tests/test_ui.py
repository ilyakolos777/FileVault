import pytest
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow, LiquidButton
from ui.history_dialog import HistoryDialog
from PyQt6.QtCore import QEvent, QRect, QPointF
from PyQt6.QtGui import QPaintEvent, QEnterEvent


@pytest.fixture
def app_window(qtbot, mocker):
    mocker.patch("ui.main_window.StorageClient")
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_initial_state(app_window):
    assert app_window.stacked_widget.currentIndex() == 0
    assert app_window.btn_connect.text() == "Подключиться"
    assert app_window.host_input.text() == "127.0.0.1"


def test_successful_connection(app_window, qtbot):
    app_window.client.connect.return_value = None
    qtbot.mouseClick(app_window.btn_connect, Qt.MouseButton.LeftButton)
    app_window.client.connect.assert_called_once_with("127.0.0.1", 5050, "Admin")
    assert app_window.stacked_widget.currentIndex() == 1
    assert app_window.connected is True


def test_connection_error(app_window, qtbot, mocker):
    app_window.client.connect.side_effect = Exception("Connection Refused")
    mock_msgbox = mocker.patch("ui.main_window.QMessageBox.critical")
    qtbot.mouseClick(app_window.btn_connect, Qt.MouseButton.LeftButton)
    assert app_window.stacked_widget.currentIndex() == 0
    mock_msgbox.assert_called_once()


def test_disconnect(app_window, qtbot):
    app_window._set_workspace_mode()
    app_window.connected = True
    qtbot.mouseClick(app_window.btn_disconnect, Qt.MouseButton.LeftButton)
    app_window.client.disconnect.assert_called_once()
    assert app_window.stacked_widget.currentIndex() == 0
    assert app_window.connected is False

def test_main_window_populate_table(app_window):
    data = "file%201.txt|1024|2026-09-22|has_bak\nfile2.txt|2048|2026-09-22|no_bak"
    app_window._populate_table(data)
    assert app_window.table.rowCount() == 2
    assert app_window.table.item(0, 0).text() == "file 1.txt"
    assert app_window.table.item(0, 3).text() == "• Доступна"
    assert app_window.table.item(1, 3).text() == "-"


def test_get_selected_filename(app_window):
    app_window._populate_table("file.txt|10|date|no_bak")
    assert app_window.get_selected_filename() is None
    app_window.table.selectRow(0)
    assert app_window.get_selected_filename() == "file.txt"


def test_actions_no_selection(app_window, mocker):
    mock_msg = mocker.patch("ui.main_window.QMessageBox.warning")
    app_window.delete_action()
    app_window.rename_action()
    app_window.history_file_action()
    app_window.download_action()
    assert mock_msg.call_count == 4


def test_upload_action_success(app_window, mocker):
    mocker.patch("ui.main_window.QFileDialog.getOpenFileName", return_value=("/fake/path.txt", ""))
    mock_start = mocker.patch.object(app_window, "_start_transfer")
    app_window.upload_action()
    mock_start.assert_called_once_with("upload", "/fake/path.txt", "path.txt")


def test_upload_action_cancel(app_window, mocker):
    mocker.patch("ui.main_window.QFileDialog.getOpenFileName", return_value=("", ""))
    mock_start = mocker.patch.object(app_window, "_start_transfer")
    app_window.upload_action()
    mock_start.assert_not_called()


def test_download_action_no_bak(app_window, mocker):
    app_window._populate_table("file.txt|10|date|-")
    app_window.table.selectRow(0)
    mock_msg = mocker.patch("ui.main_window.QMessageBox.warning")
    app_window.download_action(is_bak=True)
    mock_msg.assert_called_once_with(app_window, "Внимание", "У этого файла нет резервной копии.")


def test_download_action_success(app_window, mocker):
    app_window._populate_table("file.txt|10|date|has_bak")
    app_window.table.selectRow(0)
    mocker.patch("ui.main_window.QFileDialog.getSaveFileName", return_value=("/local/file.txt", ""))
    mock_start = mocker.patch.object(app_window, "_start_transfer")
    app_window.download_action()
    mock_start.assert_called_once_with("download", "/local/file.txt", "file.txt", False)


def test_delete_action_success(app_window, mocker):
    app_window._populate_table("file.txt|10|date|has_bak")
    app_window.table.selectRow(0)
    mocker.patch("ui.main_window.QMessageBox.question", return_value=mocker.Mock(name="Yes", __eq__=lambda s, o: True))
    mock_worker = mocker.patch("ui.main_window.ActionWorker")
    mock_run = mocker.patch.object(app_window, "_run_worker")

    app_window.delete_action()
    mock_worker.assert_called_once_with(app_window.client.delete_file, "file.txt")
    mock_run.assert_called_once()


def test_rename_action_success(app_window, mocker):
    app_window._populate_table("file.txt|10|date|has_bak")
    app_window.table.selectRow(0)
    mocker.patch("ui.main_window.QInputDialog.getText", return_value=("new_file.txt", True))
    mock_worker = mocker.patch("ui.main_window.ActionWorker")
    mock_run = mocker.patch.object(app_window, "_run_worker")

    app_window.rename_action()
    mock_worker.assert_called_once_with(app_window.client.rename_file, "file.txt", "new_file.txt")


def test_history_file_action(app_window, mocker):
    app_window._populate_table("file.txt|10|date|has_bak")
    app_window.table.selectRow(0)
    mock_worker = mocker.patch("ui.main_window.ActionWorker")
    mock_run = mocker.patch.object(app_window, "_run_worker")

    app_window.history_file_action()
    mock_worker.assert_called_once_with(app_window.client.get_history, "file.txt")


def test_transfer_callbacks(app_window, mocker):
    mock_load = mocker.patch.object(app_window, "load_file_list")

    app_window._transfer_finished()
    assert app_window.progress_bar.isHidden()
    mock_load.assert_called_once()

    mock_err = mocker.patch.object(app_window, "show_error")
    app_window._transfer_error("Bad error")
    mock_err.assert_called_once_with("Bad error")

    app_window._update_progress(50, 100)
    assert app_window.progress_bar.value() == 50
    assert app_window.progress_bar.maximum() == 100


def test_start_transfer(app_window, mocker):
    mock_worker = mocker.patch("ui.main_window.TransferWorker")
    mock_run = mocker.patch.object(app_window, "_run_worker")
    app_window._start_transfer("upload", "/local.txt", "remote.txt")
    mock_run.assert_called_once()
    assert app_window.status_label.text() == "Синхронизация..."


def test_show_history_dialog_empty(app_window, mocker):
    mock_msg = mocker.patch("ui.main_window.QMessageBox.information")
    app_window.show_history_dialog("DATE\tUSER\tACTION\tFILE\n")
    mock_msg.assert_called_once()


def test_show_history_dialog_full(app_window, mocker):
    mock_exec = mocker.patch("ui.history_dialog.HistoryDialog.exec")
    app_window.show_history_dialog("DATE\tUSER\tACTION\tFILE\n2026-09-22\tAdmin\tUPLOAD\tfile.txt")
    mock_exec.assert_called_once()

def test_history_dialog(qtbot):
    text = (
        "DATE\tUSER\tACTION\tFILE\n"
        "2026-09-22\tAdmin\tUPLOAD\tfile.txt\n"
        "2026-09-22\tAdmin\tDOWNLOAD\tfile.bak\n"
        "2026-09-22\tAdmin\tDELETE\tfile.txt\n"
        "2026-09-22\tAdmin\tRENAME\tfile.txt\n"
        "2026-09-22\tAdmin\tUNKNOWN\tfile.txt"
    )
    dialog = HistoryDialog(text)
    qtbot.addWidget(dialog)

    assert dialog.table.rowCount() == 5
    assert dialog.table.item(0, 2).text() == "UPLOAD"
    assert dialog.table.item(1, 2).text() == "DOWNLOAD"
    assert dialog.table.item(2, 2).text() == "DELETE"
    assert dialog.table.item(3, 2).text() == "RENAME"
    assert dialog.table.item(4, 2).text() == "UNKNOWN"


def test_history_dialog_empty(qtbot):
    dialog = HistoryDialog(" \n \n")
    assert dialog.table.rowCount() == 0


def test_liquid_button(qtbot):
    btn = LiquidButton("Test")
    qtbot.addWidget(btn)

    qtbot.mousePress(btn, Qt.MouseButton.LeftButton)
    assert btn._is_pressed is True

    qtbot.mouseRelease(btn, Qt.MouseButton.LeftButton)
    assert btn._is_pressed is False

    btn._is_hovered = True
    btn.timer.start()
    btn.animate()

    btn._hover_progress = 0.5
    btn.repaint()

    btn._is_hovered = False
    btn._hover_progress = 0.001
    btn.animate()
    assert btn.timer.isActive() is False


def test_liquid_button_paint_and_events(qtbot):
    btn = LiquidButton("Test")
    qtbot.addWidget(btn)


    enter_evt = QEnterEvent(QPointF(0, 0), QPointF(0, 0), QPointF(0, 0))
    btn.enterEvent(enter_evt)
    assert btn._is_hovered is True

    leave_evt = QEvent(QEvent.Type.Leave)
    btn.leaveEvent(leave_evt)
    assert btn._is_hovered is False

    btn._hover_progress = 0.5
    btn.paintEvent(QPaintEvent(QRect(0, 0, 100, 54)))

    btn._is_pressed = True
    btn.paintEvent(QPaintEvent(QRect(0, 0, 100, 54)))


def test_show_error(app_window, mocker):
    mock_box = mocker.patch("ui.main_window.QMessageBox.critical")
    app_window.show_error("Системный сбой")
    mock_box.assert_called_once_with(app_window, "Ошибка", "Системный сбой")