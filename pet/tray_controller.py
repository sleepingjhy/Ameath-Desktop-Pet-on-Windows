"""该模块负责系统托盘控制。提供打开和退出两个菜单动作。"""

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayController:
    """托盘控制器。封装托盘图标与托盘菜单行为。"""

    def __init__(self, icon_path, on_open, on_exit):
        """初始化托盘图标和菜单。"""
        self.on_open = on_open
        self.on_exit = on_exit

        self.tray = QSystemTrayIcon(QIcon(str(icon_path)))
        self.tray.setToolTip("Ameath Desktop Pet")

        self.menu = QMenu()
        self.open_action = QAction("打开", self.menu)
        self.open_action.triggered.connect(self.on_open)
        self.menu.addAction(self.open_action)

        self.menu.addSeparator()

        self.exit_action = QAction("退出", self.menu)
        self.exit_action.triggered.connect(self.on_exit)
        self.menu.addAction(self.exit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

    def show(self):
        """显示托盘图标。"""
        self.tray.show()

    def hide(self):
        """隐藏托盘图标。"""
        self.tray.hide()

    def notify_minimized(self):
        """提示应用已最小化到托盘。"""
        self.tray.showMessage(
            "Ameath Desktop Pet",
            "应用已最小化到系统托盘，可右键托盘图标选择“打开”。",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _on_activated(self, reason):
        """托盘图标双击时打开主界面。"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.on_open()
