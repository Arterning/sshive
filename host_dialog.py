from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QSpinBox, QComboBox, QTextEdit,
                             QPushButton, QFileDialog, QLabel)
from PyQt6.QtCore import Qt


class HostDialog(QDialog):
    """添加/编辑主机对话框"""

    def __init__(self, parent=None, host_data: dict = None):
        super().__init__(parent)
        self.host_data = host_data
        self.is_edit_mode = host_data is not None
        self.setup_ui()
        if self.is_edit_mode:
            self.load_host_data()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("编辑主机" if self.is_edit_mode else "添加主机")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: 生产服务器")
        form_layout.addRow("名称:", self.name_input)

        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如: 192.168.1.100")
        form_layout.addRow("主机地址:", self.host_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        form_layout.addRow("端口:", self.port_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("例如: root")
        form_layout.addRow("用户名:", self.username_input)

        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["密码认证", "密钥认证"])
        self.auth_type_combo.currentIndexChanged.connect(self._on_auth_type_changed)
        form_layout.addRow("认证方式:", self.auth_type_combo)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("输入SSH密码")
        form_layout.addRow("密码:", self.password_input)

        key_layout = QHBoxLayout()
        self.key_path_input = QLineEdit()
        self.key_path_input.setPlaceholderText("选择私钥文件")
        self.key_path_input.setVisible(False)
        key_layout.addWidget(self.key_path_input)

        self.browse_button = QPushButton("浏览...")
        self.browse_button.setVisible(False)
        self.browse_button.clicked.connect(self._browse_key_file)
        key_layout.addWidget(self.browse_button)

        self.key_label = QLabel("私钥路径:")
        self.key_label.setVisible(False)
        form_layout.addRow(self.key_label, key_layout)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("可选的描述信息")
        self.description_input.setMaximumHeight(80)
        form_layout.addRow("描述:", self.description_input)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_auth_type_changed(self, index):
        """认证方式改变"""
        is_key_auth = index == 1
        self.password_input.setVisible(not is_key_auth)
        self.key_path_input.setVisible(is_key_auth)
        self.browse_button.setVisible(is_key_auth)
        self.key_label.setVisible(is_key_auth)

        if is_key_auth:
            self.layout().itemAt(0).itemAt(5).labelForField().setVisible(False)
        else:
            self.layout().itemAt(0).itemAt(5).labelForField().setVisible(True)

    def _browse_key_file(self):
        """浏览私钥文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择私钥文件", "", "所有文件 (*)"
        )
        if file_path:
            self.key_path_input.setText(file_path)

    def load_host_data(self):
        """加载主机数据"""
        if not self.host_data:
            return

        self.name_input.setText(self.host_data.get('name', ''))
        self.host_input.setText(self.host_data.get('host', ''))
        self.port_input.setValue(self.host_data.get('port', 22))
        self.username_input.setText(self.host_data.get('username', ''))

        auth_type = self.host_data.get('auth_type', 'password')
        self.auth_type_combo.setCurrentIndex(0 if auth_type == 'password' else 1)

        self.password_input.setText(self.host_data.get('password', ''))
        self.key_path_input.setText(self.host_data.get('private_key_path', ''))
        self.description_input.setPlainText(self.host_data.get('description', ''))

    def get_host_data(self) -> dict:
        """获取主机数据"""
        auth_type = "password" if self.auth_type_combo.currentIndex() == 0 else "key"

        data = {
            'name': self.name_input.text().strip(),
            'host': self.host_input.text().strip(),
            'port': self.port_input.value(),
            'username': self.username_input.text().strip(),
            'auth_type': auth_type,
            'password': self.password_input.text() if auth_type == 'password' else '',
            'private_key_path': self.key_path_input.text() if auth_type == 'key' else '',
            'description': self.description_input.toPlainText().strip()
        }

        if self.is_edit_mode and self.host_data:
            data['id'] = self.host_data['id']

        return data

    def validate(self) -> tuple[bool, str]:
        """验证输入"""
        data = self.get_host_data()

        if not data['name']:
            return False, "请输入主机名称"
        if not data['host']:
            return False, "请输入主机地址"
        if not data['username']:
            return False, "请输入用户名"
        if data['auth_type'] == 'password' and not data['password']:
            return False, "请输入密码"
        if data['auth_type'] == 'key' and not data['private_key_path']:
            return False, "请选择私钥文件"

        return True, ""

    def accept(self):
        """确认对话框"""
        valid, message = self.validate()
        if not valid:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "验证失败", message)
            return
        super().accept()
