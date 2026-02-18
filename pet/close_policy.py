"""该模块负责关闭策略决策。支持询问用户并记住选择。"""
# EN: This module handles close-policy decisions, including prompting the user and remembering the selected action.

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .i18n import tr
from .settings_store import SettingsStore


class CloseChoiceDialog(QDialog):
    """关闭选择弹窗。提供退出、最小化托盘和取消。"""
    """EN: Close-choice dialog that provides Quit, Minimize to Tray, and Cancel options."""

    def __init__(self, language: str = "zh-CN", parent=None):
        """初始化弹窗布局与按钮。"""
        """EN: Initialize the popup layout with buttons."""
        super().__init__(parent)
        self.setWindowTitle(tr(language, "close.title"))
        self.setModal(True)
        self.setMinimumWidth(360)

        self.selection = "cancel"

        layout = QVBoxLayout(self)

        label = QLabel(tr(language, "close.prompt"))
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(label)

        description = QLabel(tr(language, "close.desc"))
        description.setWordWrap(True)
        layout.addWidget(description)

        self.remember_checkbox = QCheckBox(tr(language, "close.remember"))
        layout.addWidget(self.remember_checkbox)

        button_row = QHBoxLayout()

        self.quit_button = QPushButton(tr(language, "close.quit"))
        self.quit_button.clicked.connect(self._select_quit)
        button_row.addWidget(self.quit_button)

        self.tray_button = QPushButton(tr(language, "close.tray"))
        self.tray_button.setDefault(True)
        self.tray_button.clicked.connect(self._select_tray)
        button_row.addWidget(self.tray_button)

        self.cancel_button = QPushButton(tr(language, "close.cancel"))
        self.cancel_button.clicked.connect(self._select_cancel)
        button_row.addWidget(self.cancel_button)

        layout.addLayout(button_row)

    def _select_quit(self):
        """选择退出并关闭弹窗。"""
        """EN: Select Exit and close the pop-up."""
        self.selection = "quit"
        self.accept()

    def _select_tray(self):
        """选择最小化托盘并关闭弹窗。"""
        """EN: Select the minimize tray and close the popup."""
        self.selection = "tray"
        self.accept()

    def _select_cancel(self):
        """选择取消并关闭弹窗。"""
        """EN: Select Cancel and close the pop-up."""
        self.selection = "cancel"
        self.reject()


class ClosePolicyManager:
    """关闭策略管理器。根据配置返回关闭决策。"""
    """EN: Close policy manager that returns the final close action based on configuration."""

    def __init__(self, settings_store: SettingsStore):
        """绑定设置存储实例。"""
        """EN: Binds the settings store instance."""
        self.settings_store = settings_store

    def decide(self, parent=None) -> str:
        """获取本次关闭决策。返回 quit、tray 或 cancel。"""
        """EN: Get this closure decision. Returns quit, tray, or cancel."""
        behavior = self.settings_store.get_close_behavior()
        if behavior in {"quit", "tray"}:
            return behavior

        dialog = CloseChoiceDialog(language=self.settings_store.get_language(), parent=parent)
        dialog.exec()

        choice = dialog.selection
        if choice in {"quit", "tray"} and dialog.remember_checkbox.isChecked():
            self.settings_store.set_close_behavior(choice)

        return choice
