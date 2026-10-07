from PyQt6.QtCore import QThread, pyqtSignal
from network.client_core import StorageClient

class ActionWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            res = self.func(*self.args)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class TransferWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, action: str, client: StorageClient, local_path: str, remote_name: str, is_bak: bool = False):
        super().__init__()
        self.action = action
        self.client = client
        self.local_path = local_path
        self.remote_name = remote_name
        self.is_bak = is_bak

    def run(self):
        try:
            if self.action == "upload":
                self.client.upload_file(self.local_path, self.remote_name, self._report)
            elif self.action == "download":
                self.client.download_file(self.remote_name, self.local_path, self.is_bak, self._report)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _report(self, current, total):
        self.progress.emit(current, total)