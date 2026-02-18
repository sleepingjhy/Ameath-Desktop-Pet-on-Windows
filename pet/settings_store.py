"""该模块负责应用设置持久化。统一读写用户偏好到本地 JSON 文件。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import (
    APP_NAME,
    DISPLAY_MODE_ALWAYS_ON_TOP,
    DISPLAY_MODE_DESKTOP_ONLY,
    DISPLAY_MODE_FULLSCREEN_HIDE,
    INSTANCE_COUNT_MAX,
    INSTANCE_COUNT_MIN,
    OPACITY_DEFAULT_PERCENT,
    OPACITY_PERCENT_MAX,
    OPACITY_PERCENT_MIN,
    SCALE_MAX,
    SCALE_MIN,
)


class SettingsStore:
    """应用设置存储。提供读取、更新和保存能力。"""

    def __init__(self):
        """初始化设置路径并加载已有配置。"""
        self.settings_path = self._build_settings_path()
        self.data: dict[str, Any] = {
            "close_behavior": "ask",
            "display_mode": DISPLAY_MODE_ALWAYS_ON_TOP,
            "instance_count": INSTANCE_COUNT_MIN,
            "opacity_percent": OPACITY_DEFAULT_PERCENT,
            "follow_mouse": False,
            "scale_factor": 1.0,
        }
        self._load()

    def _build_settings_path(self) -> Path:
        """构建设置文件路径。Windows 放在 AppData/Roaming 下。"""
        appdata = os.getenv("APPDATA")
        if appdata:
            base_dir = Path(appdata) / APP_NAME
        else:
            base_dir = Path.home() / f".{APP_NAME.lower()}"

        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "settings.json"

    def _load(self):
        """从磁盘加载设置。失败时使用默认值。"""
        if not self.settings_path.exists():
            return

        try:
            loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, json.JSONDecodeError):
            return

    def save(self):
        """将当前设置写回磁盘。"""
        self.settings_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_close_behavior(self) -> str:
        """读取关闭行为配置。返回 ask、quit 或 tray。"""
        value = self.data.get("close_behavior", "ask")
        if value in {"ask", "quit", "tray"}:
            return value
        return "ask"

    def set_close_behavior(self, behavior: str):
        """更新关闭行为配置并保存。"""
        if behavior not in {"ask", "quit", "tray"}:
            return
        self.data["close_behavior"] = behavior
        self.save()

    def get_display_mode(self) -> str:
        """读取显示模式配置。返回 always_on_top、fullscreen_hide 或 desktop_only。"""
        value = self.data.get("display_mode", DISPLAY_MODE_ALWAYS_ON_TOP)
        if value in {
            DISPLAY_MODE_ALWAYS_ON_TOP,
            DISPLAY_MODE_FULLSCREEN_HIDE,
            DISPLAY_MODE_DESKTOP_ONLY,
        }:
            return value
        return DISPLAY_MODE_ALWAYS_ON_TOP

    def set_display_mode(self, mode: str):
        """更新显示模式配置并保存。非法值自动回退到默认模式。"""
        if mode not in {
            DISPLAY_MODE_ALWAYS_ON_TOP,
            DISPLAY_MODE_FULLSCREEN_HIDE,
            DISPLAY_MODE_DESKTOP_ONLY,
        }:
            mode = DISPLAY_MODE_ALWAYS_ON_TOP
        self.data["display_mode"] = mode
        self.save()

    def get_instance_count(self) -> int:
        """读取实例数量配置。返回范围限制在 1~50。"""
        value = self.data.get("instance_count", INSTANCE_COUNT_MIN)
        try:
            count = int(value)
        except (TypeError, ValueError):
            return INSTANCE_COUNT_MIN
        return max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, count))

    def set_instance_count(self, count: int):
        """更新实例数量配置并保存。保存前会裁剪到允许范围。"""
        try:
            normalized = int(count)
        except (TypeError, ValueError):
            normalized = INSTANCE_COUNT_MIN
        normalized = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, normalized))
        self.data["instance_count"] = normalized
        self.save()

    def get_opacity_percent(self) -> int:
        """读取透明度配置。返回范围限制在 0~100。"""
        value = self.data.get("opacity_percent", OPACITY_DEFAULT_PERCENT)
        try:
            percent = int(value)
        except (TypeError, ValueError):
            percent = OPACITY_DEFAULT_PERCENT
        return max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, percent))

    def set_opacity_percent(self, percent: int):
        """更新透明度配置并保存。保存前会裁剪到允许范围。"""
        try:
            normalized = int(percent)
        except (TypeError, ValueError):
            normalized = OPACITY_DEFAULT_PERCENT
        normalized = max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, normalized))
        self.data["opacity_percent"] = normalized
        self.save()

    def get_follow_mouse(self) -> bool:
        """读取跟随鼠标配置。"""
        return bool(self.data.get("follow_mouse", False))

    def set_follow_mouse(self, enabled: bool):
        """更新跟随鼠标配置并保存。"""
        self.data["follow_mouse"] = bool(enabled)
        self.save()

    def get_scale_factor(self) -> float:
        """读取缩放配置。返回范围限制在允许区间。"""
        value = self.data.get("scale_factor", 1.0)
        try:
            scale = float(value)
        except (TypeError, ValueError):
            scale = 1.0
        return max(SCALE_MIN, min(SCALE_MAX, scale))

    def set_scale_factor(self, scale: float):
        """更新缩放配置并保存。保存前会裁剪到允许范围。"""
        try:
            normalized = float(scale)
        except (TypeError, ValueError):
            normalized = 1.0
        normalized = max(SCALE_MIN, min(SCALE_MAX, normalized))
        self.data["scale_factor"] = normalized
        self.save()
