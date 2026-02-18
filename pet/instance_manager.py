"""该模块负责多开实例管理与显示策略调度。统一管理所有桌宠实例。"""
# EN: This module manages multi-instance pets and display-policy scheduling across all instances.

from __future__ import annotations

import ctypes
import random
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

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
from .i18n import normalize_language


class _ManagerState:
    """轻量状态对象。与单个桌宠保持相同字段命名，便于兼容调用。"""
    """EN: Lightweight state object. Keep the same field name as a single table darling for easy compatibility calls."""

    def __init__(self):
        self.follow_mouse = False
        self.move_enabled = True


class RECT(ctypes.Structure):
    """Windows 窗口矩形结构。"""
    """EN: Windows window rectangular structure."""

    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000


class MONITORINFO(ctypes.Structure):
    """Windows 显示器信息结构。"""
    """EN: Windows display information structure."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class PetInstanceManager(QObject):
    """多开管理器。对外暴露与桌宠实例兼容的方法和状态。"""
    """EN: Multi-open the manager. Exposure to methods and states compatible with table pet instances."""

    follow_changed = Signal(bool)
    scale_changed = Signal(float)
    autostart_changed = Signal(bool)
    display_mode_changed = Signal(str)
    instance_count_changed = Signal(int)
    opacity_changed = Signal(int)
    move_enabled_changed = Signal(bool)
    language_changed = Signal(str)

    def __init__(self, settings_store, request_quit, music_player=None):
        """初始化全局状态、实例容器和显示策略轮询。"""
        """EN: Initializes global state, instance container, and display policy polling."""
        super().__init__()
        self.settings_store = settings_store
        self.request_quit = request_quit
        self.music_player = music_player

        self.state = _ManagerState()
        self.state.follow_mouse = self.settings_store.get_follow_mouse()
        self.scale_factor: float = self.settings_store.get_scale_factor()
        self.display_mode: str = self.settings_store.get_display_mode()
        self.target_count: int = self.settings_store.get_instance_count()
        self.opacity_percent: int = self.settings_store.get_opacity_percent()
        self.language: str = self.settings_store.get_language()

        self._pets = []
        self._spawn_callback = None
        self._user32 = getattr(ctypes, "windll", None).user32 if hasattr(ctypes, "windll") else None

        self._display_timer = QTimer(self)
        self._display_timer.setInterval(50)
        self._display_timer.timeout.connect(self._apply_display_policy)
        self._display_timer.start()
        self._last_should_show = True

        self._collision_timer = QTimer(self)
        self._collision_timer.setInterval(45)
        self._collision_timer.timeout.connect(self._resolve_pet_collisions)
        self._collision_timer.start()

    @property
    def pets(self):
        """返回当前实例快照。供外部只读遍历。"""
        """EN: Returns a snapshot of the current instance. For external read-only traversal."""
        return list(self._pets)

    def register_pet(self, pet):
        """注册桌宠实例并同步当前全局状态。"""
        """EN: Register the table pet instance and synchronize the current global state."""
        if pet is None or pet in self._pets:
            return

        self._pets.append(pet)
        pet.instance_manager = self

        if len(self._pets) > 1:
            self._relocate_pet_avoid_overlap(pet)

        if hasattr(pet, "apply_move_enabled"):
            pet.apply_move_enabled(self.state.move_enabled)
        if hasattr(pet, "apply_follow_enabled"):
            pet.apply_follow_enabled(self.state.follow_mouse)
        if hasattr(pet, "apply_scale"):
            pet.apply_scale(self.scale_factor)
        if hasattr(pet, "apply_autostart"):
            pet.apply_autostart(self.get_autostart_enabled())
        if hasattr(pet, "apply_opacity_percent"):
            pet.apply_opacity_percent(self.opacity_percent)
        if hasattr(pet, "apply_language"):
            pet.apply_language(self.language)
        if hasattr(pet, "set_always_on_top"):
            pet.set_always_on_top(True)

        self._sync_multi_open_topmost()

        self._safe_show_or_hide_pet(pet, self._should_show_pets())

    def _relocate_pet_avoid_overlap(self, pet):
        """为新实例寻找不重叠位置，避免与已有桌宠重合生成。"""
        """EN: Look for non-overlapping positions for new instances to avoid overlapping with existing table darlings."""
        others = [p for p in self._pets if p is not pet]
        if not others:
            return

        screen = QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        width = max(1, pet.width())
        height = max(1, pet.height())
        step_x = max(24, int(width * 0.8))
        step_y = max(24, int(height * 0.8))

        base = others[-1].pos()
        max_cols = max(1, (geometry.width() - width) // step_x)
        max_rows = max(1, (geometry.height() - height) // step_y)

        for index in range(max_cols * max_rows + 1):
            col = index % max_cols
            row = index // max_cols
            x = geometry.left() + ((base.x() - geometry.left()) + col * step_x) % max(1, geometry.width() - width)
            y = geometry.top() + ((base.y() - geometry.top()) + row * step_y) % max(1, geometry.height() - height)

            candidate_rect = pet.frameGeometry()
            candidate_rect.moveTo(x, y)
            overlap = any(candidate_rect.intersects(other.frameGeometry()) for other in others)
            if not overlap:
                pet.move(x, y)
                if hasattr(pet, "movement") and hasattr(pet.movement, "_sync_float_position"):
                    pet.movement._sync_float_position()
                return

        fallback_x = min(max(geometry.left(), base.x() + step_x), geometry.right() - width)
        fallback_y = min(max(geometry.top(), base.y() + step_y), geometry.bottom() - height)
        pet.move(fallback_x, fallback_y)
        if hasattr(pet, "movement") and hasattr(pet.movement, "_sync_float_position"):
            pet.movement._sync_float_position()

    def _resolve_pet_collisions(self):
        """处理多桌宠碰撞。碰撞后反向移动并分离重叠区域。"""
        """EN: Handle multiple table pet collisions. Move backwards and separate overlapping areas after a collision."""
        if len(self._pets) < 2:
            return

        pets = [p for p in self._pets if hasattr(p, "movement")]
        for i in range(len(pets)):
            left_pet = pets[i]
            if getattr(left_pet.state, "is_dragging", False):
                continue

            left_rect = left_pet.frameGeometry()
            for j in range(i + 1, len(pets)):
                right_pet = pets[j]
                if getattr(right_pet.state, "is_dragging", False):
                    continue

                right_rect = right_pet.frameGeometry()
                if not left_rect.intersects(right_rect):
                    continue

                self._bounce_two_pets(left_pet, right_pet, left_rect, right_rect)
                left_rect = left_pet.frameGeometry()

    def _bounce_two_pets(self, first_pet, second_pet, first_rect, second_rect):
        """执行两实例碰撞反弹与位置分离。"""
        """EN: Perform two instances of collision bounce and position separation."""
        intersection = first_rect.intersected(second_rect)
        if intersection.isEmpty():
            return

        overlap_w = intersection.width()
        overlap_h = intersection.height()

        if overlap_w <= overlap_h:
            shift = max(1, overlap_w // 2 + 1)
            if first_rect.center().x() <= second_rect.center().x():
                first_dx = -shift
                second_dx = shift
            else:
                first_dx = shift
                second_dx = -shift
            first_dy = 0
            second_dy = 0
        else:
            shift = max(1, overlap_h // 2 + 1)
            if first_rect.center().y() <= second_rect.center().y():
                first_dy = -shift
                second_dy = shift
            else:
                first_dy = shift
                second_dy = -shift
            first_dx = 0
            second_dx = 0

        self._move_pet_by_delta(first_pet, first_dx, first_dy)
        self._move_pet_by_delta(second_pet, second_dx, second_dy)

        first_pet.movement.velocity_x = -first_pet.movement.velocity_x
        first_pet.movement.velocity_y = -first_pet.movement.velocity_y
        second_pet.movement.velocity_x = -second_pet.movement.velocity_x
        second_pet.movement.velocity_y = -second_pet.movement.velocity_y

        first_pet.facing_left = first_pet.movement.velocity_x < 0
        second_pet.facing_left = second_pet.movement.velocity_x < 0
        first_pet._apply_state_animation()
        second_pet._apply_state_animation()

    def _move_pet_by_delta(self, pet, dx: int, dy: int):
        """按位移调整实例位置并约束屏幕边界。"""
        """EN: Adjusts the instance position by displacement and constrains the screen boundaries."""
        pet.move(pet.x() + dx, pet.y() + dy)
        if hasattr(pet, "movement"):
            pet.movement.constrain_to_screen()
            if hasattr(pet.movement, "_sync_float_position"):
                pet.movement._sync_float_position()

    def unregister_pet(self, pet):
        """注销桌宠实例。"""
        """EN: Log out of the table pet instance."""
        if pet in self._pets:
            self._pets.remove(pet)
            self._sync_multi_open_topmost()

    def _sync_multi_open_topmost(self):
        """多开(>=2)时所有实例临时置顶，单实例时恢复为用户显示优先级。"""
        """EN: When more open (> = 2), all instances are temporarily pinned to the top, and when single instance is restored, the priority is displayed for the user."""
        force_topmost = len(self._pets) >= 2
        for pet in list(self._pets):
            if hasattr(pet, "set_force_topmost_for_multi"):
                pet.set_force_topmost_for_multi(force_topmost)

    def set_spawn_callback(self, callback):
        """设置补齐实例时的创建回调。"""
        """EN: Set the create callback when filling the instance."""
        self._spawn_callback = callback

    def on_stop_move(self):
        """兼容入口：切换全部实例停止/恢复移动。"""
        """EN: Compatible Entry: Switch all instances to stop/resume movement."""
        self.on_toggle_move_all()

    def on_toggle_move_all(self):
        """切换全部实例移动状态。"""
        """EN: Toggles the movement state of all instances."""
        self.on_set_move_enabled_all(not self.state.move_enabled)

    def on_set_move_enabled_all(self, enabled: bool):
        """设置全部实例移动状态并同步广播。"""
        """EN: Set all instances to move state and synchronize broadcasts."""
        self.state.move_enabled = bool(enabled)
        for pet in list(self._pets):
            if hasattr(pet, "apply_move_enabled"):
                pet.apply_move_enabled(self.state.move_enabled)
        self.move_enabled_changed.emit(self.state.move_enabled)

    def get_move_enabled(self) -> bool:
        """返回当前全局移动开关状态。"""
        """EN: Returns the current global move switch state."""
        return bool(self.state.move_enabled)

    def on_toggle_follow(self):
        """切换全局跟随状态。"""
        """EN: Toggles the global follower state."""
        self.on_set_follow(not self.state.follow_mouse)

    def on_set_follow(self, enabled):
        """设置全局跟随状态并同步所有实例。"""
        """EN: Sets the global follower state and synchronizes all instances."""
        self.state.follow_mouse = bool(enabled)
        self.settings_store.set_follow_mouse(self.state.follow_mouse)
        for pet in list(self._pets):
            if hasattr(pet, "apply_follow_enabled"):
                pet.apply_follow_enabled(self.state.follow_mouse)
        self.follow_changed.emit(self.state.follow_mouse)

    def on_set_scale(self, scale: float):
        """设置全局缩放并同步所有实例。"""
        """EN: Sets global scaling and synchronizes all instances."""
        try:
            normalized = float(scale)
        except (TypeError, ValueError):
            return

        self.scale_factor = normalized
        self.settings_store.set_scale_factor(normalized)
        for pet in list(self._pets):
            if hasattr(pet, "apply_scale"):
                pet.apply_scale(self.scale_factor)
        self.scale_changed.emit(self.scale_factor)

    def get_autostart_enabled(self) -> bool:
        """读取系统开机自启状态。"""
        """EN: Read the system power on and off status."""
        return is_autostart_enabled()

    def on_toggle_autostart(self, checked=False):
        """切换开机自启。参数为菜单/控件传入的目标状态。"""
        """EN: Toggle on and off. The parameter is the target state passed in by the menu/control."""
        self.on_set_autostart(bool(checked))

    def on_set_autostart(self, enabled):
        """设置开机自启并同步所有实例。"""
        """EN: Set boot to self-start and synchronize all instances."""
        target = bool(enabled)
        for pet in list(self._pets):
            if hasattr(pet, "apply_autostart"):
                pet.apply_autostart(target)
        self.autostart_changed.emit(target)

    def on_set_opacity_percent(self, percent: int):
        """设置全局透明度并同步所有实例。"""
        """EN: Set global transparency and synchronize all instances."""
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
        """EN: Returns the current transparency percentage."""
        return self.opacity_percent

    def on_set_display_mode(self, mode: str):
        """设置显示模式并持久化。"""
        """EN: Sets the display mode and persists."""
        if mode not in {
            DISPLAY_MODE_ALWAYS_ON_TOP,
            DISPLAY_MODE_FULLSCREEN_HIDE,
            DISPLAY_MODE_DESKTOP_ONLY,
        }:
            mode = DISPLAY_MODE_ALWAYS_ON_TOP

        self.display_mode = mode
        self.settings_store.set_display_mode(mode)

        for pet in list(self._pets):
            if hasattr(pet, "set_always_on_top"):
                pet.set_always_on_top(True)

        self.display_mode_changed.emit(self.display_mode)
        self._apply_display_policy()

    def get_display_mode(self) -> str:
        """返回当前显示模式。"""
        """EN: Returns the current display mode."""
        return self.display_mode

    def on_set_instance_count(self, count: int):
        """设置目标实例数并立即补齐或缩减。"""
        """EN: Set the number of target instances and fill or shrink them immediately."""
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
        """EN: Returns the current number of target instances."""
        return self.target_count

    def on_set_language(self, language: str):
        """设置界面语言并同步所有实例。"""
        """EN: Set the interface language and sync all instances."""
        normalized = normalize_language(language)
        self.language = normalized
        self.settings_store.set_language(normalized)

        for pet in list(self._pets):
            if hasattr(pet, "apply_language"):
                pet.apply_language(normalized)

        self.language_changed.emit(normalized)

    def get_language(self) -> str:
        """返回当前界面语言。"""
        """EN: Returns the current interface language."""
        return normalize_language(self.language)

    def close_current_pet(self, pet):
        """关闭指定桌宠实例。"""
        """EN: Close the specified table pet instance."""
        if pet not in self._pets:
            return

        self._close_pet_instance(pet)
        self._update_target_to_current_count()

    def close_random_pets(self, count: int, update_target=True):
        """随机关闭指定数量的桌宠实例。"""
        """EN: Randomly close a specified number of table darling instances."""
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
            self._update_target_to_current_count()

    def close_all_pets(self):
        """关闭全部桌宠实例。统一走应用级退出回调。"""
        """EN: Close all table darling instances. Uniform application-level exit callback."""
        self.request_quit()

    def _update_target_to_current_count(self):
        """将目标数量同步为当前存活实例数量并持久化。"""
        """EN: Synchronize the target number to the current number of surviving instances and persist."""
        current = len(self._pets)
        current = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, current))
        self.target_count = current
        self.settings_store.set_instance_count(current)
        self.instance_count_changed.emit(self.target_count)

    def _close_pet_instance(self, pet):
        """执行单实例关闭流程。"""
        """EN: Performs a single-instance shutdown process."""
        if pet not in self._pets:
            return

        self.unregister_pet(pet)

        try:
            if hasattr(pet, "prepare_for_exit") and callable(pet.prepare_for_exit):
                pet.prepare_for_exit()
            if hasattr(pet, "close") and callable(pet.close):
                pet.close()
            if hasattr(pet, "deleteLater") and callable(pet.deleteLater):
                pet.deleteLater()
        except Exception:
            pass

    def shutdown(self):
        """停止管理器计时器并释放所有桌宠实例。"""
        """EN: Stop the manager timer and release all table darling instances."""
        self._spawn_callback = None

        if self._display_timer.isActive():
            self._display_timer.stop()
        if self._collision_timer.isActive():
            self._collision_timer.stop()

        try:
            self._display_timer.timeout.disconnect(self._apply_display_policy)
        except Exception:
            pass
        try:
            self._collision_timer.timeout.disconnect(self._resolve_pet_collisions)
        except Exception:
            pass

        pets = list(self._pets)
        self._pets.clear()
        for pet in pets:
            try:
                if hasattr(pet, "prepare_for_exit") and callable(pet.prepare_for_exit):
                    pet.prepare_for_exit()
                if hasattr(pet, "close") and callable(pet.close):
                    pet.close()
                if hasattr(pet, "deleteLater") and callable(pet.deleteLater):
                    pet.deleteLater()
            except Exception:
                pass

        try:
            self._display_timer.deleteLater()
            self._collision_timer.deleteLater()
        except Exception:
            pass

    def _apply_display_policy(self):
        """按显示模式定时控制实例可见性。异常时默认显示。"""
        """EN: Timing control instance visibility by display mode. Displayed by default when abnormal."""
        should_show = self._should_show_pets()

        # 从全屏隐藏恢复到可显示时，强制恢复全部实例显示，避免遗漏。
        # EN: When recovering from full-screen hiding to displayable, force recovery of all instance displays to avoid omission.
        if should_show and not self._last_should_show:
            self._restore_all_hidden_pets()

        for pet in list(self._pets):
            self._safe_show_or_hide_pet(pet, should_show)

        self._last_should_show = should_show

    def _restore_all_hidden_pets(self):
        """恢复所有已隐藏实例的可见状态。"""
        """EN: Restore the visible state of all hidden instances."""
        for pet in list(self._pets):
            try:
                if hasattr(pet, "isVisible") and not pet.isVisible():
                    pet.show()
            except Exception:
                pass

    def _safe_show_or_hide_pet(self, pet, should_show: bool):
        """安全执行显示/隐藏。异常时回退为显示。"""
        """EN: Safely execute show/hide. Fallback to display when abnormal."""
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
        """EN: Calculate whether the table pet should be displayed based on the current display mode."""
        if self.display_mode == DISPLAY_MODE_ALWAYS_ON_TOP:
            return True

        try:
            if self.display_mode == DISPLAY_MODE_FULLSCREEN_HIDE:
                return not self._is_top_visible_window_blocking()
            if self.display_mode == DISPLAY_MODE_DESKTOP_ONLY:
                return self._is_foreground_desktop_window()
            return True
        except Exception:
            return True

    def _is_top_visible_window_blocking(self) -> bool:
        """判断当前顶层可见非最小化窗口是否应触发隐藏（全屏或最大化）。"""
        """EN: Determines whether the current top-level visible non-minimized window should trigger hide (full screen or maximized)."""
        hwnd = self._get_top_visible_window()
        if not hwnd:
            return False

        return self._is_window_fullscreen(hwnd) or self._is_window_maximized(hwnd)

    def _is_window_maximized(self, hwnd) -> bool:
        """判断指定窗口是否为最大化状态。"""
        """EN: Determine if the specified window is maximized."""
        if not hwnd or self._user32 is None:
            return False
        try:
            return bool(self._user32.IsZoomed(hwnd))
        except Exception:
            return False

    def _get_top_visible_window(self):
        """获取当前顶层可见且未最小化的窗口句柄。"""
        """EN: Gets the current top-level visible and unminimized window handle."""
        if self._user32 is None:
            return 0

        hwnd = self._user32.GetTopWindow(0)
        gw_hwndnext = 2
        while hwnd:
            if not self._user32.IsWindow(hwnd):
                hwnd = self._user32.GetWindow(hwnd, gw_hwndnext)
                continue
            if not self._user32.IsWindowVisible(hwnd):
                hwnd = self._user32.GetWindow(hwnd, gw_hwndnext)
                continue
            if self._user32.IsIconic(hwnd):
                hwnd = self._user32.GetWindow(hwnd, gw_hwndnext)
                continue

            class_name = self._get_class_name(hwnd)
            if class_name in {"Progman", "WorkerW"}:
                hwnd = self._user32.GetWindow(hwnd, gw_hwndnext)
                continue

            return hwnd

        return 0

    def _is_foreground_desktop_window(self) -> bool:
        """判断前台窗口是否为桌面窗口（Progman/WorkerW）。"""
        """EN: Determine if the front window is a desktop window (Progman/WorkerW)."""
        hwnd = self._get_valid_foreground_window()
        if not hwnd:
            return True

        class_name = self._get_class_name(hwnd)
        return class_name in {"Progman", "WorkerW"}

    def _is_foreground_fullscreen(self) -> bool:
        """判断前台窗口是否处于全屏状态。"""
        """EN: Determine if the front window is in full screen."""
        hwnd = self._get_valid_foreground_window()
        if not hwnd:
            return False

        return self._is_window_fullscreen(hwnd)

    def _is_window_fullscreen(self, hwnd) -> bool:
        """判断指定窗口是否处于全屏状态。"""
        """EN: Determine if the specified window is in full-screen state."""
        if not hwnd:
            return False

        class_name = self._get_class_name(hwnd)
        if class_name in {"Progman", "WorkerW"}:
            return False

        # 窗口化（有标题栏/可调整边框）即使尺寸很大，也不按“全屏隐藏”处理。
        # EN: Windowing (with title bar/adjustable border) is not handled by Hidden Full Screen even if it is large in size.
        try:
            style = self._user32.GetWindowLongW(hwnd, GWL_STYLE)
            if style & (WS_CAPTION | WS_THICKFRAME):
                return False
        except Exception:
            pass

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
        """EN: Gets the available foreground window handle. Invalid, invisible or minimized windows are ignored."""
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
        """EN: Reads the window class name."""
        if self._user32 is None or not hwnd:
            return ""

        buffer = ctypes.create_unicode_buffer(256)
        length = self._user32.GetClassNameW(hwnd, buffer, 256)
        if length <= 0:
            return ""
        return buffer.value
