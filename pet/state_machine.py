"""该模块是桌宠状态机。集中管理拖拽、跟随、移动、休息四类状态。"""

from dataclasses import dataclass


@dataclass
class PetStateMachine:
    """这是轻量状态容器。提供统一状态切换方法。"""

    is_dragging: bool = False
    follow_mouse: bool = False
    move_enabled: bool = True
    in_rest: bool = False

    def begin_drag(self):
        """进入拖拽状态。拖拽优先级最高并会退出休息。"""
        self.is_dragging = True
        self.in_rest = False

    def end_drag(self):
        """结束拖拽。仅清除拖拽标记。"""
        self.is_dragging = False

    def set_follow_mouse(self, enabled: bool):
        """设置跟随鼠标开关。开启时恢复移动并退出休息。"""
        self.follow_mouse = enabled
        if enabled:
            # 跟随时允许移动。否则无法持续追踪鼠标。
            self.move_enabled = True
            self.in_rest = False

    def toggle_follow_mouse(self):
        """切换跟随开关。内部复用 set_follow_mouse。"""
        self.set_follow_mouse(not self.follow_mouse)

    def stop_move(self):
        """停止移动能力。同时关闭跟随鼠标。"""
        self.move_enabled = False
        self.follow_mouse = False

    def enter_rest(self):
        """进入休息状态。仅设置休息标志位。"""
        self.in_rest = True

    def exit_rest(self):
        """退出休息状态。仅清除休息标志位。"""
        self.in_rest = False

    def state_key(self) -> str:
        """返回当前主状态标识。按照固定优先级进行判定。"""
        # 优先级固定。拖拽 > 跟随 > 休息 > 移动。
        if self.is_dragging:
            return "drag"
        if self.follow_mouse:
            return "follow"
        if self.in_rest:
            return "rest"
        return "move"
