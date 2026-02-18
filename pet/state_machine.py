"""该模块是桌宠状态机。集中管理拖拽、跟随、移动、休息四类状态。"""
"""EN: This module defines the pet state machine for dragging, following, moving, and resting states."""

from dataclasses import dataclass


@dataclass
class PetStateMachine:
    """这是轻量状态容器。提供统一状态切换方法。"""
    """EN: This is a lightweight status container. Provides a unified state switching method."""

    is_dragging: bool = False
    follow_mouse: bool = False
    move_enabled: bool = True
    in_rest: bool = False

    def begin_drag(self):
        """进入拖拽状态。拖拽优先级最高并会退出休息。"""
        """EN: Enter the drag state. Dragging has the highest priority and exits the break."""
        self.is_dragging = True
        self.in_rest = False

    def end_drag(self):
        """结束拖拽。仅清除拖拽标记。"""
        """EN: End drag. Clears only drag marks."""
        self.is_dragging = False

    def set_follow_mouse(self, enabled: bool):
        """设置跟随鼠标开关。开启时恢复移动并退出休息。"""
        """EN: Set the follow mouse switch. Resume movement and exit rest when on."""
        self.follow_mouse = enabled
        if enabled:
            # 跟随时允许移动。否则无法持续追踪鼠标。
            # EN: Followers are allowed to move at any time. Otherwise, the mouse cannot be tracked continuously.
            self.move_enabled = True
            self.in_rest = False

    def toggle_follow_mouse(self):
        """切换跟随开关。内部复用 set_follow_mouse。"""
        """EN: Toggle the follow switch. Internal multiplex set_follow_mouse."""
        self.set_follow_mouse(not self.follow_mouse)

    def stop_move(self):
        """停止移动能力。同时关闭跟随鼠标。"""
        """EN: Stops the ability to move. Also closes the following mouse."""
        self.move_enabled = False
        self.follow_mouse = False

    def start_move(self):
        """恢复移动能力。"""
        """EN: Restore mobility."""
        self.move_enabled = True

    def set_move_enabled(self, enabled: bool):
        """设置移动开关。关闭时同时关闭跟随。"""
        """EN: Set the movement switch. Closes the follower when closed."""
        if enabled:
            self.start_move()
            return
        self.stop_move()

    def toggle_move(self):
        """切换移动开关。"""
        """EN: Toggle the mobile switch."""
        self.set_move_enabled(not self.move_enabled)

    def enter_rest(self):
        """进入休息状态。仅设置休息标志位。"""
        """EN: Enter the resting state. Set only the break flag bits."""
        self.in_rest = True

    def exit_rest(self):
        """退出休息状态。仅清除休息标志位。"""
        """EN: Exit the resting state. Clear the rest flag bits only."""
        self.in_rest = False

    def state_key(self) -> str:
        """返回当前主状态标识。按照固定优先级进行判定。"""
        """EN: Returns the current master status identification. Determine according to a fixed priority."""
        # 优先级固定。拖拽 > 跟随 > 休息 > 移动。
        # EN: Priority is fixed. Drag > Follow > Rest > Move.
        if self.is_dragging:
            return "drag"
        if self.follow_mouse:
            return "follow"
        if self.in_rest:
            return "rest"
        return "move"
