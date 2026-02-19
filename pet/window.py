"""该模块是桌宠主窗口。整合动画、输入、状态机、菜单与控制器。"""
"""EN: This module implements the main desktop-pet window and integrates animation, input, state, menu, and control logic."""
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QWidget
from PySide6.QtCore import QFile
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QWidget
from PySide6.QtCore import QFile

from .animation import GifLabel, create_movie
from .autostart import is_autostart_enabled, set_autostart_enabled
from .config import (
    ASSET_PATHS,
    DISPLAY_MODE_ALWAYS_ON_TOP,
    INSTANCE_COUNT_MAX,
    INSTANCE_COUNT_MIN,
    MOVE_TICK_MS,
    OPACITY_DEFAULT_PERCENT,
    OPACITY_PERCENT_MAX,
    OPACITY_PERCENT_MIN,
)
from .idle import IdleController
from .input import handle_mouse_move, handle_mouse_press, handle_mouse_release
from .menu import build_context_menu, sync_context_menu_state
from .movement import MovementController
from .state_machine import PetStateMachine
from .i18n import normalize_language, tr


class DesktopPet(QWidget):
    """这是桌宠主窗口类。负责运行时调度和界面事件分发。"""
    """EN: This is the table owner window class. Responsible for runtime scheduling and interface event distribution."""

    follow_changed = Signal(bool)
    scale_changed = Signal(float)
    autostart_changed = Signal(bool)
    display_mode_changed = Signal(str)
    instance_count_changed = Signal(int)
    opacity_changed = Signal(int)
    move_enabled_changed = Signal(bool)
    language_changed = Signal(str)

    def __init__(
        self,
        on_open_main=None,
        on_open_chat=None,
        on_request_quit=None,
        close_policy=None,
        instance_manager=None,
        music_player=None,
    ):
        """完成主窗口初始化。包括资源校验、控制器构造和定时器启动。"""
        """EN: Finished initializing the main window. This includes resource checksumming, controller construction, and timer startup."""
        super().__init__()

        # 先做资源校验。避免运行中才发现 GIF 缺失。
        # EN: First, check the resources. Avoid running until the GIF is missing.
        self._assert_assets()

        # 配置桌宠窗口样式。无边框、置顶、工具窗组合。
        # EN: Configure the table pet window style. Borderless, Sticky, Tool Window Combo.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.label = GifLabel(self)
        # 预加载移动/拖拽动画与休息动画集合。
        # EN: Preload mobile/drag animations with a collection of rest animations.
        self.movies = {
            "move": create_movie(ASSET_PATHS["move"]),
            "drag": create_movie(ASSET_PATHS["drag"]),
        }
        self.rest_movies = [create_movie(path) for path in ASSET_PATHS["rest"]]
        for movie in self.movies.values():
            movie.setParent(self)
        for movie in self.rest_movies:
            movie.setParent(self)

        self.state = PetStateMachine()
        self.scale_factor = 1.0
        self.opacity_percent = OPACITY_DEFAULT_PERCENT
        self.drag_offset = QPoint(0, 0)
        self.facing_left = False
        self.active_menu = None
        self._context_menu = None
        self.menu_anchor_offset = QPoint(0, 0)
        self.menu_last_pet_pos = QPoint(0, 0)
        self.follow_blocked = False
        self.on_open_main = on_open_main
        self.on_open_chat = on_open_chat
        self.on_request_quit = on_request_quit
        self.close_policy = close_policy
        self.tray_controller = None
        self._is_exiting = False
        self.instance_manager = instance_manager
        self.music_player = music_player
        self._menu_open: bool = False
        self._always_on_top = True
        self._force_topmost_for_multi = False
        self.language = "zh-CN"

        self.movement = MovementController(self)
        self.idle = IdleController(self)

        # 默认进入移动动画。初始朝向设为向右。
        # EN: Enter the mobile animation by default. The initial orientation is set to right.
        self._set_animation("move", mirror=False)

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self._tick)
        self.tick_timer.start(MOVE_TICK_MS)

        self.idle.start()
        self.movement.place_initial()
        self.show()

    def _assert_assets(self):
        """校验动画资源完整性。缺失时抛出带列表的异常。"""
        """EN: Verify the integrity of the animation resource. Throws an exception with a list when missing."""
        def asset_exists(asset) -> bool:
            asset_text = str(asset)
            if asset_text.startswith(":/"):
                return QFile.exists(asset_text)
            return QFile.exists(asset_text)

        missing = []
        for key, value in ASSET_PATHS.items():
            if isinstance(value, list):
                for path in value:
                    if not asset_exists(path):
                        missing.append(str(path))
            elif not asset_exists(value):
                missing.append(str(value))

        if missing:
            raise FileNotFoundError("缺少 GIF 资源:\n" + "\n".join(missing))

    def _set_animation(self, key: str, mirror: bool):
        """切换基础动作动画。仅处理移动/拖拽并同步镜像状态。"""
        """EN: Toggle base action animation. Handles only move/drag and synchronize mirror states."""
        if key == "move":
            movie = self.movies["move"]
        else:
            movie = self.movies["drag"]

        if self.label._movie is not movie:
            self.label.set_movie(movie)
        self.label.set_mirror(mirror)

    def show_rest_animation(self):
        """播放静止/休息动画。从休息资源中随机选择并播放。"""
        """EN: Plays a still/rest animation. Randomly select and play from rest resources."""
        import random

        movie = random.choice(self.rest_movies)
        if self.label._movie is not movie:
            self.label.set_movie(movie)
        self.label.set_mirror(False)

    def set_drag_animation(self):
        """切到拖拽动画。拖拽状态始终使用该动画。"""
        """EN: Cut to drag animation. The animation is always used in the drag state."""
        self._set_animation("drag", mirror=False)

    def _apply_state_animation(self):
        """按状态优先级更新动画。拖拽优先，其次休息，再到移动。"""
        """EN: Update animations by status priority. Drag and drop first, then rest, then move."""
        if self.state.is_dragging:
            self._set_animation("drag", mirror=False)
            return

        if self.state.in_rest:
            return

        self._set_animation("move", mirror=self.facing_left)

    def _tick(self):
        """执行主循环调度。按拖拽>跟随>休息>自主移动优先级处理。"""
        """EN: Perform the main loop scheduling. Press Drag > Follow > Rest > Autonomous Move Priority Processing."""
        if self.state.is_dragging:
            return

        if self.state.follow_mouse:
            moved, blocked_by_edge = self.movement.follow_cursor_tick()
            if blocked_by_edge and not moved:
                if not self.follow_blocked:
                    self.follow_blocked = True
                    self.show_rest_animation()
            else:
                if self.follow_blocked:
                    self.follow_blocked = False
                self._apply_state_animation()
            return

        if self.state.in_rest:
            return

        if self.state.move_enabled:
            self.movement.auto_move_tick()

    def apply_stop_move(self):
        """本地执行停止移动。仅操作当前实例，不做跨实例传播。"""
        """EN: Local execution stops the move. Only operate on the current instance, not cross-instance propagation."""
        self.state.stop_move()
        self.state.exit_rest()
        self.follow_blocked = False
        self.follow_changed.emit(self.state.follow_mouse)
        self.move_enabled_changed.emit(self.state.move_enabled)
        self.idle.try_enter_rest()
        if not self.state.in_rest:
            self._set_animation("move", mirror=self.facing_left)

    def on_stop_move(self, checked=False):
        """兼容入口：切换全部实例移动状态。"""
        """EN: Compatible Entry: Toggle all instance movement states."""
        if self.instance_manager is not None and hasattr(self.instance_manager, "on_toggle_move_all"):
            self.instance_manager.on_toggle_move_all()
            return

        self.on_toggle_move_current()

    def apply_resume_move(self):
        """本地执行恢复移动。仅操作当前实例，不做跨实例传播。"""
        """EN: Resume move is performed locally. Only operate on the current instance, not cross-instance propagation."""
        self.state.start_move()
        self.state.exit_rest()
        self.follow_blocked = False
        self.move_enabled_changed.emit(self.state.move_enabled)
        self._apply_state_animation()

    def apply_move_enabled(self, enabled: bool):
        """本地应用移动开关。"""
        """EN: Local application mobile switch."""
        if bool(enabled):
            self.apply_resume_move()
            return
        self.apply_stop_move()

    def on_toggle_move_current(self, checked=False):
        """右键菜单入口：仅切换当前实例移动状态。"""
        """EN: Right-click menu entry: toggles only the current instance movement state."""
        self.apply_move_enabled(not self.state.move_enabled)

    def on_set_move_enabled(self, enabled: bool):
        """设置移动状态。优先委托实例管理器。"""
        """EN: Sets the move state. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            if hasattr(self.instance_manager, "on_set_move_enabled_all"):
                self.instance_manager.on_set_move_enabled_all(bool(enabled))
            return

        self.apply_move_enabled(bool(enabled))

    def get_move_enabled(self) -> bool:
        """读取移动开关状态。"""
        """EN: Reads the movement switch status."""
        if self.instance_manager is not None and hasattr(self.instance_manager, "get_move_enabled"):
            return bool(self.instance_manager.get_move_enabled())
        return bool(self.state.move_enabled)

    def apply_follow_enabled(self, enabled: bool):
        """本地应用跟随状态。"""
        """EN: The local app follows the state."""
        before_move_enabled = bool(self.state.move_enabled)
        self.state.set_follow_mouse(bool(enabled))
        self.follow_blocked = False
        self.follow_changed.emit(self.state.follow_mouse)
        if before_move_enabled != bool(self.state.move_enabled):
            self.move_enabled_changed.emit(self.state.move_enabled)
        self._apply_state_animation()

    def on_toggle_follow(self, checked=False):
        """处理跟随鼠标开关事件。优先委托实例管理器。"""
        """EN: Handles following mouse switch events. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_toggle_follow()
            return

        self.apply_follow_enabled(not self.state.follow_mouse)

    def on_set_follow(self, enabled):
        """设置跟随鼠标状态。优先委托实例管理器。"""
        """EN: Sets the following mouse state. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_set_follow(bool(enabled))
            return

        self.apply_follow_enabled(bool(enabled))

    def apply_scale(self, scale: float):
        """本地应用缩放。"""
        """EN: Apply zoom locally."""
        try:
            normalized = float(scale)
        except (TypeError, ValueError):
            return

        # 先应用缩放。重置窗口尺寸后再纠正位置。
        # EN: Apply zoom first. Reset the window size before correcting the position.
        old_pos = self.pos()
        self.scale_factor = normalized
        self.label.set_scale(normalized)
        self.resize(self.label.size())
        self.move(old_pos)
        self.movement.constrain_to_screen()
        self.scale_changed.emit(self.scale_factor)

    def on_set_scale(self, scale: float):
        """处理缩放菜单事件。优先委托实例管理器。"""
        """EN: Handles zoom menu events. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_set_scale(scale)
            return

        self.apply_scale(scale)

    def on_exit(self, checked=False):
        """处理退出菜单事件。优先走应用级退出回调。"""
        """EN: Handles exit menu events. Take the application level first to exit the callback."""
        if self.on_request_quit is not None:
            self.on_request_quit()
            return

        self.prepare_for_exit()
        self.close()

    def set_tray_controller(self, tray_controller):
        """设置托盘控制器引用。用于最小化到托盘时通知。"""
        """EN: Sets the tray controller reference. Used to minimize notifications when reaching the pallet."""
        self.tray_controller = tray_controller

    def prepare_for_exit(self):
        """准备退出。停止计时器并关闭活动菜单。"""
        """EN: Ready to quit. Stop the timer and close the active menu."""
        self._is_exiting = True

        if self.tick_timer.isActive():
            self.tick_timer.stop()

        if self.idle.rest_decision_timer.isActive():
            self.idle.rest_decision_timer.stop()

        if self.idle.rest_end_timer.isActive():
            self.idle.rest_end_timer.stop()

        if self.active_menu is not None:
            self.active_menu.close()
            if self.active_menu is not self._context_menu:
                self.active_menu.deleteLater()
            self.active_menu = None

        if self._context_menu is not None:
            try:
                self._context_menu.aboutToHide.disconnect(self._on_menu_hide)
            except Exception:
                pass
            self._context_menu.close()
            self._context_menu.deleteLater()
            self._context_menu = None

        if hasattr(self, "label") and hasattr(self.label, "clear_movie"):
            self.label.clear_movie()

        all_movies = list(self.movies.values()) + list(self.rest_movies)
        for movie in all_movies:
            try:
                movie.stop()
            except Exception:
                pass
            try:
                movie.deleteLater()
            except Exception:
                pass

        self.movies.clear()
        self.rest_movies.clear()

    def apply_autostart(self, enabled: bool):
        """本地应用开机自启设置。"""
        """EN: Local app bootup autostart settings."""
        set_autostart_enabled(bool(enabled))
        self.autostart_changed.emit(bool(enabled))

    def on_toggle_autostart(self, checked=False):
        """处理开机自启开关事件。优先委托实例管理器。"""
        """EN: Handles power-on self on/off switch events. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_toggle_autostart(checked)
            return

        self.apply_autostart(bool(checked))

    def on_set_autostart(self, enabled):
        """设置开机自启。优先委托实例管理器。"""
        """EN: Set the boot to auto-start. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_set_autostart(bool(enabled))
            return

        self.apply_autostart(bool(enabled))

    def get_autostart_enabled(self) -> bool:
        """读取自启状态。用于决定菜单项是否勾选。"""
        """EN: Reads the startup state. Used to decide if a menu item is checked."""
        if self.instance_manager is not None:
            return self.instance_manager.get_autostart_enabled()
        return is_autostart_enabled()

    def apply_opacity_percent(self, percent: int):
        """本地应用透明度百分比。"""
        """EN: Percentage of transparency applied locally."""
        try:
            normalized = int(percent)
        except (TypeError, ValueError):
            normalized = OPACITY_DEFAULT_PERCENT

        normalized = max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, normalized))
        self.opacity_percent = normalized
        self.setWindowOpacity(normalized / 100.0)
        self.opacity_changed.emit(normalized)

    def on_set_opacity_percent(self, percent: int):
        """设置透明度。优先委托实例管理器。"""
        """EN: Set transparency. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_set_opacity_percent(percent)
            return

        self.apply_opacity_percent(percent)

    def get_opacity_percent(self) -> int:
        """读取透明度百分比。"""
        """EN: Reads the transparency percentage."""
        if self.instance_manager is not None and hasattr(self.instance_manager, "get_opacity_percent"):
            return self.instance_manager.get_opacity_percent()
        return self.opacity_percent

    def on_set_display_mode(self, mode: str):
        """设置显示模式。优先委托实例管理器。"""
        """EN: Sets the display mode. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_set_display_mode(mode)
            return

        valid_mode = mode if isinstance(mode, str) else DISPLAY_MODE_ALWAYS_ON_TOP
        self.display_mode_changed.emit(valid_mode)

    def get_display_mode(self) -> str:
        """读取显示模式。无管理器时返回默认模式。"""
        """EN: Reads the display mode. Return to the default mode when there is no manager."""
        if self.instance_manager is not None:
            if hasattr(self.instance_manager, "get_display_mode"):
                return self.instance_manager.get_display_mode()
            return getattr(self.instance_manager, "display_mode", DISPLAY_MODE_ALWAYS_ON_TOP)
        return DISPLAY_MODE_ALWAYS_ON_TOP

    def set_always_on_top(self, enabled: bool):
        """动态切换置顶标志，并保持窗口可见状态。"""
        """EN: Dynamically toggle the sticky logo and keep the window visible."""
        self._always_on_top = bool(enabled)
        self._apply_topmost_state()

    def set_force_topmost_for_multi(self, enabled: bool):
        """多开时临时强制置顶。不修改用户显示优先级配置。"""
        """EN: Temporarily force it to the top when it is more open. Do not modify the user display priority configuration."""
        self._force_topmost_for_multi = bool(enabled)
        self._apply_topmost_state()

    def _apply_topmost_state(self):
        """应用最终置顶状态：用户设置 OR 多开临时置顶。"""
        """EN: App final sticky status: The user sets the OR to temporarily sticky."""
        should_topmost = self._always_on_top or self._force_topmost_for_multi
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, should_topmost)
        if was_visible:
            self.show()
            if should_topmost:
                self.raise_()

    def on_set_instance_count(self, count: int):
        """设置实例数量。优先委托实例管理器。"""
        """EN: Set the number of instances. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None:
            self.instance_manager.on_set_instance_count(count)
            return

        try:
            normalized = int(count)
        except (TypeError, ValueError):
            normalized = INSTANCE_COUNT_MIN
        normalized = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, normalized))
        self.instance_count_changed.emit(normalized)

    def get_instance_count(self) -> int:
        """读取实例数量。无管理器时返回 1。"""
        """EN: Number of read instances. Returns 1 when there is no manager."""
        if self.instance_manager is not None:
            if hasattr(self.instance_manager, "get_instance_count"):
                return self.instance_manager.get_instance_count()
            return getattr(self.instance_manager, "target_count", INSTANCE_COUNT_MIN)
        return INSTANCE_COUNT_MIN

    def apply_language(self, language: str):
        """本地应用界面语言，并刷新上下文菜单缓存。"""
        """EN: Local app interface language and refresh the context menu cache."""
        self.language = normalize_language(language)
        self.language_changed.emit(self.language)
        if self._context_menu is not None:
            try:
                self._context_menu.aboutToHide.disconnect(self._on_menu_hide)
            except Exception:
                pass
            self._context_menu.close()
            self._context_menu.deleteLater()
            self._context_menu = None

    def on_set_language(self, language: str):
        """设置语言。优先委托实例管理器。"""
        """EN: Set the language. Preferred Delegation Instance Manager."""
        if self.instance_manager is not None and hasattr(self.instance_manager, "on_set_language"):
            self.instance_manager.on_set_language(language)
            return
        self.apply_language(language)

    def get_language(self) -> str:
        """读取当前界面语言。"""
        """EN: Reads the current interface language."""
        if self.instance_manager is not None and hasattr(self.instance_manager, "get_language"):
            return normalize_language(self.instance_manager.get_language())
        return normalize_language(self.language)

    def on_set_instance_count_prompt(self):
        """弹窗输入实例数量。校验范围 1~50。"""
        """EN: Popup Enter the number of instances. Calibration range 1 ~ 50."""
        language = self.get_language()
        text, ok = QInputDialog.getText(
            self,
            tr(language, "menu.multi_instance"),
            tr(language, "menu.set_instance_count", min_count=INSTANCE_COUNT_MIN, max_count=INSTANCE_COUNT_MAX) + "：",
        )
        if not ok:
            return

        try:
            count = int(str(text).strip())
        except (TypeError, ValueError):
            QMessageBox.warning(self, tr(language, "common.hint"), tr(language, "common.input_number"))
            return

        if count < INSTANCE_COUNT_MIN:
            QMessageBox.warning(self, tr(language, "common.hint"), tr(language, "common.too_few"))
            return

        if count > INSTANCE_COUNT_MAX:
            QMessageBox.warning(self, tr(language, "common.hint"), tr(language, "common.too_many"))
            return

        self.on_set_instance_count(count)

    def on_close_current_pet(self):
        """关闭当前桌宠。无管理器时退化为退出当前应用。"""
        """EN: Closes the current table pet. Degrades to quit the current app when there is no manager."""
        if self.instance_manager is not None:
            self.instance_manager.close_current_pet(self)
            return

        self.on_exit()

    def on_close_random_pets_prompt(self):
        """弹窗输入随机关闭数量。非法输入按过少/过多提示。"""
        """EN: The pop-up window enters the random number of closes. Illegal input pressed too few/too many prompts."""
        if self.instance_manager is None:
            self.on_exit()
            return

        language = self.get_language()
        text, ok = QInputDialog.getText(self, tr(language, "menu.close_random"), tr(language, "dialog.close_random_input"))
        if not ok:
            return

        try:
            count = int(str(text).strip())
        except (TypeError, ValueError):
            QMessageBox.warning(self, tr(language, "common.hint"), tr(language, "common.input_number"))
            return

        if count < INSTANCE_COUNT_MIN:
            QMessageBox.warning(self, tr(language, "common.hint"), tr(language, "common.too_few"))
            return

        if count > INSTANCE_COUNT_MAX:
            QMessageBox.warning(self, tr(language, "common.hint"), tr(language, "common.too_many"))
            return

        self.instance_manager.close_random_pets(count)

    def on_close_all_pets(self):
        """关闭全部桌宠。无管理器时退化为退出当前应用。"""
        """EN: Close all table pets. Degrades to quit the current app when there is no manager."""
        if self.instance_manager is not None:
            self.instance_manager.close_all_pets()
            return

        self.on_exit()

    def build_menu(self):
        """创建右键菜单。菜单项由独立模块构建。"""
        """EN: Creates a context menu. Menu items are built by separate modules."""
        if self._context_menu is None:
            self._context_menu = build_context_menu(
                self,
                self.music_player,
                language=self.get_language(),
                on_set_language=self.on_set_language,
            )
            self._context_menu.aboutToHide.connect(self._on_menu_hide)
        sync_context_menu_state(self._context_menu, self, self.music_player, language=self.get_language())
        return self._context_menu

    def show_context_menu(self, global_pos):
        """在鼠标处弹出菜单。菜单位置固定，弹出实例显示描边。"""
        """EN: A menu pops up at the mouse. The menu position is fixed, and the pop-up instance shows the stroke."""
        self.active_menu = self.build_menu()
        # 显示天蓝色描边
        # EN: Show sky blue strokes
        self._menu_open = True
        self.update()
        self.active_menu.popup(global_pos)

    def _on_menu_hide(self):
        """菜单关闭时取消描边。"""
        """EN: Cancels the stroke when the menu closes."""
        self._menu_open = False
        self.update()

    def _clear_context_menu(self):
        """清理菜单引用。菜单关闭后释放当前活动菜单句柄。"""
        """EN: Cleanup menu references. Release the currently active menu handle when the menu is closed."""
        self.active_menu = None

    def _sync_context_menu_position(self):
        """同步菜单位置。保留方法以兼容外部调用，但菜单已不跟随移动。"""
        """EN: Sync menu locations. The method is reserved for external calls, but the menu no longer follows the move."""
        pass

    def moveEvent(self, event):
        """处理窗口移动事件。"""
        """EN: Handles window movement events."""
        super().moveEvent(event)

    def paintEvent(self, event):
        """绘制窗口。菜单开启时在边缘绘制天蓝色描边。"""
        """EN: Draws a window. Draws sky blue strokes on the edges when the menu opens."""
        super().paintEvent(event)
        if self._menu_open:
            painter = QPainter(self)
            pen = QPen(QColor("#00BFFF"))
            pen.setWidth(3)
            painter.setPen(pen)
            # 描边紧贴内边缘（各边各内缩 1px以内）
            # EN: Stroke close to the inner edge (within 1px of each edge)
            rect = self.rect().adjusted(1, 1, -2, -2)
            painter.drawRect(rect)
            painter.end()

    def mousePressEvent(self, event):
        """处理鼠标按下事件。优先交给输入模块消费。"""
        """EN: Handles mouse down events. Priority is given to input module consumption."""
        if handle_mouse_press(self, event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件。优先交给输入模块消费。"""
        """EN: Handles mouse movement events. Priority is given to input module consumption."""
        if handle_mouse_move(self, event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件。优先交给输入模块消费。"""
        """EN: Handles mouse release events. Priority is given to input module consumption."""
        if handle_mouse_release(self, event):
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """处理鼠标双击事件。左键双击打开独立聊天窗口。"""
        """EN: Handle mouse double-click events. Double-click left button opens chat window."""
        if event.button() == Qt.MouseButton.LeftButton and callable(self.on_open_chat):
            self.on_open_chat()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def event(self, event):
        """处理通用事件。失焦时执行越界修正。"""
        """EN: Handle common events. Perform out-of-focus correction when out of focus."""
        if event.type() == QEvent.Type.WindowDeactivate:
            self.movement.constrain_to_screen()
        return super().event(event)

    def closeEvent(self, event):
        """处理关闭事件。支持托盘最小化、程序退出和取消。"""
        """EN: Handles shutdown events. Supports pallet minimization, program exit, and cancellation."""
        if self._is_exiting:
            event.accept()
            return

        if self.close_policy is None:
            event.accept()
            return

        decision = self.close_policy.decide(self)
        if decision == "tray":
            event.ignore()
            self.hide()
            if self.tray_controller is not None:
                self.tray_controller.notify_minimized()
            return

        if decision == "quit":
            event.accept()
            if self.on_request_quit is not None:
                self.on_request_quit()
            else:
                self.prepare_for_exit()
                self.close()
            return

        event.ignore()
