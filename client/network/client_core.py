import socket
import os
import threading
from urllib.parse import quote


class ProtocolError(Exception):
    pass


class StorageClient:
    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()

    def connect(self, host: str, port: int, username: str):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10.0)

        try:
            self.sock.connect((host, port))
            self.sock.settimeout(None)

            self._send_cmd(f"AUTH {username}")
            self._read_text_response()
        except Exception:
            # ВАЖНО: Если сервер вернул 403 (логин занят), закрываем сокет
            self.disconnect()
            raise

    def disconnect(self):
        with self.lock:
            if self.sock:
                try:
                    self._send_cmd("QUIT")
                    self.sock.close()
                except:
                    pass
                self.sock = None

    def _send_cmd(self, cmd: str):
        self.sock.sendall((cmd + "\r\n").encode('utf-8'))

    def _read_line(self) -> str:
        buf = bytearray()
        while True:
            char = self.sock.recv(1)
            if not char:
                raise ConnectionError("Соединение разорвано сервером")
            buf.extend(char)
            if buf.endswith(b"\r\n"):
                return buf[:-2].decode('utf-8')

    def _ensure_ok(self) -> str:
        line = self._read_line()
        if line.startswith("ERR"):
            raise ProtocolError(line[4:])
        return line

    def _read_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            packet = self.sock.recv(min(size - len(data), 65536))
            if not packet:
                raise ConnectionError("Соединение разорвано во время передачи")
            data.extend(packet)
        return bytes(data)

    def _read_text_response(self) -> str:
        header = self._ensure_ok()
        parts = header.split()
        if len(parts) > 1:
            size = int(parts[1])
            if size > 0:
                raw_bytes = self._read_exact(size)
                return raw_bytes.decode('utf-8')
        return ""

    def get_list(self) -> str:
        with self.lock:
            self._send_cmd("LIST")
            return self._read_text_response()

    def get_history(self, filename: str = "") -> str:
        with self.lock:
            cmd = f"HISTORY {quote(filename)}" if filename else "HISTORY"
            self._send_cmd(cmd)
            return self._read_text_response()

    def delete_file(self, filename: str):
        with self.lock:
            self._send_cmd(f"DELETE {quote(filename)}")
            self._read_text_response()

    def rename_file(self, old_name: str, new_name: str):
        with self.lock:
            self._send_cmd(f"RENAME {quote(old_name)} {quote(new_name)}")
            self._read_text_response()

    def download_file(self, remote_name: str, local_path: str, is_bak: bool = False, callback=None):
        target = f"{remote_name}.bak" if is_bak else remote_name
        offset = os.path.getsize(local_path) if os.path.exists(local_path) and not is_bak else 0

        with self.lock:
            self._send_cmd(f"GET {quote(target)} {offset}")
            header = self._ensure_ok()
            parts = header.split()

            payload_len = int(parts[1])
            total_size = int(parts[2]) if len(parts) > 2 else payload_len

            mode = "ab" if offset > 0 else "wb"
            with open(local_path, mode) as f:
                received = 0
                while received < payload_len:
                    chunk_size = min(65536, payload_len - received)
                    data = self.sock.recv(chunk_size)
                    if not data:
                        raise ConnectionError("Оборвано скачивание")
                    f.write(data)
                    received += len(data)
                    if callback:
                        callback(offset + received, total_size)

    def upload_file(self, local_path: str, remote_name: str, offset: int = 0, callback=None):
        size = os.path.getsize(local_path)
        payload_size = size - offset

        with self.lock:
            # Отправляем PUT с указанием размера полезной нагрузки и смещения
            self._send_cmd(f"PUT {quote(remote_name)} {payload_size} {offset}")

            with open(local_path, "rb") as f:
                f.seek(offset)  # Сдвигаем указатель для докачки
                sent = 0
                while sent < payload_size:
                    chunk = f.read(min(65536, payload_size - sent))
                    if not chunk: break
                    self.sock.sendall(chunk)
                    sent += len(chunk)
                    if callback:
                        callback(offset + sent, size)

            self._read_text_response()