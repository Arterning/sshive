from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QSplitter,
                             QMessageBox, QStatusBar, QTabWidget, QVBoxLayout,
                             QPushButton, QLabel)
from PyQt6.QtCore import Qt
from database import DatabaseManager
from host_list_widget import HostListWidget
from host_dialog import HostDialog
from terminal_widget import TerminalWidget
from ssh_client import SSHClient


class SSHTerminalTab(QWidget):
    """SSH终端标签页"""

    def __init__(self, host_data: dict):
        super().__init__()
        self.host_data = host_data
        self.ssh_client = SSHClient()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        info_layout = QHBoxLayout()
        self.status_label = QLabel(f"正在连接到 {self.host_data['name']}...")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()

        self.disconnect_button = QPushButton("断开连接")
        self.disconnect_button.clicked.connect(self.disconnect)
        info_layout.addWidget(self.disconnect_button)

        layout.addLayout(info_layout)

        self.terminal = TerminalWidget()
        layout.addWidget(self.terminal)

        self.setLayout(layout)

    def connect_signals(self):
        """连接信号"""
        self.terminal.command_entered.connect(self.ssh_client.send_command)
        self.ssh_client.output_received.connect(self.terminal.append_output)
        self.ssh_client.connection_error.connect(self.on_connection_error)
        self.ssh_client.connection_closed.connect(self.on_connection_closed)

    def connect_ssh(self):
        """连接SSH"""
        success = self.ssh_client.connect(
            host=self.host_data['host'],
            port=self.host_data['port'],
            username=self.host_data['username'],
            password=self.host_data.get('password', ''),
            auth_type=self.host_data.get('auth_type', 'password'),
            private_key_path=self.host_data.get('private_key_path', '')
        )

        if success:
            self.status_label.setText(f"已连接到 {self.host_data['name']} ({self.host_data['host']})")
        else:
            self.status_label.setText(f"连接失败: {self.host_data['name']}")

    def disconnect(self):
        """断开连接"""
        self.ssh_client.disconnect()

    def on_connection_error(self, error: str):
        """连接错误"""
        self.status_label.setText(f"错误: {error}")
        self.terminal.append_output(f"\n\n[错误] {error}\n")

    def on_connection_closed(self):
        """连接关闭"""
        self.status_label.setText(f"已断开连接: {self.host_data['name']}")
        self.terminal.append_output("\n\n[连接已关闭]\n")


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setup_ui()
        self.load_hosts()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("SSHive - SSH连接管理工具")
        self.setGeometry(100, 100, 1200, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.host_list_widget = HostListWidget()
        self.host_list_widget.setMaximumWidth(400)
        self.host_list_widget.setMinimumWidth(250)
        splitter.addWidget(self.host_list_widget)

        self.terminal_tabs = QTabWidget()
        self.terminal_tabs.setTabsClosable(True)
        self.terminal_tabs.tabCloseRequested.connect(self.close_terminal_tab)
        splitter.addWidget(self.terminal_tabs)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        central_widget.setLayout(layout)

        self.statusBar().showMessage("就绪")

        self.connect_signals()

    def connect_signals(self):
        """连接信号"""
        self.host_list_widget.host_double_clicked.connect(self.connect_to_host)
        self.host_list_widget.add_host_clicked.connect(self.add_host)
        self.host_list_widget.edit_host_clicked.connect(self.edit_host)
        self.host_list_widget.delete_host_clicked.connect(self.delete_host)

    def load_hosts(self):
        """加载主机列表"""
        hosts = self.db.get_all_hosts()
        self.host_list_widget.load_hosts(hosts)
        self.statusBar().showMessage(f"已加载 {len(hosts)} 个主机")

    def add_host(self):
        """添加主机"""
        dialog = HostDialog(self)
        if dialog.exec():
            host_data = dialog.get_host_data()
            try:
                self.db.add_host(**host_data)
                self.load_hosts()
                QMessageBox.information(self, "成功", "主机已添加")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加主机失败: {str(e)}")

    def edit_host(self, host_data: dict):
        """编辑主机"""
        dialog = HostDialog(self, host_data)
        if dialog.exec():
            updated_data = dialog.get_host_data()
            try:
                self.db.update_host(host_data['id'], **updated_data)
                self.load_hosts()
                QMessageBox.information(self, "成功", "主机已更新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新主机失败: {str(e)}")

    def delete_host(self, host_id: int):
        """删除主机"""
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个主机吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_host(host_id)
                self.load_hosts()
                QMessageBox.information(self, "成功", "主机已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除主机失败: {str(e)}")

    def connect_to_host(self, host_data: dict):
        """连接到主机"""
        tab_name = f"{host_data['name']}"

        for i in range(self.terminal_tabs.count()):
            if self.terminal_tabs.tabText(i) == tab_name:
                self.terminal_tabs.setCurrentIndex(i)
                return

        terminal_tab = SSHTerminalTab(host_data)
        index = self.terminal_tabs.addTab(terminal_tab, tab_name)
        self.terminal_tabs.setCurrentIndex(index)

        terminal_tab.connect_ssh()

        self.statusBar().showMessage(f"正在连接到 {host_data['name']}...")

    def close_terminal_tab(self, index: int):
        """关闭终端标签页"""
        widget = self.terminal_tabs.widget(index)
        if isinstance(widget, SSHTerminalTab):
            widget.disconnect()
        self.terminal_tabs.removeTab(index)

    def closeEvent(self, event):
        """关闭事件"""
        for i in range(self.terminal_tabs.count()):
            widget = self.terminal_tabs.widget(i)
            if isinstance(widget, SSHTerminalTab):
                widget.disconnect()

        self.db.close()
        event.accept()
