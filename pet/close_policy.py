"""该模块负责关闭策略决策。支持询问用户并记住选择。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .settings_store import SettingsStore


class CloseChoiceDialog(QDialog):
    """关闭选择弹窗。提供退出、最小化托盘和取消。"""

    def __init__(self, parent=None):
        """初始化弹窗布局与按钮。"""
        super().__init__(parent)
        self.setWindowTitle("关闭应用")
        self.setModal(True)
        self.setMinimumWidth(360)

        self.selection = "cancel"

        layout = QVBoxLayout(self)

        label = QLabel("请选择关闭方式：")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label)

        description = QLabel("你可以退出应用，或最小化到系统托盘继续后台运行。")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.remember_checkbox = QCheckBox("记住我的选择")
        layout.addWidget(self.remember_checkbox)

        button_row = QHBoxLayout()

        self.quit_button = QPushButton("退出应用")
        self.quit_button.clicked.connect(self._select_quit)
        button_row.addWidget(self.quit_button)

        self.tray_button = QPushButton("最小化到托盘")
        self.tray_button.setDefault(True)
        self.tray_button.clicked.connect(self._select_tray)
        button_row.addWidget(self.tray_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self._select_cancel)
        button_row.addWidget(self.cancel_button)

        layout.addLayout(button_row)

    def _select_quit(self):
        """选择退出并关闭弹窗。"""
        self.selection = "quit"
        self.accept()

    def _select_tray(self):
        """选择最小化托盘并关闭弹窗。"""
        self.selection = "tray"
        self.accept()

    def _select_cancel(self):
        """选择取消并关闭弹窗。"""
        self.selection = "cancel"
        self.reject()


class ClosePolicyManager:
    """关闭策略管理器。根据配置返回关闭决策。"""

    def __init__(self, settings_store: SettingsStore):
        """绑定设置存储实例。"""
        self.settings_store = settings_store

    def decide(self, parent=None) -> str:
        """获取本次关闭决策。返回 quit、tray 或 cancel。"""
        behavior = self.settings_store.get_close_behavior()
        if behavior in {"quit", "tray"}:
            return behavior

        dialog = CloseChoiceDialog(parent)
        dialog.exec()

        choice = dialog.selection
        if choice in {"quit", "tray"} and dialog.remember_checkbox.isChecked():
            self.settings_store.set_close_behavior(choice)

        return choice
