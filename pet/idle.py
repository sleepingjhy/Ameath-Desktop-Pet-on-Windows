"""该模块管理休息调度。按概率触发休息并在超时后恢复。"""

import random

from PySide6.QtCore import QTimer

from .config import (
    REST_CHANCE_WHEN_MOVING,
    REST_CHANCE_WHEN_STOPPED,
    REST_DECISION_MS_RANGE,
    REST_DURATION_MS_RANGE,
)


class IdleController:
    """这是休息控制器。通过计时器管理进入与退出。"""

    def __init__(self, pet):
        """初始化休息计时器。分别用于判定与结束回调。"""
        self.pet = pet

        self.rest_decision_timer = QTimer(pet)
        self.rest_decision_timer.timeout.connect(self.try_enter_rest)

        self.rest_end_timer = QTimer(pet)
        self.rest_end_timer.setSingleShot(True)
        self.rest_end_timer.timeout.connect(self.exit_rest)

    def start(self):
        """启动休息调度。立即安排首次休息判定。"""
        self.schedule_next_rest_decision()

    def schedule_next_rest_decision(self):
        """安排下一次判定。时间在配置区间内随机。"""
        self.rest_decision_timer.start(random.randint(*REST_DECISION_MS_RANGE))

    def try_enter_rest(self):
        """尝试进入休息。满足状态条件后按概率触发。"""
        self.schedule_next_rest_decision()

        # 高优先状态不休息。拖拽或跟随时直接跳过。
        if self.pet.state.is_dragging or self.pet.state.follow_mouse:
            return
        if self.pet.state.in_rest:
            return

        # 停止移动时更易休息。使用更高触发概率。
        chance = REST_CHANCE_WHEN_STOPPED if not self.pet.state.move_enabled else REST_CHANCE_WHEN_MOVING
        if random.random() > chance:
            return

        self.pet.state.enter_rest()
        self.pet.show_rest_animation()
        self.rest_end_timer.start(random.randint(*REST_DURATION_MS_RANGE))

    def exit_rest(self):
        """退出休息状态。清标记后恢复当前应有动画。"""
        self.pet.state.exit_rest()
        self.pet._apply_state_animation()
