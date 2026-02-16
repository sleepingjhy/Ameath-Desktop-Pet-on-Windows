"""该模块负责 GIF 播放与绘制。实现缩放、镜像和帧更新。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMovie, QPainter, QTransform
from PySide6.QtWidgets import QLabel

from .config import SCALE_MAX, SCALE_MIN


class GifLabel(QLabel):
    """这是 GIF 标签控件。支持镜像显示和比例缩放。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._movie: QMovie | None = None
        self._mirror = False
        self._scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_movie(self, movie: QMovie):
        """切换当前 GIF。切换时同步重连帧变化回调。"""
        if self._movie is not None:
            try:
                # 先解绑旧信号。避免重复连接导致重复刷新。
                self._movie.frameChanged.disconnect(self._on_frame_changed)
            except (RuntimeError, TypeError):
                pass

        self._movie = movie
        # 新动画要绑定帧回调。每帧变化都刷新尺寸和绘制。
        self._movie.frameChanged.connect(self._on_frame_changed)
        self._movie.start()
        self._resize_to_frame()
        self.update()

    def set_mirror(self, mirror: bool):
        """设置镜像开关。向左移动时通常开启水平镜像。"""
        if self._mirror != mirror:
            self._mirror = mirror
            self.update()

    def set_scale(self, scale: float):
        """设置显示比例。变更后立即刷新尺寸和绘制。"""
        self._scale = max(SCALE_MIN, min(SCALE_MAX, scale))
        self._resize_to_frame()
        self.update()

    def _on_frame_changed(self, _: int):
        """处理帧变化。帧变化时同步控件大小并重绘。"""
        self._resize_to_frame()
        self.update()

    def _resize_to_frame(self):
        """更新标签尺寸。依据当前帧尺寸和缩放比例计算。"""
        if self._movie is None:
            return

        # 优先读取像素图尺寸。失败时回退到当前图像尺寸。
        pix = self._movie.currentPixmap()
        if pix.isNull():
            size = self._movie.currentImage().size()
            if size.isEmpty():
                return
            width, height = size.width(), size.height()
        else:
            width, height = pix.width(), pix.height()

        self.resize(max(1, int(width * self._scale)), max(1, int(height * self._scale)))

    def paintEvent(self, event):
        """执行自定义绘制。先缩放，再按需镜像后输出到控件。"""
        if self._movie is None:
            return super().paintEvent(event)

        pix = self._movie.currentPixmap()
        if pix.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        target_w = max(1, int(pix.width() * self._scale))
        target_h = max(1, int(pix.height() * self._scale))

        if self.width() != target_w or self.height() != target_h:
            self.resize(target_w, target_h)

        scaled = pix.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        if self._mirror:
            # 镜像模式绘制翻转帧。用于角色向左移动。
            transform = QTransform()
            transform.scale(-1, 1)
            mirrored = scaled.transformed(transform, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(0, 0, mirrored)
            return

        painter.drawPixmap(0, 0, scaled)


def create_movie(path):
    """创建 QMovie 实例。统一配置缓存和播放速度。"""
    movie = QMovie(str(path))
    # 开启帧缓存。减少重复读取带来的开销。
    movie.setCacheMode(QMovie.CacheMode.CacheAll)
    movie.setSpeed(100)
    return movie
