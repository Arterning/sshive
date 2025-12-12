import paramiko
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal


class SSHClient(QObject):
    """SSH客户端，处理连接和命令执行"""

    output_received = pyqtSignal(str)
    connection_closed = pyqtSignal()
    connection_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.client = None
        self.channel = None
        self.is_connected = False
        self.read_thread = None

    def connect(self, host: str, port: int, username: str, password: str = "",
                auth_type: str = "password", private_key_path: str = ""):
        """连接到SSH服务器"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if auth_type == "key" and private_key_path:
                key = paramiko.RSAKey.from_private_key_file(private_key_path)
                self.client.connect(host, port=port, username=username, pkey=key, timeout=10)
            else:
                self.client.connect(host, port=port, username=username, password=password, timeout=10)

            self.channel = self.client.invoke_shell(term='xterm', width=80, height=24)
            self.channel.settimeout(0.1)
            self.is_connected = True

            self.read_thread = threading.Thread(target=self._read_output, daemon=True)
            self.read_thread.start()

            return True
        except Exception as e:
            self.connection_error.emit(f"连接失败: {str(e)}")
            return False

    def _read_output(self):
        """读取SSH输出"""
        while self.is_connected:
            try:
                if self.channel and self.channel.recv_ready():
                    data = self.channel.recv(4096).decode('utf-8', errors='ignore')
                    self.output_received.emit(data)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self.is_connected:
                    self.connection_error.emit(f"读取输出错误: {str(e)}")
                break

    def send_command(self, command: bytes):
        """发送命令到SSH服务器"""
        if self.is_connected and self.channel:
            try:
                self.channel.send(command)
            except Exception as e:
                self.connection_error.emit(f"发送命令失败: {str(e)}")

    def resize_terminal(self, width: int, height: int):
        """调整终端大小"""
        if self.is_connected and self.channel:
            try:
                self.channel.resize_pty(width=width, height=height)
            except Exception as e:
                pass

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
        if self.channel:
            self.channel.close()
            self.channel = None
        if self.client:
            self.client.close()
            self.client = None
        self.connection_closed.emit()
