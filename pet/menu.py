"""该模块负责构建右键菜单。包含显示模式与多开控制。"""
"""EN: This module builds the right-click context menu, including display modes and multi-instance controls."""

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSlider, QWidgetAction, QLabel, QHBoxLayout, QWidget
from PySide6.QtCore import Qt

from .config import (
    DISPLAY_MODE_ALWAYS_ON_TOP,
    DISPLAY_MODE_DESKTOP_ONLY,
    DISPLAY_MODE_FULLSCREEN_HIDE,
    INSTANCE_COUNT_MAX,
    INSTANCE_COUNT_MIN,
    OPACITY_MENU_MIN,
    OPACITY_MENU_STEP,
    OPACITY_PERCENT_MAX,
    SCALE_MAX,
    SCALE_MIN,
    SCALE_STEP,
)
from .i18n import get_language_items, normalize_language, tr


def build_context_menu(pet, music_player=None, language: str = "zh-CN", on_set_language=None) -> QMenu:
    """构建并返回右键菜单。菜单项绑定桌宠实例回调。"""
    """EN: Build and return to the context menu. Menu item binding table pet instance callback."""
    language = normalize_language(language)
    menu = QMenu(pet)

    if hasattr(pet, "on_open_main") and callable(pet.on_open_main):
        open_main_action = QAction(tr(language, "app.open_main"), menu)
        open_main_action.triggered.connect(pet.on_open_main)
        menu.addAction(open_main_action)
        menu.addSeparator()

    stop_action = QAction(menu)
    stop_action.setObjectName("toggleMoveAction")
    stop_action.triggered.connect(pet.on_toggle_move_current)
    menu.addAction(stop_action)

    follow_action = QAction(tr(language, "menu.follow_mouse"), menu)
    follow_action.setObjectName("followAction")
    follow_action.setCheckable(True)
    follow_action.setChecked(pet.state.follow_mouse)
    follow_action.triggered.connect(pet.on_toggle_follow)
    menu.addAction(follow_action)

    # 创建缩放二级菜单。范围 0.1x~2.0x，步进 0.1x。
    # EN: Creates a zoom secondary menu. Range 0.1x~2.0x, step 0.1x.
    scale_menu = menu.addMenu(tr(language, "menu.scale"))
    count = int(round((SCALE_MAX - SCALE_MIN) / SCALE_STEP)) + 1
    for i in range(count):
        value = round(SCALE_MIN + i * SCALE_STEP, 1)
        action = QAction(f"{value:.1f}x", scale_menu)
        action.setCheckable(True)
        action.setChecked(abs(pet.scale_factor - value) < 1e-6)
        action.triggered.connect(lambda checked=False, s=value: pet.on_set_scale(s))
        scale_menu.addAction(action)

    opacity_menu = menu.addMenu(tr(language, "menu.opacity"))
    current_opacity = (
        pet.get_opacity_percent()
        if hasattr(pet, "get_opacity_percent") and callable(pet.get_opacity_percent)
        else OPACITY_PERCENT_MAX
    )
    opacity_group = QActionGroup(opacity_menu)
    opacity_group.setExclusive(True)
    for value in range(OPACITY_MENU_MIN, OPACITY_PERCENT_MAX + 1, OPACITY_MENU_STEP):
        action = QAction(f"{value}%", opacity_menu)
        action.setCheckable(True)
        action.setChecked(int(current_opacity) == value)
        action.triggered.connect(lambda checked=False, p=value: pet.on_set_opacity_percent(p))
        opacity_group.addAction(action)
        opacity_menu.addAction(action)

    display_mode_menu = menu.addMenu(tr(language, "menu.display_mode"))
    current_mode = (
        pet.get_display_mode()
        if hasattr(pet, "get_display_mode") and callable(pet.get_display_mode)
        else DISPLAY_MODE_ALWAYS_ON_TOP
    )
    display_group = QActionGroup(display_mode_menu)
    display_group.setExclusive(True)

    display_items = [
        (tr(language, "menu.display.always_top"), DISPLAY_MODE_ALWAYS_ON_TOP),
        (tr(language, "menu.display.fullscreen_hide"), DISPLAY_MODE_FULLSCREEN_HIDE),
        (tr(language, "menu.display.desktop_only"), DISPLAY_MODE_DESKTOP_ONLY),
    ]
    for text, mode in display_items:
        action = QAction(text, display_mode_menu)
        action.setCheckable(True)
        action.setChecked(current_mode == mode)
        action.triggered.connect(lambda checked=False, m=mode: pet.on_set_display_mode(m))
        display_group.addAction(action)
        display_mode_menu.addAction(action)

    multi_instance_menu = menu.addMenu(tr(language, "menu.multi_instance"))
    set_count_action = QAction(
        tr(language, "menu.set_instance_count", min_count=INSTANCE_COUNT_MIN, max_count=INSTANCE_COUNT_MAX),
        multi_instance_menu,
    )
    set_count_action.triggered.connect(pet.on_set_instance_count_prompt)
    multi_instance_menu.addAction(set_count_action)

    # 创建开机自启开关。勾选状态由当前系统配置决定。
    # EN: Create a power-on auto-on switch. The checked status is determined by the current system configuration.
    autostart_action = QAction(tr(language, "menu.autostart"), menu)
    autostart_action.setCheckable(True)
    autostart_action.setChecked(pet.get_autostart_enabled())
    autostart_action.triggered.connect(pet.on_toggle_autostart)
    menu.addAction(autostart_action)

    language_menu = menu.addMenu(tr(language, "menu.language"))
    language_group = QActionGroup(language_menu)
    language_group.setExclusive(True)
    current_language = language
    for code, display_name in get_language_items():
        language_action = QAction(display_name, language_menu)
        language_action.setCheckable(True)
        language_action.setChecked(code == current_language)
        if on_set_language is not None:
            language_action.triggered.connect(lambda checked=False, c=code: on_set_language(c))
        language_group.addAction(language_action)
        language_menu.addAction(language_action)

    # 将关闭项置于分隔线后。降低误触风险。
    # EN: Place the closing item after the separator line. Reduce the risk of accidental contact.
    menu.addSeparator()

    close_menu = menu.addMenu(tr(language, "menu.close"))

    close_current_action = QAction(tr(language, "menu.close_current"), close_menu)
    close_current_action.triggered.connect(pet.on_close_current_pet)
    close_menu.addAction(close_current_action)

    close_random_action = QAction(tr(language, "menu.close_random"), close_menu)
    close_random_action.triggered.connect(pet.on_close_random_pets_prompt)
    close_menu.addAction(close_random_action)

    close_all_action = QAction(tr(language, "menu.close_all"), close_menu)
    close_all_action.triggered.connect(pet.on_close_all_pets)
    close_menu.addAction(close_all_action)

    # 音乐子菜单（简化控制）
    # EN: Music Submenu (Simplified Control)
    if music_player is not None:
        menu.addSeparator()
        music_menu = menu.addMenu(tr(language, "menu.music"))

        # 当前歌曲名（只读）
        # EN: Current song title (read-only)
        track_name_action = QAction(music_player.current_track_name, music_menu)
        track_name_action.setObjectName("musicTrackNameAction")
        track_name_action.setEnabled(False)
        music_menu.addAction(track_name_action)

        music_menu.addSeparator()

        # 上一首
        # EN: Previous
        prev_action = QAction(tr(language, "menu.music.prev"), music_menu)
        prev_action.triggered.connect(music_player.prev)
        music_menu.addAction(prev_action)

        # 播放/暂停（动态文字）
        # EN: Play/Pause (Dynamic Text)
        play_pause_text = tr(language, "menu.music.pause") if music_player.is_playing else tr(language, "menu.music.play")
        play_pause_action = QAction(play_pause_text, music_menu)
        play_pause_action.setObjectName("musicPlayPauseAction")
        play_pause_action.triggered.connect(music_player.toggle_pause)
        music_menu.addAction(play_pause_action)

        # 下一首
        # EN: up next
        next_action = QAction(tr(language, "menu.music.next"), music_menu)
        next_action.triggered.connect(music_player.next)
        music_menu.addAction(next_action)

        music_menu.addSeparator()

        # 播放模式（互斥单选）
        # EN: Play Mode (Mutually Exclusive Radio)
        from .music_player import PLAY_MODE_LIST, PLAY_MODE_SINGLE, PLAY_MODE_RANDOM, MODE_ICONS
        mode_group = QActionGroup(music_menu)
        mode_group.setExclusive(True)
        for mode_key, mode_label in [
            (PLAY_MODE_LIST, f"{MODE_ICONS[PLAY_MODE_LIST]} {tr(language, 'menu.music.mode.list')}"),
            (PLAY_MODE_SINGLE, f"{MODE_ICONS[PLAY_MODE_SINGLE]} {tr(language, 'menu.music.mode.single')}"),
            (PLAY_MODE_RANDOM, f"{MODE_ICONS[PLAY_MODE_RANDOM]} {tr(language, 'menu.music.mode.random')}"),
        ]:
            mode_action = QAction(mode_label, music_menu)
            mode_action.setCheckable(True)
            mode_action.setChecked(music_player.play_mode == mode_key)
            mode_action.triggered.connect(lambda checked=False, m=mode_key: music_player.set_mode(m))
            mode_group.addAction(mode_action)
            music_menu.addAction(mode_action)

        music_menu.addSeparator()

        # 音量滑条（嵌入 QWidgetAction）
        # EN: Volume slider (embedded with QWidgetAction)
        vol_widget = QWidget()
        vol_layout = QHBoxLayout(vol_widget)
        vol_layout.setContentsMargins(8, 4, 8, 4)
        vol_label = QLabel("🔈")
        vol_layout.addWidget(vol_label)
        vol_slider = QSlider(Qt.Orientation.Horizontal)
        vol_slider.setRange(0, 100)
        vol_slider.setValue(int(music_player.volume * 100))
        vol_slider.setFixedWidth(120)
        vol_slider.valueChanged.connect(lambda v: music_player.set_volume(v / 100.0))
        vol_layout.addWidget(vol_slider)
        vol_action = QWidgetAction(music_menu)
        vol_action.setDefaultWidget(vol_widget)
        music_menu.addAction(vol_action)

    sync_context_menu_state(menu, pet, music_player, language=language)
    return menu


def sync_context_menu_state(menu: QMenu, pet, music_player=None, language: str = "zh-CN"):
    """刷新右键菜单动态状态（停止/恢复文案与勾选态）。"""
    """EN: Refresh the right-click menu dynamic state (stop/resume copy and check)."""
    language = normalize_language(language)
    toggle_action = menu.findChild(QAction, "toggleMoveAction")
    if toggle_action is not None:
        toggle_action.setText(tr(language, "menu.move.resume") if not pet.state.move_enabled else tr(language, "menu.move.stop"))

    follow_action = menu.findChild(QAction, "followAction")
    if follow_action is not None:
        follow_action.setChecked(bool(pet.state.follow_mouse))

    if music_player is not None:
        track_name_action = menu.findChild(QAction, "musicTrackNameAction")
        if track_name_action is not None:
            track_name_action.setText(music_player.current_track_name)

        play_pause_action = menu.findChild(QAction, "musicPlayPauseAction")
        if play_pause_action is not None:
            play_pause_action.setText(
                tr(language, "menu.music.pause") if music_player.is_playing else tr(language, "menu.music.play")
            )
