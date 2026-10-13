import pytest
from unittest.mock import MagicMock, mock_open, patch
from urllib.parse import quote
from network.client_core import StorageClient, ProtocolError


@pytest.fixture
def client():
    return StorageClient()


def test_connect(client, mocker):
    mock_socket = mocker.patch("socket.socket")
    mock_sock_instance = MagicMock()
    mock_socket.return_value = mock_sock_instance

    mock_sock_instance.recv.side_effect = [
        b"O", b"K", b" ", b"1", b"3", b"\r", b"\n",
        b"A", b"u", b"t", b"h", b"e", b"n", b"t", b"i", b"c", b"a", b"t", b"e", b"d"
    ]

    client.connect("127.0.0.1", 5050, "Admin")

    mock_sock_instance.connect.assert_called_once_with(("127.0.0.1", 5050))
    mock_sock_instance.sendall.assert_called_once_with(b"AUTH Admin\r\n")


def test_disconnect(client):
    mock_sock = MagicMock()
    client.sock = mock_sock
    client.disconnect()

    mock_sock.sendall.assert_called_once_with(b"QUIT\r\n")
    mock_sock.close.assert_called_once()
    assert client.sock is None


def test_disconnect_exception(client):
    mock_sock = MagicMock()
    mock_sock.sendall.side_effect = Exception("Network error")
    client.sock = mock_sock
    client.disconnect()
    assert client.sock is None


def test_read_line(client):
    client.sock = MagicMock()
    client.sock.recv.side_effect = [b"O", b"K", b"\r", b"\n"]
    assert client._read_line() == "OK"


def test_read_line_disconnect(client):
    client.sock = MagicMock()
    client.sock.recv.return_value = b""
    with pytest.raises(ConnectionError, match="Соединение разорвано сервером"):
        client._read_line()


def test_ensure_ok_success(client, mocker):
    mocker.patch.object(client, "_read_line", return_value="OK 10")
    assert client._ensure_ok() == "OK 10"


def test_ensure_ok_error(client, mocker):
    mocker.patch.object(client, "_read_line", return_value="ERR 404 Not Found")
    with pytest.raises(ProtocolError, match="404 Not Found"):
        client._ensure_ok()


def test_read_exact_disconnect(client):
    client.sock = MagicMock()
    client.sock.recv.return_value = b""
    with pytest.raises(ConnectionError, match="Соединение разорвано во время передачи"):
        client._read_exact(5)


def test_read_text_response_empty(client, mocker):
    mocker.patch.object(client, "_ensure_ok", return_value="OK")
    assert client._read_text_response() == ""


def test_read_text_response_data(client, mocker):
    mocker.patch.object(client, "_ensure_ok", return_value="OK 5")
    mocker.patch.object(client, "_read_exact", return_value=b"Hello")
    assert client._read_text_response() == "Hello"


def test_get_list(client, mocker):
    client.sock = MagicMock()
    mocker.patch.object(client, "_read_text_response", return_value="file1.txt|100|date|has_bak")
    result = client.get_list()
    client.sock.sendall.assert_called_once_with(b"LIST\r\n")
    assert result == "file1.txt|100|date|has_bak"


def test_get_history(client, mocker):
    client.sock = MagicMock()
    mocker.patch.object(client, "_read_text_response", return_value="hist")
    assert client.get_history("my file") == "hist"
    client.sock.sendall.assert_called_once_with(f"HISTORY {quote('my file')}\r\n".encode())


def test_get_history_all(client, mocker):
    client.sock = MagicMock()
    mocker.patch.object(client, "_read_text_response", return_value="hist")
    assert client.get_history("") == "hist"
    client.sock.sendall.assert_called_once_with(b"HISTORY\r\n")


def test_delete_file(client, mocker):
    client.sock = MagicMock()
    mocker.patch.object(client, "_read_text_response")
    client.delete_file("my file")
    client.sock.sendall.assert_called_once_with(f"DELETE {quote('my file')}\r\n".encode())


def test_rename_file(client, mocker):
    client.sock = MagicMock()
    mocker.patch.object(client, "_read_text_response")
    client.rename_file("old", "new")
    client.sock.sendall.assert_called_once_with(f"RENAME {quote('old')} {quote('new')}\r\n".encode())


def test_download_file(client, mocker):
    client.sock = MagicMock()
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.object(client, "_ensure_ok", return_value="OK 5")
    client.sock.recv.side_effect = [b"Hello", b""]
    mock_file = mock_open()
    mock_callback = MagicMock()
    with patch("builtins.open", mock_file):
        client.download_file("test.txt", "/fake.txt", is_bak=False, callback=mock_callback)

    client.sock.sendall.assert_called_once_with(b"GET test.txt 0\r\n")
    mock_file.assert_called_once_with("/fake.txt", "wb")
    mock_file().write.assert_called_once_with(b"Hello")
    mock_callback.assert_called_with(5, 5)


def test_download_file_resume(client, mocker):
    client.sock = MagicMock()
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.getsize", return_value=10)
    mocker.patch.object(client, "_ensure_ok", return_value="OK 5 15")
    client.sock.recv.side_effect = [b"World", b""]
    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        client.download_file("test.txt", "/fake.txt", is_bak=False)
    client.sock.sendall.assert_called_once_with(b"GET test.txt 10\r\n")
    mock_file.assert_called_once_with("/fake.txt", "ab")  # Append режим


def test_download_file_disconnect(client, mocker):
    client.sock = MagicMock()
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.object(client, "_ensure_ok", return_value="OK 5")
    client.sock.recv.return_value = b""  # Имитация обрыва связи
    mock_file = mock_open()
    with patch("builtins.open", mock_file):
        with pytest.raises(ConnectionError, match="Оборвано скачивание"):
            client.download_file("test.txt", "/fake.txt")


def test_upload_file(client, mocker):
    client.sock = MagicMock()
    mocker.patch("os.path.getsize", return_value=4)
    mocker.patch.object(client, "_read_text_response", return_value="Success")
    mock_callback = MagicMock()
    mock_file = mock_open(read_data=b"Data")

    from unittest.mock import patch
    with patch("builtins.open", mock_file):
        client.upload_file("/fake.txt", "test.txt", callback=mock_callback)

    # ИСПРАВЛЕНО: добавлено смещение "0" в ожидаемый пакет, так как мы изменили протокол
    client.sock.sendall.assert_any_call(b"PUT test.txt 4 0\r\n")
    client.sock.sendall.assert_any_call(b"Data")
    mock_callback.assert_called_with(4, 4)