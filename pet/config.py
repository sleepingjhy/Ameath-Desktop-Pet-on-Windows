"""该模块集中管理配置。统一维护资源路径与运行参数。"""

import sys
from pathlib import Path

# 定义核心目录。支持源码运行与打包运行两种路径模式。
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
GIFS_DIR = ROOT_DIR / "gifs"
MUSIC_DIR = ROOT_DIR / "music"
RESOURCE_PREFIX = ":/gifs"

# 定义应用标识与通用资源路径。
APP_NAME = "AmeathDesktopPet"
APP_ICON_PATH = f"{RESOURCE_PREFIX}/ameath.ico"
ABOUT_GIF_PATH = f"{RESOURCE_PREFIX}/ameath.gif"

# 建立动画资源映射。按动作类别组织 GIF 文件路径。
ASSET_PATHS = {
    "move": f"{RESOURCE_PREFIX}/move.gif",
    "drag": f"{RESOURCE_PREFIX}/drag.gif",
    "rest": [
        f"{RESOURCE_PREFIX}/ameath.gif",
        f"{RESOURCE_PREFIX}/idle1.gif",
        f"{RESOURCE_PREFIX}/idle2.gif",
        f"{RESOURCE_PREFIX}/idle3.gif",
        f"{RESOURCE_PREFIX}/idle4.gif",
    ],
}

# 定义缩放菜单参数。范围由最小值、最大值和步进共同决定。
SCALE_MIN = 0.1
SCALE_MAX = 2.0
SCALE_STEP = 0.1

# 定义显示模式。用于控制桌宠在不同前台窗口场景下的显示策略。
DISPLAY_MODE_ALWAYS_ON_TOP = "always_on_top"
DISPLAY_MODE_FULLSCREEN_HIDE = "fullscreen_hide"
DISPLAY_MODE_DESKTOP_ONLY = "desktop_only"

# 定义实例数量限制。用于多开桌宠的数量校验。
INSTANCE_COUNT_MIN = 0
INSTANCE_COUNT_MAX = 50

# 定义透明度参数。设置页支持 0~100，无级滑动；右键菜单支持 10~100，步进 10。
OPACITY_PERCENT_MIN = 0
OPACITY_PERCENT_MAX = 100
OPACITY_DEFAULT_PERCENT = 100
OPACITY_MENU_MIN = 10
OPACITY_MENU_STEP = 10

# 定义移动行为参数。包含主循环节拍、分辨率速度与触边停顿设置。
MOVE_TICK_MS = 16
CROSS_SCREEN_SECONDS = 20.0
FOLLOW_SPEED_MULTIPLIER = 1.4
VERTICAL_SPEED_FACTOR = 0.35
VERTICAL_CHANGE_TICK_RANGE = (30, 120)
EDGE_PAUSE_MS = 500

# 定义开机自启键名。用于写入 Windows Run 注册表项。
APP_AUTOSTART_NAME = "DesktopPetAmeath"

# 定义音乐播放器默认参数。
MUSIC_DEFAULT_VOLUME = 0.5

# 定义随机休息参数。控制休息判定频率、休息时长和触发概率。
REST_DECISION_MS_RANGE = (3500, 9000)
REST_DURATION_MS_RANGE = (2000, 6000)
REST_CHANCE_WHEN_MOVING = 0.23
REST_CHANCE_WHEN_STOPPED = 0.55
