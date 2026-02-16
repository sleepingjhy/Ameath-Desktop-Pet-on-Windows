"""该模块负责多开实例管理与显示策略调度。统一管理所有桌宠实例。"""

from __future__ import annotations

import ctypes
import random
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal

from .autostart import is_autostart_enabled
from .config import (
    DISPLAY_MODE_ALWAYS_ON_TOP,
    DISPLAY_MODE_DESKTOP_ONLY,
    DISPLAY_MODE_FULLSCREEN_HIDE,
    INSTANCE_COUNT_MAX,
    INSTANCE_COUNT_MIN,
    OPACITY_DEFAULT_PERCENT,
    OPACITY_PERCENT_MAX,
    OPACITY_PERCENT_MIN,
)


class _ManagerState:
    """轻量状态对象。与单个桌宠保持相同字段命名，便于兼容调用。"""

    def __init__(self):
        self.follow_mouse = False


class RECT(ctypes.Structure):
    """Windows 窗口矩形结构。"""

    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFO(ctypes.Structure):
    """Windows 显示器信息结构。"""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class PetInstanceManager(QObject):
    """多开管理器。对外暴露与桌宠实例兼容的方法和状态。"""

    follow_changed = Signal(bool)
    scale_changed = Signal(float)
    autostart_changed = Signal(bool)
    display_mode_changed = Signal(str)
    instance_count_changed = Signal(int)
    opacity_changed = Signal(int)

    def __init__(self, settings_store, request_quit):
        """初始化全局状态、实例容器和显示策略轮询。"""
        super().__init__()
        self.settings_store = settings_store
        self.request_quit = request_quit

        self.state = _ManagerState()
        self.scale_factor: float = 1.0
        self.display_mode: str = self.settings_store.get_display_mode()
        self.target_count: int = self.settings_store.get_instance_count()
        self.opacity_percent: int = self.settings_store.get_opacity_percent()

        self._pets = []
        self._spawn_callback = None
        self._user32 = getattr(ctypes, "windll", None).user32 if hasattr(ctypes, "windll") else None

        self._display_timer = QTimer(self)
        self._display_timer.setInterval(250)
        self._display_timer.timeout.connect(self._apply_display_policy)
        self._display_timer.start()

    @property
    def pets(self):
        """返回当前实例快照。供外部只读遍历。"""
        return list(self._pets)

    def register_pet(self, pet):
        """注册桌宠实例并同步当前全局状态。"""
        if pet is None or pet in self._pets:
            return

        self._pets.append(pet)
        pet.instance_manager = self

        if hasattr(pet, "apply_follow_enabled"):
            pet.apply_follow_enabled(self.state.follow_mouse)
        if hasattr(pet, "apply_scale"):
            pet.apply_scale(self.scale_factor)
        if hasattr(pet, "apply_autostart"):
            pet.apply_autostart(self.get_autostart_enabled())
        if hasattr(pet, "apply_opacity_percent"):
            pet.apply_opacity_percent(self.opacity_percent)
        if hasattr(pet, "set_always_on_top"):
            pet.set_always_on_top(self.display_mode == DISPLAY_MODE_ALWAYS_ON_TOP)

        self._safe_show_or_hide_pet(pet, self._should_show_pets())

    def unregister_pet(self, pet):
        """注销桌宠实例。"""
        if pet in self._pets:
            self._pets.remove(pet)

    def set_spawn_callback(self, callback):
        """设置补齐实例时的创建回调。"""
        self._spawn_callback = callback

    def on_stop_move(self):
        """停止所有实例移动。仅调用本地执行方法，避免二次传播。"""
        for pet in list(self._pets):
            if hasattr(pet, "apply_stop_move"):
                pet.apply_stop_move()

    def on_toggle_follow(self):
        """切换全局跟随状态。"""
        self.on_set_follow(not self.state.follow_mouse)

    def on_set_follow(self, enabled):
        """设置全局跟随状态并同步所有实例。"""
        self.state.follow_mouse = bool(enabled)
        for pet in list(self._pets):
            if hasattr(pet, "apply_follow_enabled"):
                pet.apply_follow_enabled(self.state.follow_mouse)
        self.follow_changed.emit(self.state.follow_mouse)

    def on_set_scale(self, scale: float):
        """设置全局缩放并同步所有实例。"""
        try:
            normalized = float(scale)
        except (TypeError, ValueError):
            return

        self.scale_factor = normalized
        for pet in list(self._pets):
            if hasattr(pet, "apply_scale"):
                pet.apply_scale(self.scale_factor)
        self.scale_changed.emit(self.scale_factor)

    def get_autostart_enabled(self) -> bool:
        """读取系统开机自启状态。"""
        return is_autostart_enabled()

    def on_toggle_autostart(self, checked=False):
        """切换开机自启。参数为菜单/控件传入的目标状态。"""
        self.on_set_autostart(bool(checked))

    def on_set_autostart(self, enabled):
        """设置开机自启并同步所有实例。"""
        target = bool(enabled)
        for pet in list(self._pets):
            if hasattr(pet, "apply_autostart"):
                pet.apply_autostart(target)
        self.autostart_changed.emit(target)

    def on_set_opacity_percent(self, percent: int):
        """设置全局透明度并同步所有实例。"""
        try:
            normalized = int(percent)
        except (TypeError, ValueError):
            normalized = OPACITY_DEFAULT_PERCENT

        normalized = max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, normalized))
        self.opacity_percent = normalized
        self.settings_store.set_opacity_percent(normalized)

        for pet in list(self._pets):
            if hasattr(pet, "apply_opacity_percent"):
                pet.apply_opacity_percent(normalized)

        self.opacity_changed.emit(normalized)

    def get_opacity_percent(self) -> int:
        """返回当前透明度百分比。"""
        return self.opacity_percent

    def on_set_display_mode(self, mode: str):
        """设置显示模式并持久化。"""
        if mode not in {
            DISPLAY_MODE_ALWAYS_ON_TOP,
            DISPLAY_MODE_FULLSCREEN_HIDE,
            DISPLAY_MODE_DESKTOP_ONLY,
        }:
            mode = DISPLAY_MODE_ALWAYS_ON_TOP

        self.display_mode = mode
        self.settings_store.set_display_mode(mode)

        always_on_top = mode == DISPLAY_MODE_ALWAYS_ON_TOP
        for pet in list(self._pets):
            if hasattr(pet, "set_always_on_top"):
                pet.set_always_on_top(always_on_top)

        self.display_mode_changed.emit(self.display_mode)
        self._apply_display_policy()

    def get_display_mode(self) -> str:
        """返回当前显示模式。"""
        return self.display_mode

    def on_set_instance_count(self, count: int):
        """设置目标实例数并立即补齐或缩减。"""
        try:
            target = int(count)
        except (TypeError, ValueError):
            target = INSTANCE_COUNT_MIN

        target = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, target))
        self.target_count = target
        self.settings_store.set_instance_count(target)

        while len(self._pets) < self.target_count:
            if self._spawn_callback is None:
                break
            spawned = self._spawn_callback()
            if spawned is None:
                break
            if spawned not in self._pets:
                self.register_pet(spawned)

        if len(self._pets) > self.target_count:
            self.close_random_pets(len(self._pets) - self.target_count, update_target=False)

        self.instance_count_changed.emit(self.target_count)

    def get_instance_count(self) -> int:
        """返回当前目标实例数。"""
        return self.target_count

    def close_current_pet(self, pet):
        """关闭指定桌宠实例。"""
        if pet not in self._pets:
            return

        self._close_pet_instance(pet)
        if not self._pets:
            self.request_quit()
            return
        self._update_target_to_current_count()

    def close_random_pets(self, count: int, update_target=True):
        """随机关闭指定数量的桌宠实例。"""
        if not self._pets:
            return

        try:
            target_close = int(count)
        except (TypeError, ValueError):
            return

        if target_close <= 0:
            return

        actual_close = min(target_close, len(self._pets))
        selected = random.sample(list(self._pets), actual_close)
        for pet in selected:
            self._close_pet_instance(pet)

        if update_target:
            if not self._pets:
                self.request_quit()
                return
            self._update_target_to_current_count()

    def close_all_pets(self):
        """关闭全部桌宠实例。统一走应用级退出回调。"""
        self.request_quit()

    def _update_target_to_current_count(self):
        """将目标数量同步为当前存活实例数量并持久化。"""
        current = len(self._pets)
        current = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, current))
        self.target_count = current
        self.settings_store.set_instance_count(current)
        self.instance_count_changed.emit(self.target_count)

    def _close_pet_instance(self, pet):
        """执行单实例关闭流程。"""
        if pet not in self._pets:
            return

        self.unregister_pet(pet)

        try:
            if hasattr(pet, "prepare_for_exit") and callable(pet.prepare_for_exit):
                pet.prepare_for_exit()
            if hasattr(pet, "close") and callable(pet.close):
                pet.close()
        except Exception:
            pass

    def _apply_display_policy(self):
        """按显示模式定时控制实例可见性。异常时默认显示。"""
        should_show = self._should_show_pets()
        for pet in list(self._pets):
            self._safe_show_or_hide_pet(pet, should_show)

    def _safe_show_or_hide_pet(self, pet, should_show: bool):
        """安全执行显示/隐藏。异常时回退为显示。"""
        try:
            if should_show:
                if hasattr(pet, "show"):
                    pet.show()
                return
            if hasattr(pet, "hide"):
                pet.hide()
        except Exception:
            try:
                if hasattr(pet, "show"):
                    pet.show()
            except Exception:
                pass

    def _should_show_pets(self) -> bool:
        """根据当前显示模式计算是否应显示桌宠。"""
        if self.display_mode == DISPLAY_MODE_ALWAYS_ON_TOP:
            return True

        try:
            if self.display_mode == DISPLAY_MODE_FULLSCREEN_HIDE:
                return not self._is_foreground_fullscreen()
            if self.display_mode == DISPLAY_MODE_DESKTOP_ONLY:
                return self._is_foreground_desktop_window()
            return True
        except Exception:
            return True

    def _is_foreground_desktop_window(self) -> bool:
        """判断前台窗口是否为桌面窗口（Progman/WorkerW）。"""
        hwnd = self._get_valid_foreground_window()
        if not hwnd:
            return True

        class_name = self._get_class_name(hwnd)
        return class_name in {"Progman", "WorkerW"}

    def _is_foreground_fullscreen(self) -> bool:
        """判断前台窗口是否处于全屏状态。"""
        hwnd = self._get_valid_foreground_window()
        if not hwnd:
            return False

        class_name = self._get_class_name(hwnd)
        if class_name in {"Progman", "WorkerW"}:
            return False

        rect = RECT()
        if not self._user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        if rect.right <= rect.left or rect.bottom <= rect.top:
            return False

        monitor = self._user32.MonitorFromWindow(hwnd, 2)
        if not monitor:
            return False

        monitor_info = MONITORINFO()
        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
        if not self._user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
            return False

        monitor_rect = monitor_info.rcMonitor
        tolerance = 2
        return (
            rect.left <= monitor_rect.left + tolerance
            and rect.top <= monitor_rect.top + tolerance
            and rect.right >= monitor_rect.right - tolerance
            and rect.bottom >= monitor_rect.bottom - tolerance
        )

    def _get_valid_foreground_window(self):
        """获取可用的前台窗口句柄。无效、不可见或最小化窗口会被忽略。"""
        if self._user32 is None:
            return 0

        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return 0

        if not self._user32.IsWindow(hwnd):
            return 0

        if not self._user32.IsWindowVisible(hwnd):
            return 0

        if self._user32.IsIconic(hwnd):
            return 0

        return hwnd

    def _get_class_name(self, hwnd) -> str:
        """读取窗口类名。"""
        if self._user32 is None or not hwnd:
            return ""

        buffer = ctypes.create_unicode_buffer(256)
        length = self._user32.GetClassNameW(hwnd, buffer, 256)
        if length <= 0:
            return ""
        return buffer.value
