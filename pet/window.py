"""该模块是桌宠主窗口。整合动画、输入、状态机、菜单与控制器。"""

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox, QWidget

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
from .menu import build_context_menu
from .movement import MovementController
from .state_machine import PetStateMachine


class DesktopPet(QWidget):
    """这是桌宠主窗口类。负责运行时调度和界面事件分发。"""

    follow_changed = Signal(bool)
    scale_changed = Signal(float)
    autostart_changed = Signal(bool)
    display_mode_changed = Signal(str)
    instance_count_changed = Signal(int)
    opacity_changed = Signal(int)

    def __init__(self, on_open_main=None, on_request_quit=None, close_policy=None, instance_manager=None):
        """完成主窗口初始化。包括资源校验、控制器构造和定时器启动。"""
        super().__init__()

        # 先做资源校验。避免运行中才发现 GIF 缺失。
        self._assert_assets()

        # 配置桌宠窗口样式。无边框、置顶、工具窗组合。
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.label = GifLabel(self)
        # 预加载移动/拖拽动画与休息动画集合。
        self.movies = {
            "move": create_movie(ASSET_PATHS["move"]),
            "drag": create_movie(ASSET_PATHS["drag"]),
        }
        self.rest_movies = [create_movie(path) for path in ASSET_PATHS["rest"]]

        self.state = PetStateMachine()
        self.scale_factor = 1.0
        self.opacity_percent = OPACITY_DEFAULT_PERCENT
        self.drag_offset = QPoint(0, 0)
        self.facing_left = False
        self.active_menu = None
        self.menu_anchor_offset = QPoint(0, 0)
        self.menu_last_pet_pos = QPoint(0, 0)
        self.follow_blocked = False
        self.on_open_main = on_open_main
        self.on_request_quit = on_request_quit
        self.close_policy = close_policy
        self.tray_controller = None
        self._is_exiting = False
        self.instance_manager = instance_manager

        self.movement = MovementController(self)
        self.idle = IdleController(self)

        # 默认进入移动动画。初始朝向设为向右。
        self._set_animation("move", mirror=False)

        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self._tick)
        self.tick_timer.start(MOVE_TICK_MS)

        self.idle.start()
        self.movement.place_initial()
        self.show()

    def _assert_assets(self):
        """校验动画资源完整性。缺失时抛出带列表的异常。"""
        missing = []
        for key, value in ASSET_PATHS.items():
            if isinstance(value, list):
                for path in value:
                    if not path.exists():
                        missing.append(str(path))
            elif not value.exists():
                missing.append(str(value))

        if missing:
            raise FileNotFoundError("缺少 GIF 资源:\n" + "\n".join(missing))

    def _set_animation(self, key: str, mirror: bool):
        """切换基础动作动画。仅处理移动/拖拽并同步镜像状态。"""
        if key == "move":
            movie = self.movies["move"]
        else:
            movie = self.movies["drag"]

        if self.label._movie is not movie:
            self.label.set_movie(movie)
        self.label.set_mirror(mirror)

    def show_rest_animation(self):
        """播放静止/休息动画。从休息资源中随机选择并播放。"""
        import random

        movie = random.choice(self.rest_movies)
        if self.label._movie is not movie:
            self.label.set_movie(movie)
        self.label.set_mirror(False)

    def set_drag_animation(self):
        """切到拖拽动画。拖拽状态始终使用该动画。"""
        self._set_animation("drag", mirror=False)

    def _apply_state_animation(self):
        """按状态优先级更新动画。拖拽优先，其次休息，再到移动。"""
        if self.state.is_dragging:
            self._set_animation("drag", mirror=False)
            return

        if self.state.in_rest:
            return

        self._set_animation("move", mirror=self.facing_left)

    def _tick(self):
        """执行主循环调度。按拖拽>跟随>休息>自主移动优先级处理。"""
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
        self.state.stop_move()
        self.state.exit_rest()
        self.follow_blocked = False
        self.follow_changed.emit(self.state.follow_mouse)
        self.idle.try_enter_rest()
        if not self.state.in_rest:
            self._set_animation("move", mirror=self.facing_left)

    def on_stop_move(self, checked=False):
        """处理停止移动菜单事件。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_stop_move()
            return

        self.apply_stop_move()

    def apply_follow_enabled(self, enabled: bool):
        """本地应用跟随状态。"""
        self.state.set_follow_mouse(bool(enabled))
        self.follow_blocked = False
        self.follow_changed.emit(self.state.follow_mouse)
        self._apply_state_animation()

    def on_toggle_follow(self, checked=False):
        """处理跟随鼠标开关事件。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_toggle_follow()
            return

        self.apply_follow_enabled(not self.state.follow_mouse)

    def on_set_follow(self, enabled):
        """设置跟随鼠标状态。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_set_follow(bool(enabled))
            return

        self.apply_follow_enabled(bool(enabled))

    def apply_scale(self, scale: float):
        """本地应用缩放。"""
        try:
            normalized = float(scale)
        except (TypeError, ValueError):
            return

        # 先应用缩放。重置窗口尺寸后再纠正位置。
        old_pos = self.pos()
        self.scale_factor = normalized
        self.label.set_scale(normalized)
        self.resize(self.label.size())
        self.move(old_pos)
        self.movement.constrain_to_screen()
        self.scale_changed.emit(self.scale_factor)

    def on_set_scale(self, scale: float):
        """处理缩放菜单事件。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_set_scale(scale)
            return

        self.apply_scale(scale)

    def on_exit(self, checked=False):
        """处理退出菜单事件。优先走应用级退出回调。"""
        if self.on_request_quit is not None:
            self.on_request_quit()
            return

        self.prepare_for_exit()
        self.close()

    def set_tray_controller(self, tray_controller):
        """设置托盘控制器引用。用于最小化到托盘时通知。"""
        self.tray_controller = tray_controller

    def prepare_for_exit(self):
        """准备退出。停止计时器并关闭活动菜单。"""
        self._is_exiting = True

        if self.tick_timer.isActive():
            self.tick_timer.stop()

        if self.idle.rest_decision_timer.isActive():
            self.idle.rest_decision_timer.stop()

        if self.idle.rest_end_timer.isActive():
            self.idle.rest_end_timer.stop()

        if self.active_menu is not None:
            self.active_menu.close()

    def apply_autostart(self, enabled: bool):
        """本地应用开机自启设置。"""
        set_autostart_enabled(bool(enabled))
        self.autostart_changed.emit(bool(enabled))

    def on_toggle_autostart(self, checked=False):
        """处理开机自启开关事件。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_toggle_autostart(checked)
            return

        self.apply_autostart(bool(checked))

    def on_set_autostart(self, enabled):
        """设置开机自启。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_set_autostart(bool(enabled))
            return

        self.apply_autostart(bool(enabled))

    def get_autostart_enabled(self) -> bool:
        """读取自启状态。用于决定菜单项是否勾选。"""
        if self.instance_manager is not None:
            return self.instance_manager.get_autostart_enabled()
        return is_autostart_enabled()

    def apply_opacity_percent(self, percent: int):
        """本地应用透明度百分比。"""
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
        if self.instance_manager is not None:
            self.instance_manager.on_set_opacity_percent(percent)
            return

        self.apply_opacity_percent(percent)

    def get_opacity_percent(self) -> int:
        """读取透明度百分比。"""
        if self.instance_manager is not None and hasattr(self.instance_manager, "get_opacity_percent"):
            return self.instance_manager.get_opacity_percent()
        return self.opacity_percent

    def on_set_display_mode(self, mode: str):
        """设置显示模式。优先委托实例管理器。"""
        if self.instance_manager is not None:
            self.instance_manager.on_set_display_mode(mode)
            return

        valid_mode = mode if isinstance(mode, str) else DISPLAY_MODE_ALWAYS_ON_TOP
        self.display_mode_changed.emit(valid_mode)

    def get_display_mode(self) -> str:
        """读取显示模式。无管理器时返回默认模式。"""
        if self.instance_manager is not None:
            if hasattr(self.instance_manager, "get_display_mode"):
                return self.instance_manager.get_display_mode()
            return getattr(self.instance_manager, "display_mode", DISPLAY_MODE_ALWAYS_ON_TOP)
        return DISPLAY_MODE_ALWAYS_ON_TOP

    def set_always_on_top(self, enabled: bool):
        """动态切换置顶标志，并保持窗口可见状态。"""
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(enabled))
        if was_visible:
            self.show()

    def on_set_instance_count(self, count: int):
        """设置实例数量。优先委托实例管理器。"""
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
        if self.instance_manager is not None:
            if hasattr(self.instance_manager, "get_instance_count"):
                return self.instance_manager.get_instance_count()
            return getattr(self.instance_manager, "target_count", INSTANCE_COUNT_MIN)
        return INSTANCE_COUNT_MIN

    def on_set_instance_count_prompt(self):
        """弹窗输入实例数量。校验范围 1~50。"""
        text, ok = QInputDialog.getText(
            self,
            "多开数量",
            f"请输入桌宠数量（{INSTANCE_COUNT_MIN}-{INSTANCE_COUNT_MAX}）：",
        )
        if not ok:
            return

        try:
            count = int(str(text).strip())
        except (TypeError, ValueError):
            QMessageBox.warning(self, "提示", "请输入数字")
            return

        if count < INSTANCE_COUNT_MIN:
            QMessageBox.warning(self, "提示", "数量过少")
            return

        if count > INSTANCE_COUNT_MAX:
            QMessageBox.warning(self, "提示", "数量过多")
            return

        self.on_set_instance_count(count)

    def on_close_current_pet(self):
        """关闭当前桌宠。无管理器时退化为退出当前应用。"""
        if self.instance_manager is not None:
            self.instance_manager.close_current_pet(self)
            return

        self.on_exit()

    def on_close_random_pets_prompt(self):
        """弹窗输入随机关闭数量。非法输入按过少/过多提示。"""
        if self.instance_manager is None:
            self.on_exit()
            return

        text, ok = QInputDialog.getText(self, "随机关闭", "请输入关闭数量：")
        if not ok:
            return

        try:
            count = int(str(text).strip())
        except (TypeError, ValueError):
            QMessageBox.warning(self, "提示", "请输入数字")
            return

        if count < INSTANCE_COUNT_MIN:
            QMessageBox.warning(self, "提示", "数量过少")
            return

        if count > INSTANCE_COUNT_MAX:
            QMessageBox.warning(self, "提示", "数量过多")
            return

        self.instance_manager.close_random_pets(count)

    def on_close_all_pets(self):
        """关闭全部桌宠。无管理器时退化为退出当前应用。"""
        if self.instance_manager is not None:
            self.instance_manager.close_all_pets()
            return

        self.on_exit()

    def build_menu(self):
        """创建右键菜单。菜单项由独立模块构建。"""
        return build_context_menu(self)

    def show_context_menu(self, global_pos):
        """在鼠标处弹出菜单。记录偏移以支持菜单随桌宠移动。"""
        if self.active_menu is not None:
            self.active_menu.close()

        # 记录菜单与桌宠相对关系。后续按位移增量同步菜单。
        self.active_menu = self.build_menu()
        self.menu_anchor_offset = global_pos - self.pos()
        self.menu_last_pet_pos = QPoint(self.pos())
        self.active_menu.aboutToHide.connect(self._clear_context_menu)
        self.active_menu.popup(global_pos)

    def _clear_context_menu(self):
        """清理菜单引用。菜单关闭后释放当前活动菜单句柄。"""
        self.active_menu = None

    def _sync_context_menu_position(self):
        """同步菜单位置。主菜单与可见二级菜单都随桌宠平移。"""
        if self.active_menu is None or not self.active_menu.isVisible():
            return

        # 使用增量平移菜单。可减少子菜单抖动与错位。
        delta = self.pos() - self.menu_last_pet_pos
        if delta.isNull():
            return

        self.active_menu.move(self.active_menu.pos() + delta)

        for sub_menu in self.active_menu.findChildren(QMenu):
            if sub_menu.isVisible():
                sub_menu.move(sub_menu.pos() + delta)

        self.menu_last_pet_pos = QPoint(self.pos())

    def moveEvent(self, event):
        """处理窗口移动事件。移动后立即同步菜单坐标。"""
        super().moveEvent(event)
        self._sync_context_menu_position()

    def mousePressEvent(self, event):
        """处理鼠标按下事件。优先交给输入模块消费。"""
        if handle_mouse_press(self, event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件。优先交给输入模块消费。"""
        if handle_mouse_move(self, event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件。优先交给输入模块消费。"""
        if handle_mouse_release(self, event):
            return
        super().mouseReleaseEvent(event)

    def event(self, event):
        """处理通用事件。失焦时执行越界修正。"""
        if event.type() == QEvent.Type.WindowDeactivate:
            self.movement.constrain_to_screen()
        return super().event(event)

    def closeEvent(self, event):
        """处理关闭事件。支持托盘最小化、程序退出和取消。"""
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
