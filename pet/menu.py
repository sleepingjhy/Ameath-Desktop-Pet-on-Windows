"""该模块负责构建右键菜单。包含显示模式与多开控制。"""

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


def build_context_menu(pet, music_player=None) -> QMenu:
    """构建并返回右键菜单。菜单项绑定桌宠实例回调。"""
    menu = QMenu(pet)

    if hasattr(pet, "on_open_main") and callable(pet.on_open_main):
        open_main_action = QAction("打开应用界面", menu)
        open_main_action.triggered.connect(pet.on_open_main)
        menu.addAction(open_main_action)
        menu.addSeparator()

    stop_action = QAction(menu)
    stop_action.setObjectName("toggleMoveAction")
    stop_action.triggered.connect(pet.on_toggle_move_current)
    menu.addAction(stop_action)

    follow_action = QAction("跟随鼠标", menu)
    follow_action.setObjectName("followAction")
    follow_action.setCheckable(True)
    follow_action.setChecked(pet.state.follow_mouse)
    follow_action.triggered.connect(pet.on_toggle_follow)
    menu.addAction(follow_action)

    # 创建缩放二级菜单。范围 0.1x~2.0x，步进 0.1x。
    scale_menu = menu.addMenu("缩放比例")
    count = int(round((SCALE_MAX - SCALE_MIN) / SCALE_STEP)) + 1
    for i in range(count):
        value = round(SCALE_MIN + i * SCALE_STEP, 1)
        action = QAction(f"{value:.1f}x", scale_menu)
        action.setCheckable(True)
        action.setChecked(abs(pet.scale_factor - value) < 1e-6)
        action.triggered.connect(lambda checked=False, s=value: pet.on_set_scale(s))
        scale_menu.addAction(action)

    opacity_menu = menu.addMenu("透明度")
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

    display_mode_menu = menu.addMenu("显示优先级")
    current_mode = (
        pet.get_display_mode()
        if hasattr(pet, "get_display_mode") and callable(pet.get_display_mode)
        else DISPLAY_MODE_ALWAYS_ON_TOP
    )
    display_group = QActionGroup(display_mode_menu)
    display_group.setExclusive(True)

    display_items = [
        ("始终置顶", DISPLAY_MODE_ALWAYS_ON_TOP),
        ("其他应用全屏时隐藏", DISPLAY_MODE_FULLSCREEN_HIDE),
        ("仅在桌面显示", DISPLAY_MODE_DESKTOP_ONLY),
    ]
    for text, mode in display_items:
        action = QAction(text, display_mode_menu)
        action.setCheckable(True)
        action.setChecked(current_mode == mode)
        action.triggered.connect(lambda checked=False, m=mode: pet.on_set_display_mode(m))
        display_group.addAction(action)
        display_mode_menu.addAction(action)

    multi_instance_menu = menu.addMenu("多开模式")
    set_count_action = QAction(f"设置桌宠数量({INSTANCE_COUNT_MIN}-{INSTANCE_COUNT_MAX})", multi_instance_menu)
    set_count_action.triggered.connect(pet.on_set_instance_count_prompt)
    multi_instance_menu.addAction(set_count_action)

    # 创建开机自启开关。勾选状态由当前系统配置决定。
    autostart_action = QAction("开机自启", menu)
    autostart_action.setCheckable(True)
    autostart_action.setChecked(pet.get_autostart_enabled())
    autostart_action.triggered.connect(pet.on_toggle_autostart)
    menu.addAction(autostart_action)

    # 将关闭项置于分隔线后。降低误触风险。
    menu.addSeparator()

    close_menu = menu.addMenu("关闭桌宠")

    close_current_action = QAction("仅关闭当前桌宠", close_menu)
    close_current_action.triggered.connect(pet.on_close_current_pet)
    close_menu.addAction(close_current_action)

    close_random_action = QAction("关闭_个桌宠", close_menu)
    close_random_action.triggered.connect(pet.on_close_random_pets_prompt)
    close_menu.addAction(close_random_action)

    close_all_action = QAction("一键关闭所有桌宠并退出", close_menu)
    close_all_action.triggered.connect(pet.on_close_all_pets)
    close_menu.addAction(close_all_action)

    # 音乐子菜单（简化控制）
    if music_player is not None:
        menu.addSeparator()
        music_menu = menu.addMenu("🎵 音乐")

        # 当前歌曲名（只读）
        track_name_action = QAction(music_player.current_track_name, music_menu)
        track_name_action.setObjectName("musicTrackNameAction")
        track_name_action.setEnabled(False)
        music_menu.addAction(track_name_action)

        music_menu.addSeparator()

        # 上一首
        prev_action = QAction("◀◀ 上一首", music_menu)
        prev_action.triggered.connect(music_player.prev)
        music_menu.addAction(prev_action)

        # 播放/暂停（动态文字）
        play_pause_text = "⏸ 暂停" if music_player.is_playing else "▶ 播放"
        play_pause_action = QAction(play_pause_text, music_menu)
        play_pause_action.setObjectName("musicPlayPauseAction")
        play_pause_action.triggered.connect(music_player.toggle_pause)
        music_menu.addAction(play_pause_action)

        # 下一首
        next_action = QAction("▶▶ 下一首", music_menu)
        next_action.triggered.connect(music_player.next)
        music_menu.addAction(next_action)

        music_menu.addSeparator()

        # 播放模式（互斥单选）
        from .music_player import PLAY_MODE_LIST, PLAY_MODE_SINGLE, PLAY_MODE_RANDOM, MODE_ICONS
        mode_group = QActionGroup(music_menu)
        mode_group.setExclusive(True)
        for mode_key, mode_label in [
            (PLAY_MODE_LIST, f"{MODE_ICONS[PLAY_MODE_LIST]} 列表循环"),
            (PLAY_MODE_SINGLE, f"{MODE_ICONS[PLAY_MODE_SINGLE]} 单曲循环"),
            (PLAY_MODE_RANDOM, f"{MODE_ICONS[PLAY_MODE_RANDOM]} 随机播放"),
        ]:
            mode_action = QAction(mode_label, music_menu)
            mode_action.setCheckable(True)
            mode_action.setChecked(music_player.play_mode == mode_key)
            mode_action.triggered.connect(lambda checked=False, m=mode_key: music_player.set_mode(m))
            mode_group.addAction(mode_action)
            music_menu.addAction(mode_action)

        music_menu.addSeparator()

        # 音量滑条（嵌入 QWidgetAction）
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

    sync_context_menu_state(menu, pet, music_player)
    return menu


def sync_context_menu_state(menu: QMenu, pet, music_player=None):
    """刷新右键菜单动态状态（停止/恢复文案与勾选态）。"""
    toggle_action = menu.findChild(QAction, "toggleMoveAction")
    if toggle_action is not None:
        toggle_action.setText("恢复移动" if not pet.state.move_enabled else "停止移动")

    follow_action = menu.findChild(QAction, "followAction")
    if follow_action is not None:
        follow_action.setChecked(bool(pet.state.follow_mouse))

    if music_player is not None:
        track_name_action = menu.findChild(QAction, "musicTrackNameAction")
        if track_name_action is not None:
            track_name_action.setText(music_player.current_track_name)

        play_pause_action = menu.findChild(QAction, "musicPlayPauseAction")
        if play_pause_action is not None:
            play_pause_action.setText("⏸ 暂停" if music_player.is_playing else "▶ 播放")
