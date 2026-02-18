"""该模块负责系统托盘控制。提供打开、音乐控制和退出菜单动作。"""
# EN: This module manages the system tray, including open, music controls, and exit actions.

from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .i18n import tr
from .music_player import MODE_ICONS, PLAY_MODE_LIST, PLAY_MODE_RANDOM, PLAY_MODE_SINGLE


class TrayController:
    """托盘控制器。封装托盘图标与托盘菜单行为。"""
    """EN: Tray controller that encapsulates tray icon and context menu behavior."""

    def __init__(self, icon_path, on_open, on_exit, settings_store=None, music_player=None):
        """初始化托盘图标和菜单。"""
        """EN: Initialize tray icon and tray menu."""
        self.on_open = on_open
        self.on_exit = on_exit
        self.settings_store = settings_store
        self.music_player = music_player

        self.tray = QSystemTrayIcon(QIcon(str(icon_path)))
        self.tray.setToolTip("Ameath Desktop Pet")

        self.menu = QMenu()
        self.menu.aboutToShow.connect(self._refresh_texts)
        self.open_action = QAction(self._tr("tray.open"), self.menu)
        self.open_action.triggered.connect(self.on_open)
        self.menu.addAction(self.open_action)

        self.music_menu = self.menu.addMenu(self._tr("tray.music"))
        self.music_track_action = QAction(self._tr("tray.music.no_track"), self.music_menu)
        self.music_track_action.setEnabled(False)
        self.music_menu.addAction(self.music_track_action)
        self.music_menu.addSeparator()

        self.music_prev_action = QAction(self._tr("tray.music.prev"), self.music_menu)
        self.music_prev_action.triggered.connect(self._on_music_prev)
        self.music_menu.addAction(self.music_prev_action)

        self.music_play_pause_action = QAction(self._tr("tray.music.play"), self.music_menu)
        self.music_play_pause_action.triggered.connect(self._on_music_toggle)
        self.music_menu.addAction(self.music_play_pause_action)

        self.music_next_action = QAction(self._tr("tray.music.next"), self.music_menu)
        self.music_next_action.triggered.connect(self._on_music_next)
        self.music_menu.addAction(self.music_next_action)

        self.music_menu.addSeparator()

        self.music_mode_list_action = QAction(self.music_mode_text(PLAY_MODE_LIST), self.music_menu)
        self.music_mode_list_action.setCheckable(True)
        self.music_mode_list_action.triggered.connect(lambda checked=False: self._on_music_set_mode(PLAY_MODE_LIST))
        self.music_menu.addAction(self.music_mode_list_action)

        self.music_mode_single_action = QAction(self.music_mode_text(PLAY_MODE_SINGLE), self.music_menu)
        self.music_mode_single_action.setCheckable(True)
        self.music_mode_single_action.triggered.connect(lambda checked=False: self._on_music_set_mode(PLAY_MODE_SINGLE))
        self.music_menu.addAction(self.music_mode_single_action)

        self.music_mode_random_action = QAction(self.music_mode_text(PLAY_MODE_RANDOM), self.music_menu)
        self.music_mode_random_action.setCheckable(True)
        self.music_mode_random_action.triggered.connect(lambda checked=False: self._on_music_set_mode(PLAY_MODE_RANDOM))
        self.music_menu.addAction(self.music_mode_random_action)

        self.menu.addSeparator()

        self.exit_action = QAction(self._tr("tray.exit"), self.menu)
        self.exit_action.triggered.connect(self.on_exit)
        self.menu.addAction(self.exit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

        if self.music_player is not None:
            self.music_player.track_changed.connect(self._refresh_music_menu)
            self.music_player.state_changed.connect(self._refresh_music_menu)
            self.music_player.mode_changed.connect(self._refresh_music_menu)
            self.music_player.playlist_reordered.connect(self._refresh_music_menu)

        self._refresh_texts()
        self._refresh_music_menu()

    def show(self):
        """显示托盘图标。"""
        """EN: Show tray icon."""
        self._refresh_texts()
        self._refresh_music_menu()
        self.tray.show()

    def hide(self):
        """隐藏托盘图标。"""
        """EN: Hide tray icon."""
        self.tray.hide()

    def notify_minimized(self):
        """提示应用已最小化到托盘。"""
        """EN: Show notification that app has been minimized to tray."""
        self._refresh_texts()
        self.tray.showMessage(
            "Ameath Desktop Pet",
            self._tr("tray.minimized"),
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _on_activated(self, reason):
        """托盘图标双击时打开主界面。"""
        """EN: Open app window on tray icon double-click."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.on_open()

    def _on_music_prev(self):
        """托盘菜单上一首。"""
        """EN: Play previous track from tray menu."""
        if self.music_player is not None:
            self.music_player.prev()

    def _on_music_toggle(self):
        """托盘菜单播放/暂停。"""
        """EN: Toggle play/pause from tray menu."""
        if self.music_player is not None:
            self.music_player.toggle_pause()

    def _on_music_next(self):
        """托盘菜单下一首。"""
        """EN: Play next track from tray menu."""
        if self.music_player is not None:
            self.music_player.next()

    def _on_music_set_mode(self, mode: str):
        """托盘菜单切换播放模式。"""
        """EN: Switch playback mode from tray menu."""
        if self.music_player is not None:
            self.music_player.set_mode(mode)

    def music_mode_text(self, mode: str) -> str:
        """生成播放模式菜单文本。"""
        """EN: Build text for a playback mode menu action."""
        if mode == PLAY_MODE_LIST:
            return f"{MODE_ICONS[PLAY_MODE_LIST]} {self._tr('tray.music.mode.list')}"
        if mode == PLAY_MODE_SINGLE:
            return f"{MODE_ICONS[PLAY_MODE_SINGLE]} {self._tr('tray.music.mode.single')}"
        return f"{MODE_ICONS[PLAY_MODE_RANDOM]} {self._tr('tray.music.mode.random')}"

    def _refresh_music_menu(self, *args):
        """刷新托盘音乐菜单状态和可用性。"""
        """EN: Refresh tray music menu state and availability."""
        has_player = self.music_player is not None
        has_tracks = bool(has_player and self.music_player.playlist)

        self.music_prev_action.setEnabled(has_tracks)
        self.music_play_pause_action.setEnabled(has_tracks)
        self.music_next_action.setEnabled(has_tracks)
        self.music_mode_list_action.setEnabled(has_tracks)
        self.music_mode_single_action.setEnabled(has_tracks)
        self.music_mode_random_action.setEnabled(has_tracks)

        if not has_tracks:
            self.music_track_action.setText(self._tr("tray.music.no_track"))
            self.music_play_pause_action.setText(self._tr("tray.music.play"))
            self.music_mode_list_action.setChecked(False)
            self.music_mode_single_action.setChecked(False)
            self.music_mode_random_action.setChecked(False)
            return

        self.music_track_action.setText(self.music_player.current_track_name)
        self.music_play_pause_action.setText(
            self._tr("tray.music.pause") if self.music_player.is_playing else self._tr("tray.music.play")
        )
        current_mode = self.music_player.play_mode
        self.music_mode_list_action.setChecked(current_mode == PLAY_MODE_LIST)
        self.music_mode_single_action.setChecked(current_mode == PLAY_MODE_SINGLE)
        self.music_mode_random_action.setChecked(current_mode == PLAY_MODE_RANDOM)

    def dispose(self):
        """释放托盘控制器信号连接和菜单资源。"""
        """EN: Release tray signal connections and menu resources."""
        if self.music_player is not None:
            try:
                self.music_player.track_changed.disconnect(self._refresh_music_menu)
            except Exception:
                pass
            try:
                self.music_player.state_changed.disconnect(self._refresh_music_menu)
            except Exception:
                pass
            try:
                self.music_player.mode_changed.disconnect(self._refresh_music_menu)
            except Exception:
                pass
            try:
                self.music_player.playlist_reordered.disconnect(self._refresh_music_menu)
            except Exception:
                pass

        try:
            self.tray.activated.disconnect(self._on_activated)
        except Exception:
            pass
        try:
            self.menu.aboutToShow.disconnect(self._refresh_texts)
        except Exception:
            pass

        try:
            self.open_action.triggered.disconnect(self.on_open)
        except Exception:
            pass
        try:
            self.exit_action.triggered.disconnect(self.on_exit)
        except Exception:
            pass
        try:
            self.music_prev_action.triggered.disconnect(self._on_music_prev)
        except Exception:
            pass
        try:
            self.music_play_pause_action.triggered.disconnect(self._on_music_toggle)
        except Exception:
            pass
        try:
            self.music_next_action.triggered.disconnect(self._on_music_next)
        except Exception:
            pass

        self.tray.hide()
        self.tray.setContextMenu(None)
        self.menu.deleteLater()

    def _tr(self, key: str) -> str:
        """读取当前语言文案。"""
        """EN: Resolve translated text for the current language."""
        language = "zh-CN"
        if self.settings_store is not None and hasattr(self.settings_store, "get_language"):
            language = self.settings_store.get_language()
        return tr(language, key)

    def _refresh_texts(self):
        """刷新托盘菜单静态文案。"""
        """EN: Refresh static tray menu texts."""
        self.open_action.setText(self._tr("tray.open"))
        self.music_menu.setTitle(self._tr("tray.music"))
        self.music_prev_action.setText(self._tr("tray.music.prev"))
        self.music_next_action.setText(self._tr("tray.music.next"))
        self.music_mode_list_action.setText(self.music_mode_text(PLAY_MODE_LIST))
        self.music_mode_single_action.setText(self.music_mode_text(PLAY_MODE_SINGLE))
        self.music_mode_random_action.setText(self.music_mode_text(PLAY_MODE_RANDOM))
        self.exit_action.setText(self._tr("tray.exit"))
        self._refresh_music_menu()
