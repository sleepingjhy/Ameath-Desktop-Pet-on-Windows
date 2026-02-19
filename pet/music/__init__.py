"""音乐功能库导出。"""

from .music_player import (
    MODE_ICONS,
    PLAY_MODE_LIST,
    PLAY_MODE_RANDOM,
    PLAY_MODE_SINGLE,
    MusicPlayer,
)

__all__ = [
    "MusicPlayer",
    "PLAY_MODE_LIST",
    "PLAY_MODE_SINGLE",
    "PLAY_MODE_RANDOM",
    "MODE_ICONS",
]
