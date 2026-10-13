import pytest
from ui.worker_threads import ActionWorker, TransferWorker
from network.client_core import StorageClient


def test_action_worker_success(qtbot):
    def mock_action(arg1, arg2):
        return f"{arg1} {arg2}"

    worker = ActionWorker(mock_action, "hello", "world")

    with qtbot.waitSignal(worker.finished, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == ["hello world"]


def test_action_worker_error(qtbot):
    def mock_action():
        raise ValueError("Test error")

    worker = ActionWorker(mock_action)

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == ["Test error"]


def test_transfer_worker_upload(qtbot, mocker):
    mock_client = mocker.MagicMock(spec=StorageClient)
    # Передаем offset=10
    worker = TransferWorker("upload", mock_client, "/local.txt", "remote.txt", offset=10)

    with qtbot.waitSignal(worker.finished, timeout=1000):
        worker.run()

    mock_client.upload_file.assert_called_once()
    args = mock_client.upload_file.call_args[0]
    assert args[0] == "/local.txt"
    assert args[1] == "remote.txt"
    assert args[2] == 10 
    assert callable(args[3])


def test_transfer_worker_download(qtbot, mocker):
    mock_client = mocker.MagicMock(spec=StorageClient)
    worker = TransferWorker("download", mock_client, "/local.txt", "remote.txt", is_bak=True)

    with qtbot.waitSignal(worker.finished, timeout=1000):
        worker.run()

    mock_client.download_file.assert_called_once()

    args = mock_client.download_file.call_args[0]
    assert args[0] == "remote.txt"
    assert args[1] == "/local.txt"
    assert args[2] is True  # Проверяем is_bak
    assert callable(args[3])  # Проверяем callback


def test_transfer_worker_error(qtbot, mocker):
    mock_client = mocker.MagicMock(spec=StorageClient)
    mock_client.upload_file.side_effect = Exception("Upload failed")
    worker = TransferWorker("upload", mock_client, "/l", "r")

    with qtbot.waitSignal(worker.error, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == ["Upload failed"]


def test_transfer_worker_progress(qtbot, mocker):
    mock_client = mocker.MagicMock(spec=StorageClient)

    def side_effect(remote, local, is_bak, callback):
        callback(50, 100)

    mock_client.download_file.side_effect = side_effect
    worker = TransferWorker("download", mock_client, "/l", "r")

    with qtbot.waitSignal(worker.progress, timeout=1000) as blocker:
        worker.run()

    assert blocker.args == [50, 100]