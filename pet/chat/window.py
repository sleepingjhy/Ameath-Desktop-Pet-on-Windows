"""独立聊天窗口。"""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow

from .session import ChatSession
from .widgets import ChatPanel


class ChatWindow(QMainWindow):
    """桌宠聊天独立窗口。"""

    def __init__(self, session: ChatSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.chat_panel = ChatPanel(session=self.session, parent=self)
        self.setCentralWidget(self.chat_panel)

        self.setWindowTitle("Ameath Chat")
        self.setMinimumSize(520, 700)

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def prepare_for_exit(self):
        if hasattr(self, "chat_panel") and self.chat_panel is not None:
            self.chat_panel.dispose()
        self.session.clear()

    def closeEvent(self, event: QCloseEvent):
        self.prepare_for_exit()
        event.accept()
