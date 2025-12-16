from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QKeyEvent, QColor, QTextCharFormat
import re


class TerminalWidget(QTextEdit):
    """终端显示组件"""

    command_entered = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()
        self.current_format = QTextCharFormat()
        self.default_fg_color = QColor("#d4d4d4")
        self.default_bg_color = QColor("#1e1e1e")
        self.setup_colors()
        self.setup_ui()

    def setup_colors(self):
        """设置ANSI颜色映射"""
        self.ansi_colors = {
            # 前景色
            30: QColor("#000000"),  # 黑色
            31: QColor("#cd3131"),  # 红色
            32: QColor("#0dbc79"),  # 绿色
            33: QColor("#e5e510"),  # 黄色
            34: QColor("#2472c8"),  # 蓝色
            35: QColor("#bc3fbc"),  # 品红
            36: QColor("#11a8cd"),  # 青色
            37: QColor("#e5e5e5"),  # 白色
            # 高亮前景色
            90: QColor("#666666"),  # 亮黑
            91: QColor("#f14c4c"),  # 亮红
            92: QColor("#23d18b"),  # 亮绿
            93: QColor("#f5f543"),  # 亮黄
            94: QColor("#3b8eea"),  # 亮蓝
            95: QColor("#d670d6"),  # 亮品红
            96: QColor("#29b8db"),  # 亮青
            97: QColor("#ffffff"),  # 亮白
        }

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

        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)

        # 设置默认文本格式
        self.current_format.setForeground(self.default_fg_color)

    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件 - 将所有输入直接发送到SSH"""
        key = event.key()
        modifiers = event.modifiers()
        text = event.text()

        # Ctrl+C
        if key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.command_entered.emit(b'\x03')
            return

        # Ctrl+D
        if key == Qt.Key.Key_D and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.command_entered.emit(b'\x04')
            return

        # Ctrl+Z
        if key == Qt.Key.Key_Z and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.command_entered.emit(b'\x1a')
            return

        # Ctrl+L (清屏)
        if key == Qt.Key.Key_L and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.command_entered.emit(b'\x0c')
            return

        # Ctrl+V (粘贴)
        if key == Qt.Key.Key_V and modifiers == Qt.KeyboardModifier.ControlModifier:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text:
                try:
                    self.command_entered.emit(text.encode('utf-8'))
                except:
                    pass
            return

        # Enter/Return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.command_entered.emit(b'\r')
            return

        # Backspace
        if key == Qt.Key.Key_Backspace:
            self.command_entered.emit(b'\x08')
            return

        # Tab
        if key == Qt.Key.Key_Tab:
            self.command_entered.emit(b'\t')
            return

        # Arrow keys
        if key == Qt.Key.Key_Up:
            self.command_entered.emit(b'\x1b[A')
            return
        if key == Qt.Key.Key_Down:
            self.command_entered.emit(b'\x1b[B')
            return
        if key == Qt.Key.Key_Right:
            self.command_entered.emit(b'\x1b[C')
            return
        if key == Qt.Key.Key_Left:
            self.command_entered.emit(b'\x1b[D')
            return

        # Home/End
        if key == Qt.Key.Key_Home:
            self.command_entered.emit(b'\x1b[H')
            return
        if key == Qt.Key.Key_End:
            self.command_entered.emit(b'\x1b[F')
            return

        # Delete
        if key == Qt.Key.Key_Delete:
            self.command_entered.emit(b'\x1b[3~')
            return

        # PageUp/PageDown
        if key == Qt.Key.Key_PageUp:
            self.command_entered.emit(b'\x1b[5~')
            return
        if key == Qt.Key.Key_PageDown:
            self.command_entered.emit(b'\x1b[6~')
            return

        # 普通字符
        if text:
            try:
                self.command_entered.emit(text.encode('utf-8'))
            except:
                pass

    def append_output(self, text: str):
        """添加输出文本，解析ANSI转义序列"""
        # 规范化换行符：将 \r\n 和单独的 \r 都转换为 \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 正则表达式匹配ANSI转义序列
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=>]|\x1b\[[?][0-9;]*[a-zA-Z]')

        pos = 0
        for match in ansi_escape.finditer(text):
            # 插入转义序列之前的普通文本
            if match.start() > pos:
                plain_text = text[pos:match.start()]
                # 处理backspace和其他控制字符
                cursor = self._process_text_with_backspace(plain_text, cursor)

            # 处理转义序列
            escape_seq = match.group()
            self._process_escape_sequence(escape_seq)

            pos = match.end()

        # 插入剩余的普通文本
        if pos < len(text):
            remaining_text = text[pos:]
            # 处理backspace和其他控制字符
            cursor = self._process_text_with_backspace(remaining_text, cursor)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _process_text_with_backspace(self, text: str, cursor: QTextCursor) -> QTextCursor:
        """处理包含控制字符的文本"""
        i = 0
        while i < len(text):
            char = text[i]

            if char == '\x08':
                # Backspace: 删除前一个字符
                if not cursor.atStart():
                    cursor.deletePreviousChar()
            elif char == '\x7f':
                # DEL字符：忽略，避免显示为方框
                pass
            elif char == '\x07':
                # Bell响铃字符：忽略
                pass
            elif ord(char) >= 32 or char in '\n\t':
                # 可打印字符或常用控制字符（换行、制表符）
                # 注意：\r 已经在 append_output 中被转换为 \n
                cursor.insertText(char, self.current_format)
            # 其他控制字符默认忽略

            i += 1

        return cursor

    def _process_escape_sequence(self, seq: str):
        """处理ANSI转义序列"""
        # 清屏序列：ESC [ 2 J 或 ESC [ H ESC [ 2 J
        if seq == '\x1b[2J' or seq == '\x1b[H':
            if seq == '\x1b[2J':
                self.clear()
                self.current_format = QTextCharFormat()
                self.current_format.setForeground(self.default_fg_color)
            return

        # 清除行序列：ESC [ K
        if seq == '\x1b[K':
            return

        # 光标移动序列 - 暂时忽略
        if seq.startswith('\x1b[') and seq[-1] in 'ABCDEFGH':
            return

        # CSI序列：ESC [ ... m (SGR - 设置图形属性)
        if seq.startswith('\x1b[') and seq.endswith('m'):
            params = seq[2:-1]
            if not params:
                params = '0'

            codes = [int(code) if code else 0 for code in params.split(';')]

            for code in codes:
                if code == 0:  # 重置
                    self.current_format = QTextCharFormat()
                    self.current_format.setForeground(self.default_fg_color)
                elif code == 1:  # 粗体
                    self.current_format.setFontWeight(QFont.Weight.Bold)
                elif code == 2:  # 暗淡
                    pass
                elif code == 3:  # 斜体
                    self.current_format.setFontItalic(True)
                elif code == 4:  # 下划线
                    self.current_format.setFontUnderline(True)
                elif code == 22:  # 正常强度
                    self.current_format.setFontWeight(QFont.Weight.Normal)
                elif code == 23:  # 非斜体
                    self.current_format.setFontItalic(False)
                elif code == 24:  # 非下划线
                    self.current_format.setFontUnderline(False)
                elif code in self.ansi_colors:  # 前景色
                    self.current_format.setForeground(self.ansi_colors[code])
                elif code == 39:  # 默认前景色
                    self.current_format.setForeground(self.default_fg_color)
                elif 40 <= code <= 47:  # 背景色
                    bg_color = self.ansi_colors.get(code - 10)
                    if bg_color:
                        self.current_format.setBackground(bg_color)
                elif code == 49:  # 默认背景色
                    self.current_format.clearBackground()

    def clear_terminal(self):
        """清空终端"""
        self.clear()
        self.input_buffer = ""

    def set_readonly(self, readonly: bool):
        """设置只读模式"""
        self.setReadOnly(readonly)
