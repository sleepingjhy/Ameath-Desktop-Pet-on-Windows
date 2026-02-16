"""该模块负责构建右键菜单。包含显示模式与多开控制。"""

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

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


def build_context_menu(pet) -> QMenu:
    """构建并返回右键菜单。菜单项绑定桌宠实例回调。"""
    menu = QMenu(pet)

    stop_action = QAction("停止移动", pet)
    stop_action.triggered.connect(pet.on_stop_move)
    menu.addAction(stop_action)

    follow_action = QAction("跟随鼠标", pet)
    follow_action.setCheckable(True)
    follow_action.setChecked(pet.state.follow_mouse)
    follow_action.triggered.connect(pet.on_toggle_follow)
    menu.addAction(follow_action)

    # 创建缩放二级菜单。范围 0.1x~2.0x，步进 0.1x。
    scale_menu = menu.addMenu("缩放比例")
    count = int(round((SCALE_MAX - SCALE_MIN) / SCALE_STEP)) + 1
    for i in range(count):
        value = round(SCALE_MIN + i * SCALE_STEP, 1)
        action = QAction(f"{value:.1f}x", pet)
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
        action = QAction(f"{value}%", pet)
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
        action = QAction(text, pet)
        action.setCheckable(True)
        action.setChecked(current_mode == mode)
        action.triggered.connect(lambda checked=False, m=mode: pet.on_set_display_mode(m))
        display_group.addAction(action)
        display_mode_menu.addAction(action)

    multi_instance_menu = menu.addMenu("多开模式")
    set_count_action = QAction(f"设置桌宠数量({INSTANCE_COUNT_MIN}-{INSTANCE_COUNT_MAX})", pet)
    set_count_action.triggered.connect(pet.on_set_instance_count_prompt)
    multi_instance_menu.addAction(set_count_action)

    # 创建开机自启开关。勾选状态由当前系统配置决定。
    autostart_action = QAction("开机自启", pet)
    autostart_action.setCheckable(True)
    autostart_action.setChecked(pet.get_autostart_enabled())
    autostart_action.triggered.connect(pet.on_toggle_autostart)
    menu.addAction(autostart_action)

    # 将关闭项置于分隔线后。降低误触风险。
    menu.addSeparator()

    close_menu = menu.addMenu("关闭桌宠")

    close_current_action = QAction("仅关闭当前桌宠", pet)
    close_current_action.triggered.connect(pet.on_close_current_pet)
    close_menu.addAction(close_current_action)

    close_random_action = QAction("关闭_个桌宠", pet)
    close_random_action.triggered.connect(pet.on_close_random_pets_prompt)
    close_menu.addAction(close_random_action)

    close_all_action = QAction("一键关闭所有桌宠", pet)
    close_all_action.triggered.connect(pet.on_close_all_pets)
    close_menu.addAction(close_all_action)

    return menu
