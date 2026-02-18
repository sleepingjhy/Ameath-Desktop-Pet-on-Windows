"""该模块负责桌宠位移控制。包含自动移动、跟随鼠标、边界约束和方向更新。"""

import random
import time

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

from .config import (
    CROSS_SCREEN_SECONDS,
    FOLLOW_SPEED_MULTIPLIER,
    MOVE_TICK_MS,
)


class MovementController:
    """这是桌宠位移控制器。统一管理速度、浮点坐标和边界行为。"""

    def __init__(self, pet):
        """初始化移动控制状态。设置速度、浮点坐标和触边停顿计时字段。"""
        self.pet = pet
        self.velocity_x = 1.0
        self.velocity_y = 0.0
        self.float_x = float(pet.x())
        self.float_y = float(pet.y())
        self.pause_until_ms = 0
        self.tick_count = 0
        self.direction_change_interval_ticks = max(1, int(round(3000 / MOVE_TICK_MS)))
        self.next_horizontal_change_tick = 0
        self.next_vertical_change_tick = 0

    def _sync_float_position(self):
        """同步浮点坐标到窗口坐标。避免长时间移动产生累计误差。"""
        self.float_x = float(self.pet.x())
        self.float_y = float(self.pet.y())

    def _base_speed_x(self, geometry: QRect) -> float:
        """按分辨率计算横向基准速度。目标是约 20 秒横穿可用宽度。"""
        # 先计算可移动横向距离。宽度需扣除桌宠自身宽度。
        travel_px = max(1, geometry.width() - self.pet.width())
        # 再换算每 tick 位移。总耗时除以主循环间隔得到 tick 总数。
        ticks = max(1.0, (CROSS_SCREEN_SECONDS * 1000.0) / MOVE_TICK_MS)
        return max(0.2, travel_px / ticks)

    def _base_speed_y(self, geometry: QRect) -> float:
        """按分辨率计算纵向基准速度。目标是约 20 秒纵穿可用高度。"""
        travel_px = max(1, geometry.height() - self.pet.height())
        ticks = max(1.0, (CROSS_SCREEN_SECONDS * 1000.0) / MOVE_TICK_MS)
        return max(0.2, travel_px / ticks)

    def _randomized_speed(self, base_speed: float) -> float:
        """在基准速度上应用随机浮动。范围为 0.8x~1.2x。"""
        factor = random.uniform(0.8, 1.2)
        return max(0.2, base_speed * factor)

    def _maybe_update_horizontal_velocity(self, base_speed_x: float):
        """按时间片独立更新横向速度。用于实现左右随机移动。"""
        if self.tick_count < self.next_horizontal_change_tick:
            return

        horizontal_speed = self._randomized_speed(base_speed_x)
        direction = random.choice([-1, 0, 1])
        self.velocity_x = float(direction) * horizontal_speed
        self.next_horizontal_change_tick = self.tick_count + self.direction_change_interval_ticks

    def _maybe_update_vertical_velocity(self, base_speed_y: float):
        """按时间片独立更新纵向速度。用于实现上下随机移动。"""
        if self.tick_count < self.next_vertical_change_tick:
            return

        vertical_speed = self._randomized_speed(base_speed_y)
        direction = random.choice([-1, 0, 1])
        self.velocity_y = float(direction) * vertical_speed
        self.next_vertical_change_tick = self.tick_count + self.direction_change_interval_ticks

    def place_initial(self):
        """设置桌宠初始位置。默认放在屏幕左下区域。"""
        screen = QApplication.primaryScreen()
        geometry: QRect = screen.availableGeometry()
        x = geometry.left() + int(geometry.width() * 0.15)
        y = geometry.top() + int(geometry.height() * 0.70)
        self.pet.move(x, y)
        self._sync_float_position()

    def constrain_to_screen(self):
        """约束窗口不越界。将窗口夹紧在当前屏幕可用区域内。"""
        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        geometry: QRect = screen.availableGeometry()

        x = self.pet.x()
        y = self.pet.y()

        if x < geometry.left():
            x = geometry.left()
        if x + self.pet.width() > geometry.right():
            x = geometry.right() - self.pet.width()

        if y < geometry.top():
            y = geometry.top()
        if y + self.pet.height() > geometry.bottom():
            y = geometry.bottom() - self.pet.height()

        self.pet.move(x, y)
        self._sync_float_position()

    def follow_cursor_tick(self) -> tuple[bool, bool]:
        """执行一次跟随鼠标更新。返回(是否发生位移, 是否因触边被阻挡)。"""
        cursor = QCursor.pos()
        target = QPoint(cursor.x() - self.pet.width() // 2, cursor.y() - self.pet.height() // 2)

        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        geometry: QRect = screen.availableGeometry()
        # 跟随速度基于分辨率。使用基准速度乘以跟随倍率。
        base_speed = self._base_speed_x(geometry)
        max_step = max(1, int(round(base_speed * FOLLOW_SPEED_MULTIPLIER)))

        dx = target.x() - self.pet.x()
        dy = target.y() - self.pet.y()

        step_x = max(-max_step, min(max_step, dx))
        step_y = max(-max_step, min(max_step, dy))

        if step_x == 0 and step_y == 0:
            return False, False

        current_x = self.pet.x()
        current_y = self.pet.y()
        desired_x = current_x + step_x
        desired_y = current_y + step_y

        min_x = geometry.left()
        max_x = geometry.right() - self.pet.width()
        min_y = geometry.top()
        max_y = geometry.bottom() - self.pet.height()

        clamped_x = max(min_x, min(max_x, desired_x))
        clamped_y = max(min_y, min(max_y, desired_y))

        moved = (clamped_x != current_x) or (clamped_y != current_y)
        blocked_by_edge = (desired_x != clamped_x) or (desired_y != clamped_y)

        if not moved:
            return False, blocked_by_edge

        self.pet.facing_left = step_x < 0
        self.pet._apply_state_animation()

        self.pet.move(clamped_x, clamped_y)
        self._sync_float_position()
        return True, blocked_by_edge

    def auto_move_tick(self):
        """执行一次自主移动。横向与纵向独立随机执行，触边后立即反弹。"""
        screen = QApplication.screenAt(self.pet.frameGeometry().center()) or QApplication.primaryScreen()
        geometry: QRect = screen.availableGeometry()
        base_speed_x = self._base_speed_x(geometry)
        base_speed_y = self._base_speed_y(geometry)

        self.tick_count += 1
        self._maybe_update_horizontal_velocity(base_speed_x)
        self._maybe_update_vertical_velocity(base_speed_y)

        now_ms = int(time.monotonic() * 1000)
        # 停顿期内不移动。触边后先停顿再允许下一次位移。
        if now_ms < self.pause_until_ms:
            return

        self.float_x += self.velocity_x
        self.float_y += self.velocity_y

        next_x = int(round(self.float_x))
        next_y = int(round(self.float_y))

        min_x = geometry.left()
        max_x = geometry.right() - self.pet.width()
        min_y = geometry.top()
        max_y = geometry.bottom() - self.pet.height()

        # 触边立即反弹：位置钳制到边界，并立刻反向速度。
        if next_x < min_x:
            next_x = min_x
            self.velocity_x = abs(self.velocity_x)
        elif next_x > max_x:
            next_x = max_x
            self.velocity_x = -abs(self.velocity_x)

        if next_y < min_y:
            next_y = min_y
            self.velocity_y = abs(self.velocity_y)
        elif next_y > max_y:
            next_y = max_y
            self.velocity_y = -abs(self.velocity_y)

        self.float_x = float(next_x)
        self.float_y = float(next_y)

        self.pet.facing_left = self.velocity_x < 0
        self.pet._apply_state_animation()
        self.pet.move(next_x, next_y)
