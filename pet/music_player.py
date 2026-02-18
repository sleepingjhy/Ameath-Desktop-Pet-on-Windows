"""全局音乐播放器单例。使用 QMediaPlayer + QAudioOutput 播放 music/ 目录下的 OGG 文件。"""

from __future__ import annotations

import os
import random
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal

# Windows 下优先使用 ffmpeg 后端以支持 .ogg，并补齐 PySide6 目录到 DLL 搜索路径。
if sys.platform.startswith("win"):
    try:
        import PySide6

        pyside_dir = Path(PySide6.__file__).resolve().parent
        pyside_dir_text = str(pyside_dir)
        os.environ["PATH"] = pyside_dir_text + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(pyside_dir_text)
    except Exception:
        pass

    os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from .config import MUSIC_DEFAULT_VOLUME, MUSIC_DIR

PLAY_MODE_LIST = "list"
PLAY_MODE_SINGLE = "single"
PLAY_MODE_RANDOM = "random"

MODE_ICONS = {
    PLAY_MODE_LIST: "🔁",
    PLAY_MODE_SINGLE: "🔂",
    PLAY_MODE_RANDOM: "🔀",
}


class MusicPlayer(QObject):
    """全局音乐播放器。管理播放列表、播放状态与音量控制。"""

    track_changed = Signal(int)          # 当前播放索引
    state_changed = Signal(str)          # "playing" / "paused" / "stopped"
    playlist_reordered = Signal()        # 播放列表顺序改变
    volume_changed = Signal(float)       # 音量 0.0~1.0
    mode_changed = Signal(str)           # 播放模式
    duration_changed = Signal(object)    # 总时长（毫秒，qint64）
    position_changed = Signal(object)    # 播放位置（毫秒，qint64）

    def __init__(self, parent=None):
        super().__init__(parent)

        self._audio_output = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_output)

        self._playlist: list[Path] = []
        self._current_index: int = -1
        self._play_mode: str = PLAY_MODE_LIST
        self._volume: float = MUSIC_DEFAULT_VOLUME

        self._audio_output.setVolume(self._volume)

        # 信号连接
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.positionChanged.connect(self._on_position_changed)

        self._load_playlist()

    # ------------------------------------------------------------------
    # 播放列表初始化
    # ------------------------------------------------------------------

    def _load_playlist(self):
        """扫描 music/ 目录，加载所有 OGG 文件。"""
        music_dir = Path(MUSIC_DIR)
        if music_dir.exists():
            files = sorted(music_dir.glob("*.ogg"))
            self._playlist = list(files)
        if self._playlist:
            self._current_index = 0

    # ------------------------------------------------------------------
    # 只读属性
    # ------------------------------------------------------------------

    @property
    def playlist(self) -> list[Path]:
        return list(self._playlist)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def play_mode(self) -> str:
        return self._play_mode

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def is_paused(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState

    @property
    def current_track_name(self) -> str:
        if 0 <= self._current_index < len(self._playlist):
            return self._playlist[self._current_index].stem
        return "（无歌曲）"

    @property
    def duration(self) -> int:
        return self._player.duration()

    @property
    def position(self) -> int:
        return self._player.position()

    # ------------------------------------------------------------------
    # 播放控制
    # ------------------------------------------------------------------

    def play(self, index: int | None = None):
        """播放指定索引（或当前索引）的歌曲。"""
        if not self._playlist:
            return
        if index is not None:
            self._current_index = max(0, min(index, len(self._playlist) - 1))
        if self._current_index < 0:
            self._current_index = 0
        path = self._playlist[self._current_index]
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()
        self.track_changed.emit(self._current_index)

    def toggle_pause(self):
        """切换播放/暂停。"""
        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
        else:
            self.play()

    def next(self):
        """切换到下一首（按播放模式决定跳转逻辑）。"""
        if not self._playlist:
            return
        n = len(self._playlist)
        if self._play_mode == PLAY_MODE_SINGLE:
            self._player.setPosition(0)
            self._player.play()
        elif self._play_mode == PLAY_MODE_RANDOM:
            idx = random.randint(0, n - 1)
            self.play(idx)
        else:
            self.play((self._current_index + 1) % n)

    def prev(self):
        """切换到上一首。"""
        if not self._playlist:
            return
        n = len(self._playlist)
        # 若已播放 3 秒以上，先回到开头
        if self._player.position() > 3000:
            self._player.setPosition(0)
        else:
            self.play((self._current_index - 1) % n)

    def stop(self):
        """停止播放。"""
        self._player.stop()

    # ------------------------------------------------------------------
    # 音量
    # ------------------------------------------------------------------

    def set_volume(self, volume: float):
        """设置应用级音量（0.0~1.0），不影响系统音量。"""
        v = max(0.0, min(1.0, float(volume)))
        self._volume = v
        self._audio_output.setVolume(v)
        self.volume_changed.emit(v)

    # ------------------------------------------------------------------
    # 播放模式
    # ------------------------------------------------------------------

    def set_mode(self, mode: str):
        """切换播放模式。mode 为 list / single / random 之一。"""
        if mode in (PLAY_MODE_LIST, PLAY_MODE_SINGLE, PLAY_MODE_RANDOM):
            self._play_mode = mode
            self.mode_changed.emit(mode)

    def cycle_mode(self):
        """循环切换播放模式：列表循环 → 单曲循环 → 随机播放 → 列表循环。"""
        order = [PLAY_MODE_LIST, PLAY_MODE_SINGLE, PLAY_MODE_RANDOM]
        idx = order.index(self._play_mode) if self._play_mode in order else 0
        self.set_mode(order[(idx + 1) % len(order)])

    # ------------------------------------------------------------------
    # 播放列表排序
    # ------------------------------------------------------------------

    def move_track(self, from_index: int, to_index: int):
        """将索引 from_index 的歌曲移动到 to_index 位置。"""
        n = len(self._playlist)
        if not (0 <= from_index < n and 0 <= to_index < n and from_index != to_index):
            return
        track = self._playlist.pop(from_index)
        self._playlist.insert(to_index, track)
        # 更新当前播放索引
        if self._current_index == from_index:
            self._current_index = to_index
        elif from_index < self._current_index <= to_index:
            self._current_index -= 1
        elif to_index <= self._current_index < from_index:
            self._current_index += 1
        self.playlist_reordered.emit()

    def add_track_from_file(self, file_path: str):
        """将本地音频文件拷贝到 music/ 目录并加入播放列表。返回 (ok, message)。"""
        try:
            src = Path(file_path).expanduser().resolve()
        except Exception:
            return False, "无效文件路径"

        if not src.exists() or not src.is_file():
            return False, "文件不存在"

        if src.suffix.lower() not in {".ogg", ".mp3", ".wav", ".flac", ".m4a"}:
            return False, "不支持的音频格式"

        music_dir = Path(MUSIC_DIR)
        music_dir.mkdir(parents=True, exist_ok=True)

        target = music_dir / src.name
        if target.exists():
            stem = src.stem
            suffix = src.suffix
            i = 1
            while True:
                candidate = music_dir / f"{stem} ({i}){suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                i += 1

        try:
            shutil.copy2(src, target)
        except Exception as exc:
            return False, f"复制失败：{exc}"

        self._playlist.append(target)
        if self._current_index < 0:
            self._current_index = 0
        self.playlist_reordered.emit()
        return True, str(target)

    def remove_track(self, index: int, delete_file: bool = True):
        """删除播放列表中的歌曲。delete_file=True 时同步删除 music/ 目录文件。"""
        n = len(self._playlist)
        if not (0 <= index < n):
            return False, "索引越界"

        was_playing = self.is_playing
        removed_path = self._playlist[index]
        removed_current = (index == self._current_index)

        if removed_current:
            self._player.stop()

        self._playlist.pop(index)

        if not self._playlist:
            self._current_index = -1
            self.track_changed.emit(-1)
        else:
            if index < self._current_index:
                self._current_index -= 1
            elif removed_current:
                self._current_index = min(index, len(self._playlist) - 1)
                if was_playing:
                    self.play(self._current_index)
                else:
                    self.track_changed.emit(self._current_index)

        if delete_file:
            try:
                if removed_path.exists():
                    removed_path.unlink()
            except Exception as exc:
                self.playlist_reordered.emit()
                return False, f"已移出列表，但删除文件失败：{exc}"

        self.playlist_reordered.emit()
        return True, "ok"

    def rename_track(self, index: int, new_name: str):
        """重命名播放列表歌曲，并同步修改 music/ 目录中的文件名。"""
        n = len(self._playlist)
        if not (0 <= index < n):
            return False, "索引越界"

        old_path = self._playlist[index]
        if not old_path.exists():
            return False, "源文件不存在"

        sanitized = str(new_name).strip().replace("\\", "_").replace("/", "_")
        if not sanitized:
            return False, "文件名不能为空"

        target_path = old_path.with_name(f"{sanitized}{old_path.suffix}")
        if target_path == old_path:
            return True, "名称未变化"
        if target_path.exists():
            return False, "目标文件名已存在"

        was_current = (index == self._current_index)
        was_playing = self.is_playing

        if was_current:
            try:
                self._player.stop()
            except Exception:
                pass

        try:
            old_path.rename(target_path)
        except Exception as exc:
            return False, f"重命名失败：{exc}"

        self._playlist[index] = target_path

        if was_current:
            try:
                self._player.setSource(QUrl.fromLocalFile(str(target_path)))
                if was_playing:
                    self._player.play()
            except Exception:
                pass
            self.track_changed.emit(self._current_index)

        self.playlist_reordered.emit()
        return True, "ok"

    # ------------------------------------------------------------------
    # 进度跳转
    # ------------------------------------------------------------------

    def seek(self, position_ms: int):
        """跳转到指定毫秒位置。"""
        self._player.setPosition(position_ms)

    def dispose(self):
        """释放播放器资源与信号连接。用于应用退出时避免对象残留。"""
        try:
            self._player.mediaStatusChanged.disconnect(self._on_media_status_changed)
        except Exception:
            pass
        try:
            self._player.playbackStateChanged.disconnect(self._on_playback_state_changed)
        except Exception:
            pass
        try:
            self._player.durationChanged.disconnect(self._on_duration_changed)
        except Exception:
            pass
        try:
            self._player.positionChanged.disconnect(self._on_position_changed)
        except Exception:
            pass

        try:
            self._player.stop()
            self._player.setSource(QUrl())
        except Exception:
            pass

        try:
            self._playlist.clear()
            self._current_index = -1
        except Exception:
            pass

        try:
            self._player.deleteLater()
            self._audio_output.deleteLater()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 内部槽
    # ------------------------------------------------------------------

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        """媒体状态变化时自动衔接下一首。"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._play_mode == PLAY_MODE_SINGLE:
                self._player.setPosition(0)
                self._player.play()
            elif self._play_mode == PLAY_MODE_RANDOM:
                n = len(self._playlist)
                if n:
                    self.play(random.randint(0, n - 1))
            else:
                n = len(self._playlist)
                if n:
                    self.play((self._current_index + 1) % n)

    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        mapping = {
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
        }
        self.state_changed.emit(mapping.get(state, "stopped"))

    def _on_duration_changed(self, duration_ms):
        """转发 Qt qint64 时长信号，避免签名不匹配导致连接失败。"""
        self.duration_changed.emit(duration_ms)

    def _on_position_changed(self, position_ms):
        """转发 Qt qint64 位置信号，避免签名不匹配导致连接失败。"""
        self.position_changed.emit(position_ms)
