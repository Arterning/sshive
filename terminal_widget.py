from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette


class TerminalWidget(QTextEdit):
    """终端显示组件"""

    command_entered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.input_buffer = ""
        self.command_history = []
        self.history_index = -1

    def setup_ui(self):
        """设置UI样式"""
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 5px;
            }
        """)

        self.setReadOnly(False)
        self.setUndoRedoEnabled(False)

    def keyPressEvent(self, event):
        """处理键盘事件"""
        key = event.key()
        text = event.text()

        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            command = self.input_buffer + "\n"
            self.command_entered.emit(command)
            self.command_history.append(self.input_buffer)
            self.history_index = len(self.command_history)
            self.input_buffer = ""
            return

        elif key == Qt.Key.Key_Backspace:
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
                command = "\b"
                self.command_entered.emit(command)
            return

        elif key == Qt.Key.Key_Up:
            if self.history_index > 0:
                self.history_index -= 1
                self._replace_input_line(self.command_history[self.history_index])
            return

        elif key == Qt.Key.Key_Down:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self._replace_input_line(self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self._replace_input_line("")
            return

        elif key == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.command_entered.emit("\x03")
            self.input_buffer = ""
            return

        elif key == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.command_entered.emit("\x04")
            return

        elif text and text.isprintable():
            self.input_buffer += text
            self.command_entered.emit(text)

    def _replace_input_line(self, text: str):
        """替换当前输入行"""
        clear_command = "\b" * len(self.input_buffer) + " " * len(self.input_buffer) + "\b" * len(self.input_buffer)
        self.command_entered.emit(clear_command + text)
        self.input_buffer = text

    def append_output(self, text: str):
        """添加输出文本"""
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(text)
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.ensureCursorVisible()

    def clear_terminal(self):
        """清空终端"""
        self.clear()
        self.input_buffer = ""

    def set_readonly(self, readonly: bool):
        """设置只读模式"""
        self.setReadOnly(readonly)
