from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QListWidget, QListWidgetItem, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon


class HostListWidget(QWidget):
    """主机列表组件"""

    host_double_clicked = pyqtSignal(dict)
    add_host_clicked = pyqtSignal()
    edit_host_clicked = pyqtSignal(dict)
    delete_host_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.hosts = []
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索主机...")
        self.search_input.textChanged.connect(self.filter_hosts)
        search_layout.addWidget(self.search_input)

        self.add_button = QPushButton("添加主机")
        self.add_button.clicked.connect(self.add_host_clicked.emit)
        search_layout.addWidget(self.add_button)

        layout.addLayout(search_layout)

        self.host_list = QListWidget()
        self.host_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.host_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.host_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.host_list)

        self.setLayout(layout)

    def load_hosts(self, hosts: list):
        """加载主机列表"""
        self.hosts = hosts
        self.refresh_list()

    def refresh_list(self):
        """刷新列表显示"""
        self.host_list.clear()
        keyword = self.search_input.text().lower()

        for host in self.hosts:
            if keyword and keyword not in host['name'].lower() and \
               keyword not in host['host'].lower() and \
               keyword not in host['username'].lower():
                continue

            item = QListWidgetItem(f"{host['name']} ({host['username']}@{host['host']}:{host['port']})")
            item.setData(Qt.ItemDataRole.UserRole, host)
            self.host_list.addItem(item)

    def filter_hosts(self):
        """过滤主机列表"""
        self.refresh_list()

    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击主机项"""
        host = item.data(Qt.ItemDataRole.UserRole)
        self.host_double_clicked.emit(host)

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.host_list.itemAt(pos)
        if not item:
            return

        host = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        connect_action = menu.addAction("连接")
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")

        action = menu.exec(self.host_list.mapToGlobal(pos))

        if action == connect_action:
            self.host_double_clicked.emit(host)
        elif action == edit_action:
            self.edit_host_clicked.emit(host)
        elif action == delete_action:
            self.delete_host_clicked.emit(host['id'])

    def get_selected_host(self):
        """获取选中的主机"""
        item = self.host_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
