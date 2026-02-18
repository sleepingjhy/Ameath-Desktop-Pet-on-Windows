"""该模块是前端主界面。包含设置页和关于页。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QSize
from PySide6.QtGui import QCloseEvent, QIcon, QMovie
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import (
    ABOUT_GIF_PATH,
    APP_ICON_PATH,
    DISPLAY_MODE_ALWAYS_ON_TOP,
    DISPLAY_MODE_DESKTOP_ONLY,
    DISPLAY_MODE_FULLSCREEN_HIDE,
    INSTANCE_COUNT_MAX,
    INSTANCE_COUNT_MIN,
    OPACITY_DEFAULT_PERCENT,
    OPACITY_PERCENT_MAX,
    OPACITY_PERCENT_MIN,
    ROOT_DIR,
    SCALE_MAX,
    SCALE_MIN,
)


class AppWindow(QMainWindow):
    """应用主界面窗口。负责设置与关于页面展示。"""

    def __init__(self, pet, settings_store, close_policy, request_quit, tray_controller=None, music_player=None):
        """初始化界面、样式和交互绑定。"""
        super().__init__()
        self.pet = pet
        self.settings_store = settings_store
        self.close_policy = close_policy
        self.request_quit = request_quit
        self.tray_controller = tray_controller
        self.music_player = music_player
        self._is_exiting = False

        self.setWindowTitle("Ameath Desktop Pet")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setMinimumSize(980, 720)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.about_text_content = (
            "爱弥斯——变身~\n"
            "群星，皎映明日！\n"
            "此夜，星海澈明！\n"
            "救世之刻，已至！\n"
            "但愿我会让你感到骄傲\n"
            "但愿我不会让你失望😭\n\n"
            "❤️❤️❤️ 爱来自 jhy ❤️❤️❤️"
        )

        self._build_ui()
        self._bind_pet_state_sync()
        self._apply_theme()

    def _build_ui(self):
        """构建主界面布局和两个页面。"""
        root = QWidget(self)
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        nav_card = QFrame()
        nav_card.setObjectName("NavCard")
        nav_card.setFixedWidth(180)
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(8)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon(str(APP_ICON_PATH)).pixmap(44, 44))
        nav_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.settings_btn = QPushButton("设置")
        self.music_btn = QPushButton("🎵 音乐")
        self.about_btn = QPushButton("关于")
        self.settings_btn.setObjectName("NavButton")
        self.music_btn.setObjectName("NavButton")
        self.about_btn.setObjectName("NavButton")
        self.settings_btn.setFixedWidth(120)
        self.music_btn.setFixedWidth(120)
        self.about_btn.setFixedWidth(120)

        self.settings_btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.music_btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.about_btn.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        nav_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        nav_layout.addWidget(self.music_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        nav_layout.addWidget(self.about_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        nav_layout.addStretch(1)

        self.pages = QStackedWidget()
        self.pages.currentChanged.connect(self._on_page_changed)
        self.pages.addWidget(self._build_settings_page())   # index 0
        self.pages.addWidget(self._build_music_page())      # index 1
        self.pages.addWidget(self._build_about_page())      # index 2

        main_layout.addWidget(nav_card, stretch=0)
        main_layout.addWidget(self.pages, stretch=1)

    def _bind_pet_state_sync(self):
        """绑定桌宠状态信号，实现设置页控件实时同步。"""
        if hasattr(self.pet, "follow_changed"):
            self.pet.follow_changed.connect(self._on_pet_follow_changed)
        if hasattr(self.pet, "move_enabled_changed"):
            self.pet.move_enabled_changed.connect(self._on_pet_move_enabled_changed)
        if hasattr(self.pet, "scale_changed"):
            self.pet.scale_changed.connect(self._on_pet_scale_changed)
        if hasattr(self.pet, "autostart_changed"):
            self.pet.autostart_changed.connect(self._on_pet_autostart_changed)
        if hasattr(self.pet, "display_mode_changed"):
            self.pet.display_mode_changed.connect(self._on_pet_display_mode_changed)
        if hasattr(self.pet, "instance_count_changed"):
            self.pet.instance_count_changed.connect(self._on_pet_instance_count_changed)
        if hasattr(self.pet, "opacity_changed"):
            self.pet.opacity_changed.connect(self._on_pet_opacity_changed)

        # 绑定音乐播放器信号
        if self.music_player is not None:
            self.music_player.track_changed.connect(self._on_music_track_changed)
            self.music_player.state_changed.connect(self._on_music_state_changed)
            self.music_player.playlist_reordered.connect(self._on_music_playlist_reordered)
            self.music_player.volume_changed.connect(self._on_music_volume_changed)
            self.music_player.mode_changed.connect(self._on_music_mode_changed)
            self.music_player.duration_changed.connect(self._on_music_duration_changed)
            self.music_player.position_changed.connect(self._on_music_position_changed)

        self._sync_controls_from_pet()

    def _sync_controls_from_pet(self):
        """将设置页控件与当前桌宠状态对齐。"""
        self._on_pet_follow_changed(self.pet.state.follow_mouse)
        self._on_pet_move_enabled_changed(self._resolve_pet_move_enabled())
        self._on_pet_scale_changed(self.pet.scale_factor)
        self._on_pet_autostart_changed(self.pet.get_autostart_enabled())
        self._on_pet_display_mode_changed(self._resolve_pet_display_mode())
        self._on_pet_instance_count_changed(self._resolve_pet_instance_count())
        self._on_pet_opacity_changed(self._resolve_pet_opacity_percent())

    def _resolve_pet_display_mode(self) -> str:
        """读取当前显示模式。优先调用标准 getter。"""
        if hasattr(self.pet, "get_display_mode") and callable(self.pet.get_display_mode):
            mode = self.pet.get_display_mode()
            if isinstance(mode, str):
                return mode

        mode = getattr(self.pet, "display_mode", DISPLAY_MODE_ALWAYS_ON_TOP)
        if isinstance(mode, str):
            return mode
        return DISPLAY_MODE_ALWAYS_ON_TOP

    def _resolve_pet_instance_count(self) -> int:
        """读取当前实例数量。优先调用标准 getter。"""
        if hasattr(self.pet, "get_instance_count") and callable(self.pet.get_instance_count):
            value = self.pet.get_instance_count()
        else:
            value = getattr(self.pet, "target_count", INSTANCE_COUNT_MIN)

        try:
            count = int(value)
        except (TypeError, ValueError):
            count = INSTANCE_COUNT_MIN
        return max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, count))

    def _resolve_pet_opacity_percent(self) -> int:
        """读取当前透明度百分比。优先调用标准 getter。"""
        if hasattr(self.pet, "get_opacity_percent") and callable(self.pet.get_opacity_percent):
            value = self.pet.get_opacity_percent()
        else:
            value = getattr(self.pet, "opacity_percent", OPACITY_DEFAULT_PERCENT)

        try:
            opacity = int(value)
        except (TypeError, ValueError):
            opacity = OPACITY_DEFAULT_PERCENT
        return max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, opacity))

    def _resolve_pet_move_enabled(self) -> bool:
        """读取当前移动开关。优先调用标准 getter。"""
        if hasattr(self.pet, "get_move_enabled") and callable(self.pet.get_move_enabled):
            return bool(self.pet.get_move_enabled())
        return bool(getattr(self.pet.state, "move_enabled", True))

    def _on_pet_move_enabled_changed(self, enabled: bool):
        """接收移动开关变化并更新设置页按钮文案。"""
        if not hasattr(self, "stop_move_btn"):
            return
        self.stop_move_btn.setText("恢复移动" if not bool(enabled) else "停止移动")

    def _on_pet_follow_changed(self, follow_enabled: bool):
        """接收桌宠跟随状态变化并更新设置页控件。"""
        self.follow_checkbox.blockSignals(True)
        self.follow_checkbox.setChecked(bool(follow_enabled))
        self.follow_checkbox.blockSignals(False)

    def _on_pet_scale_changed(self, scale_value: float):
        """接收桌宠缩放变化并更新设置页控件。"""
        min_slider = int(round(SCALE_MIN * 10))
        max_slider = int(round(SCALE_MAX * 10))
        slider_value = int(round(float(scale_value) * 10))
        slider_value = max(min_slider, min(max_slider, slider_value))

        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(slider_value)
        self.scale_slider.blockSignals(False)
        self.scale_value_label.setText(f"{slider_value / 10:.1f}x")

    def _on_pet_autostart_changed(self, enabled: bool):
        """接收桌宠开机自启变化并更新设置页控件。"""
        self.autostart_checkbox.blockSignals(True)
        self.autostart_checkbox.setChecked(bool(enabled))
        self.autostart_checkbox.blockSignals(False)

    def _on_pet_display_mode_changed(self, mode: str):
        """接收显示模式变化并更新设置页下拉。"""
        index = self.display_mode_combo.findData(mode)
        if index < 0:
            index = self.display_mode_combo.findData(DISPLAY_MODE_ALWAYS_ON_TOP)
            if index < 0:
                index = 0

        self.display_mode_combo.blockSignals(True)
        self.display_mode_combo.setCurrentIndex(index)
        self.display_mode_combo.blockSignals(False)

    def _on_pet_instance_count_changed(self, count: int):
        """接收实例数量变化并更新设置页数值控件。"""
        try:
            value = int(count)
        except (TypeError, ValueError):
            value = INSTANCE_COUNT_MIN
        value = max(INSTANCE_COUNT_MIN, min(INSTANCE_COUNT_MAX, value))

        self.instance_count_spin.blockSignals(True)
        self.instance_count_spin.setValue(value)
        self.instance_count_spin.blockSignals(False)

    def _on_pet_opacity_changed(self, opacity: int):
        """接收透明度变化并更新设置页滑块。"""
        try:
            value = int(opacity)
        except (TypeError, ValueError):
            value = OPACITY_DEFAULT_PERCENT
        value = max(OPACITY_PERCENT_MIN, min(OPACITY_PERCENT_MAX, value))

        self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(value)
        self.opacity_slider.blockSignals(False)
        self.opacity_value_label.setText(f"{value}%")

    def _build_settings_page(self) -> QWidget:
        """构建设置页。包含所有右键菜单可配置项。"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(0)

        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setObjectName("SettingsScrollArea")
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        settings_content = QWidget()
        settings_content.setObjectName("SettingsPageContent")
        layout = QVBoxLayout(settings_content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("设置")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setVerticalSpacing(12)
        form_layout.setHorizontalSpacing(16)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.stop_move_btn = QPushButton("停止移动")
        self.stop_move_btn.setMinimumWidth(180)
        self.stop_move_btn.clicked.connect(self._on_toggle_move_clicked)
        form_layout.addRow("移动控制", self.stop_move_btn)

        self.move_scope_hint = QLabel("说明：此处“停止/恢复移动”会作用于全部实例；右键菜单仅作用于当前实例。")
        self.move_scope_hint.setWordWrap(True)
        self.move_scope_hint.setObjectName("FormHint")
        form_layout.addRow("", self.move_scope_hint)
        form_layout.addRow(self._create_form_separator())

        self.follow_checkbox = QCheckBox("启用跟随鼠标")
        self.follow_checkbox.setChecked(self.pet.state.follow_mouse)
        self.follow_checkbox.toggled.connect(self._on_follow_toggled)
        form_layout.addRow("跟随鼠标", self.follow_checkbox)
        form_layout.addRow(self._create_form_separator())

        scale_slider_row = QWidget()
        scale_slider_layout = QHBoxLayout(scale_slider_row)
        scale_slider_layout.setContentsMargins(0, 0, 0, 0)
        scale_slider_layout.setSpacing(8)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setMinimum(int(round(SCALE_MIN * 10)))
        self.scale_slider.setMaximum(int(round(SCALE_MAX * 10)))
        self.scale_slider.setSingleStep(1)
        self.scale_slider.setPageStep(1)
        self.scale_slider.setValue(int(round(self.pet.scale_factor * 10)))
        self.scale_slider.valueChanged.connect(self._on_scale_slider_changed)

        self.scale_value_label = QLabel(f"{self.scale_slider.value() / 10:.1f}x")
        self.scale_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.scale_value_label.setMinimumWidth(44)

        scale_slider_layout.addWidget(self.scale_slider, stretch=1)
        scale_slider_layout.addWidget(self.scale_value_label, stretch=0)
        form_layout.addRow("缩放比例", scale_slider_row)
        form_layout.addRow(self._create_form_separator())

        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItem("始终置顶", userData=DISPLAY_MODE_ALWAYS_ON_TOP)
        self.display_mode_combo.addItem("其他应用全屏时隐藏", userData=DISPLAY_MODE_FULLSCREEN_HIDE)
        self.display_mode_combo.addItem("仅在桌面显示", userData=DISPLAY_MODE_DESKTOP_ONLY)
        self.display_mode_combo.installEventFilter(self)
        self.display_mode_combo.currentIndexChanged.connect(self._on_display_mode_combo_changed)
        form_layout.addRow("显示优先级", self.display_mode_combo)
        form_layout.addRow(self._create_form_separator())

        self.instance_count_spin = QSpinBox()
        self.instance_count_spin.setRange(INSTANCE_COUNT_MIN, INSTANCE_COUNT_MAX)
        self.instance_count_spin.setSingleStep(1)
        self.instance_count_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.instance_count_spin.setAccelerated(True)
        self.instance_count_spin.setKeyboardTracking(False)
        self.instance_count_spin.installEventFilter(self)
        self.instance_count_spin.setValue(self._resolve_pet_instance_count())
        self.instance_count_spin.valueChanged.connect(self._on_instance_count_spin_changed)

        instance_count_row = QWidget()
        instance_count_layout = QHBoxLayout(instance_count_row)
        instance_count_layout.setContentsMargins(0, 0, 0, 0)
        instance_count_layout.setSpacing(6)

        self.instance_count_down_btn = QPushButton("▼")
        self.instance_count_down_btn.setObjectName("SpinArrowButton")
        self.instance_count_down_btn.setFixedWidth(40)
        self.instance_count_down_btn.clicked.connect(self._on_instance_count_decrease)

        self.instance_count_up_btn = QPushButton("▲")
        self.instance_count_up_btn.setObjectName("SpinArrowButton")
        self.instance_count_up_btn.setFixedWidth(40)
        self.instance_count_up_btn.clicked.connect(self._on_instance_count_increase)

        instance_count_layout.addWidget(self.instance_count_spin, stretch=1)
        instance_count_layout.addWidget(self.instance_count_up_btn, stretch=0)
        instance_count_layout.addWidget(self.instance_count_down_btn, stretch=0)

        form_layout.addRow("多开数量", instance_count_row)
        form_layout.addRow(self._create_form_separator())

        opacity_row = QWidget()
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(8)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(OPACITY_PERCENT_MIN, OPACITY_PERCENT_MAX)
        self.opacity_slider.setSingleStep(1)
        self.opacity_slider.setPageStep(1)
        self.opacity_slider.setValue(self._resolve_pet_opacity_percent())
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)

        self.opacity_value_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.opacity_value_label.setMinimumWidth(44)

        opacity_layout.addWidget(self.opacity_slider, stretch=1)
        opacity_layout.addWidget(self.opacity_value_label, stretch=0)
        form_layout.addRow("透明度", opacity_row)
        form_layout.addRow(self._create_form_separator())

        self.autostart_checkbox = QCheckBox("开机自启")
        self.autostart_checkbox.setChecked(self.pet.get_autostart_enabled())
        self.autostart_checkbox.toggled.connect(self._on_autostart_toggled)
        form_layout.addRow("系统启动", self.autostart_checkbox)
        form_layout.addRow(self._create_form_separator())

        self.close_behavior_combo = QComboBox()
        self.close_behavior_combo.addItem("每次询问", userData="ask")
        self.close_behavior_combo.addItem("直接退出应用", userData="quit")
        self.close_behavior_combo.addItem("最小化到系统托盘", userData="tray")
        behavior = self.settings_store.get_close_behavior()
        for i in range(self.close_behavior_combo.count()):
            if self.close_behavior_combo.itemData(i) == behavior:
                self.close_behavior_combo.setCurrentIndex(i)
                break
        self.close_behavior_combo.installEventFilter(self)
        self.close_behavior_combo.currentIndexChanged.connect(self._on_close_behavior_changed)
        form_layout.addRow("点击“×”行为", self.close_behavior_combo)
        form_layout.addRow(self._create_form_separator())

        self.quit_btn = QPushButton("退出应用程序")
        self.quit_btn.setMinimumWidth(180)
        self.quit_btn.clicked.connect(self.request_quit)
        form_layout.addRow("应用操作", self.quit_btn)

        layout.addWidget(form_card)
        layout.addStretch(1)

        self.settings_scroll_area.setWidget(settings_content)
        page_layout.addWidget(self.settings_scroll_area)
        return page

    def _create_form_separator(self) -> QWidget:
        """创建设置页分隔线。用于在功能模块间留出间隔。"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 14, 0, 14)
        wrapper_layout.setSpacing(0)

        line = QFrame()
        line.setObjectName("FormSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        wrapper_layout.addWidget(line)
        return wrapper

    def _build_music_page(self) -> QWidget:
        """构建音乐播放器页面。包含播放控制、进度条、播放模式、音量与播放列表。"""
        from .music_player import PLAY_MODE_LIST, PLAY_MODE_SINGLE, PLAY_MODE_RANDOM, MODE_ICONS

        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(12)

        title = QLabel("🎵 音乐")
        title.setObjectName("SectionTitle")
        page_layout.addWidget(title)

        # ---- 歌曲名 ----
        self.music_track_label = QLabel("（未播放）")
        self.music_track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.music_track_label.setObjectName("MusicTrackLabel")
        self.music_track_label.setWordWrap(True)
        page_layout.addWidget(self.music_track_label)

        # ---- 进度条 ----
        self.music_progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_progress_slider.setRange(0, 0)
        self.music_progress_slider.setSingleStep(1000)
        self.music_progress_slider.setObjectName("MusicProgressSlider")
        self._music_seeking = False
        self.music_progress_slider.sliderPressed.connect(lambda: setattr(self, "_music_seeking", True))
        self.music_progress_slider.sliderReleased.connect(self._on_music_seek)
        page_layout.addWidget(self.music_progress_slider)

        # 时间标签行
        time_row = QWidget()
        time_layout = QHBoxLayout(time_row)
        time_layout.setContentsMargins(0, 0, 0, 0)
        self.music_pos_label = QLabel("0:00")
        self.music_dur_label = QLabel("0:00")
        time_layout.addWidget(self.music_pos_label)
        time_layout.addStretch(1)
        time_layout.addWidget(self.music_dur_label)
        page_layout.addWidget(time_row)

        # ---- 主控按钮行 ----
        ctrl_row = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_row)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(10)

        self.music_prev_btn = QPushButton("◀◀ 上一首")
        self.music_play_btn = QPushButton("▶ 播放")
        self.music_play_btn.setObjectName("MusicPlayBtn")
        self.music_next_btn = QPushButton("▶▶ 下一首")

        self.music_prev_btn.clicked.connect(self._on_music_prev)
        self.music_play_btn.clicked.connect(self._on_music_toggle_pause)
        self.music_next_btn.clicked.connect(self._on_music_next)

        ctrl_layout.addWidget(self.music_prev_btn, stretch=1)
        ctrl_layout.addWidget(self.music_play_btn, stretch=2)
        ctrl_layout.addWidget(self.music_next_btn, stretch=1)
        page_layout.addWidget(ctrl_row)

        # ---- 播放模式按钮 ----
        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(8)

        self._music_mode_btns = {}
        for mode_key, mode_label in [
            (PLAY_MODE_LIST, f"{MODE_ICONS[PLAY_MODE_LIST]} 列表循环"),
            (PLAY_MODE_SINGLE, f"{MODE_ICONS[PLAY_MODE_SINGLE]} 单曲循环"),
            (PLAY_MODE_RANDOM, f"{MODE_ICONS[PLAY_MODE_RANDOM]} 随机播放"),
        ]:
            btn = QPushButton(mode_label)
            btn.setObjectName("MusicModeBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, m=mode_key: self._on_music_set_mode(m))
            self._music_mode_btns[mode_key] = btn
            mode_layout.addWidget(btn, stretch=1)
        page_layout.addWidget(mode_row)

        # ---- 音量行 ----
        vol_row = QWidget()
        vol_layout = QHBoxLayout(vol_row)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(8)

        vol_icon = QLabel("🔈")
        self.music_vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_vol_slider.setRange(0, 100)
        self.music_vol_slider.setValue(50)
        self.music_vol_slider.setObjectName("MusicVolSlider")
        self.music_vol_label = QLabel("50%")
        self.music_vol_label.setMinimumWidth(44)
        self.music_vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.music_vol_slider.valueChanged.connect(self._on_music_vol_changed)

        vol_layout.addWidget(vol_icon)
        vol_layout.addWidget(self.music_vol_slider, stretch=1)
        vol_layout.addWidget(self.music_vol_label)
        page_layout.addWidget(vol_row)

        # ---- 播放列表 ----
        list_title = QLabel("播放列表")
        list_title.setObjectName("MusicListTitle")
        page_layout.addWidget(list_title)

        list_action_row = QWidget()
        list_action_layout = QHBoxLayout(list_action_row)
        list_action_layout.setContentsMargins(0, 0, 0, 0)
        list_action_layout.setSpacing(8)

        self.music_add_btn = QPushButton("加入本地歌曲")
        self.music_add_btn.setObjectName("MusicListActionBtn")
        self.music_add_btn.clicked.connect(self._on_music_add_local)

        self.music_remove_btn = QPushButton("删除列表歌曲")
        self.music_remove_btn.setObjectName("MusicListActionBtn")
        self.music_remove_btn.clicked.connect(self._on_music_remove_selected)

        list_action_layout.addWidget(self.music_add_btn, stretch=1)
        list_action_layout.addWidget(self.music_remove_btn, stretch=1)
        page_layout.addWidget(list_action_row)

        self.music_list_widget = QListWidget()
        self.music_list_widget.setObjectName("MusicListWidget")
        self.music_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.music_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.music_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.music_list_widget.viewport().installEventFilter(self)
        self.music_list_widget.itemClicked.connect(self._on_music_list_item_clicked)
        self.music_list_widget.model().rowsMoved.connect(self._on_music_list_rows_moved)
        self.music_list_widget.customContextMenuRequested.connect(self._on_music_list_context_menu)
        page_layout.addWidget(self.music_list_widget, stretch=1)

        self._music_delete_mode = False

        self.music_confirm_delete_btn = QPushButton("确认删除")
        self.music_confirm_delete_btn.setObjectName("MusicListActionBtn")
        self.music_confirm_delete_btn.clicked.connect(self._on_music_confirm_batch_remove)
        self.music_confirm_delete_btn.hide()

        self.music_cancel_delete_btn = QPushButton("取消删除")
        self.music_cancel_delete_btn.setObjectName("MusicListActionBtn")
        self.music_cancel_delete_btn.clicked.connect(self._on_music_cancel_batch_remove)
        self.music_cancel_delete_btn.hide()

        self.music_delete_mode_hint = QLabel("已进入删除模式，请勾选歌曲后确认")
        self.music_delete_mode_hint.setObjectName("MusicDeleteModeHint")
        self.music_delete_mode_hint.hide()

        list_action_layout.addWidget(self.music_confirm_delete_btn, stretch=1)
        list_action_layout.addWidget(self.music_cancel_delete_btn, stretch=1)
        page_layout.addWidget(self.music_delete_mode_hint)

        # 初始化列表与状态
        self._music_refresh_playlist()
        if self.music_player is not None:
            self._sync_music_ui_from_player()

        return page

    def _build_about_page(self) -> QWidget:
        """构建关于页。中心显示 648x648 的 ameath.gif。"""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(0)

        self.about_scroll_area = QScrollArea()
        self.about_scroll_area.setObjectName("AboutScrollArea")
        self.about_scroll_area.setWidgetResizable(True)
        self.about_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.about_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.about_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.about_page = QWidget()
        self.about_page.setObjectName("AboutPageContent")
        layout = QVBoxLayout(self.about_page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("关于")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.gif_wrap = QFrame()
        self.gif_wrap.setObjectName("Card")
        gif_layout = QVBoxLayout(self.gif_wrap)
        gif_layout.setContentsMargins(16, 16, 16, 16)

        self.about_gif_label = QLabel()
        self.about_gif_label.setMinimumSize(96, 96)
        self.about_gif_label.setMaximumSize(648, 648)
        self.about_gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_gif_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.about_movie = QMovie(str(ABOUT_GIF_PATH))
        self.about_movie.setParent(self)
        self.about_movie.setCacheMode(QMovie.CacheMode.CacheNone)
        self.about_movie.setScaledSize(QSize(648, 648))
        self.about_gif_label.setMovie(self.about_movie)
        self.about_movie.start()

        gif_layout.addWidget(self.about_gif_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.gif_wrap, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        text_card = QFrame()
        text_card.setObjectName("Card")
        text_layout = QVBoxLayout(text_card)
        text_layout.setContentsMargins(16, 16, 16, 16)

        self.about_text_edit = QTextEdit()
        self.about_text_edit.setObjectName("AboutText")
        self.about_text_edit.setReadOnly(True)
        self.about_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.about_text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.about_text_edit.setHtml(
            "<div style='text-align:center; line-height:1.6;'>"
            + self.about_text_content.replace("\n", "<br>")
            + "</div>"
        )
        self.about_text_edit.setMinimumHeight(180)
        text_layout.addWidget(self.about_text_edit)

        layout.addWidget(text_card)
        layout.addStretch(1)
        self.about_scroll_area.setWidget(self.about_page)
        page_layout.addWidget(self.about_scroll_area)
        return page

    def _apply_theme(self):
        """应用浅粉白主基调样式。"""
        check_icon_path = (ROOT_DIR / "gifs" / "check_white.svg").as_posix()
        style = """
            QMainWindow {
                background: #fff8fb;
            }
            QScrollArea#SettingsScrollArea, QScrollArea#AboutScrollArea {
                background: #fff8fb;
                border: none;
            }
            QWidget#SettingsPageContent, QWidget#AboutPageContent {
                background: #fff8fb;
            }
            QFrame#NavCard, QFrame#Card {
                background: #fffdfd;
                border: 1px solid #f5d9e6;
                border-radius: 12px;
            }
            QFrame#FormSeparator {
                background: #f3d8e4;
                max-height: 1px;
                min-height: 1px;
                border: none;
            }
            QLabel {
                color: #6e4b5a;
                font-size: 16px;
            }
            QLabel#SectionTitle {
                font-size: 26px;
                font-weight: 700;
                color: #8e5f73;
            }
            QTextEdit#AboutText {
                font-size: 22px;
                line-height: 1.6;
                font-weight: 600;
                color: #7a4b60;
                background: #ffffff;
                border: 1px solid #f0c7d8;
                border-radius: 8px;
                padding: 8px;
            }
            QTextEdit#AboutText QScrollBar:vertical {
                background: #fff4f9;
                width: 12px;
                margin: 4px 2px 4px 2px;
                border-radius: 6px;
            }
            QTextEdit#AboutText QScrollBar::handle:vertical {
                background: #f6cde0;
                min-height: 28px;
                border-radius: 6px;
                border: 1px solid #efbdd5;
            }
            QTextEdit#AboutText QScrollBar::handle:vertical:hover {
                background: #efb8d2;
            }
            QTextEdit#AboutText QScrollBar::add-line:vertical,
            QTextEdit#AboutText QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }
            QTextEdit#AboutText QScrollBar::add-page:vertical,
            QTextEdit#AboutText QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollArea#SettingsScrollArea QScrollBar:vertical,
            QScrollArea#AboutScrollArea QScrollBar:vertical {
                background: #fff4f9;
                width: 12px;
                margin: 4px 2px 4px 2px;
                border-radius: 6px;
            }
            QScrollArea#SettingsScrollArea QScrollBar::handle:vertical,
            QScrollArea#AboutScrollArea QScrollBar::handle:vertical {
                background: #f6cde0;
                min-height: 28px;
                border-radius: 6px;
                border: 1px solid #efbdd5;
            }
            QScrollArea#SettingsScrollArea QScrollBar::handle:vertical:hover,
            QScrollArea#AboutScrollArea QScrollBar::handle:vertical:hover {
                background: #efb8d2;
            }
            QScrollArea#SettingsScrollArea QScrollBar::add-line:vertical,
            QScrollArea#SettingsScrollArea QScrollBar::sub-line:vertical,
            QScrollArea#AboutScrollArea QScrollBar::add-line:vertical,
            QScrollArea#AboutScrollArea QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
                border: none;
            }
            QScrollArea#SettingsScrollArea QScrollBar::add-page:vertical,
            QScrollArea#SettingsScrollArea QScrollBar::sub-page:vertical,
            QScrollArea#AboutScrollArea QScrollBar::add-page:vertical,
            QScrollArea#AboutScrollArea QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QPushButton {
                background: #ffeaf3;
                border: 1px solid #f3c6da;
                border-radius: 10px;
                padding: 10px 14px;
                min-height: 44px;
                color: #7a4b60;
                font-weight: 600;
                font-size: 16px;
            }
            QPushButton#NavButton {
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#SpinArrowButton {
                font-size: 18px;
                font-weight: 700;
                min-height: 48px;
                padding: 6px 0px;
            }
            QPushButton:hover {
                background: #ffdfeF;
            }
            QComboBox, QTextEdit {
                background: #ffffff;
                border: 1px solid #f0c7d8;
                border-radius: 8px;
                padding: 8px;
                color: #6d4657;
                font-size: 16px;
            }
            QSpinBox {
                background: #ffffff;
                border: 1px solid #f0c7d8;
                border-radius: 8px;
                padding: 8px;
                color: #6d4657;
                font-size: 16px;
                min-height: 24px;
            }
            QCheckBox {
                color: #6d4657;
                font-size: 16px;
            }
            QLabel#MusicTrackLabel {
                font-size: 18px;
                font-weight: 600;
                color: #7a4b60;
                padding: 4px 0;
            }
            QLabel#MusicListTitle {
                font-size: 15px;
                font-weight: 600;
                color: #8e6070;
            }
            QSlider#MusicProgressSlider::groove:horizontal,
            QSlider#MusicVolSlider::groove:horizontal {
                height: 6px;
                background: #f3d8e4;
                border-radius: 3px;
            }
            QSlider#MusicProgressSlider::handle:horizontal,
            QSlider#MusicVolSlider::handle:horizontal {
                background: #e08ab0;
                border: 1px solid #d070a0;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider#MusicProgressSlider::sub-page:horizontal,
            QSlider#MusicVolSlider::sub-page:horizontal {
                background: #e8a0c0;
                border-radius: 3px;
            }
            QPushButton#MusicPlayBtn {
                font-size: 18px;
                font-weight: 700;
                background: #ffd6ec;
            }
            QPushButton#MusicModeBtn {
                font-size: 15px;
                min-height: 36px;
            }
            QPushButton#MusicModeBtn:checked {
                background: #f9c0d8;
                border: 1.5px solid #e080b0;
                color: #8e3060;
            }
            QPushButton#MusicListActionBtn {
                min-height: 36px;
                font-size: 15px;
            }
            QListWidget#MusicListWidget {
                background: #fff8fb;
                border: 1px solid #f0c7d8;
                border-radius: 8px;
                font-size: 15px;
                color: #6d4657;
            }
            QListWidget#MusicListWidget::item:selected {
                background: #ffd6ec;
                color: #7a2550;
            }
            QListWidget#MusicListWidget::item:hover {
                background: #fff0f7;
            }
            QListWidget#MusicListWidget::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #6aa5ff;
                background: #d7e8ff;
            }
            QListWidget#MusicListWidget::indicator:checked {
                border: 1px solid #2f75ff;
                background: #3b82f6;
                image: url(__CHECK_ICON__);
            }
            QLabel#MusicDeleteModeHint {
                color: #1d4ed8;
                font-size: 14px;
                font-weight: 600;
                background: #dbeafe;
                border: 1px solid #93c5fd;
                border-radius: 8px;
                padding: 8px 10px;
            }
            """
        self.setStyleSheet(style.replace("__CHECK_ICON__", check_icon_path))

    def _on_follow_toggled(self, checked: bool):
        """设置页跟随开关回调。"""
        if self.pet.state.follow_mouse != checked:
            self.pet.on_toggle_follow()

    def _on_scale_slider_changed(self, slider_value: int):
        """设置页缩放滑块变化回调。"""
        scale = float(slider_value) / 10
        self.scale_value_label.setText(f"{scale:.1f}x")
        self.pet.on_set_scale(scale)

    def _on_autostart_toggled(self, checked: bool):
        """设置页开机自启开关回调。"""
        self.pet.on_toggle_autostart(checked)

    def _on_toggle_move_clicked(self):
        """设置页移动开关按钮回调。作用于全部实例。"""
        if hasattr(self.pet, "on_toggle_move_all") and callable(self.pet.on_toggle_move_all):
            self.pet.on_toggle_move_all()
            return

        if hasattr(self.pet, "on_stop_move") and callable(self.pet.on_stop_move):
            self.pet.on_stop_move()

    def _on_display_mode_combo_changed(self):
        """设置页显示模式下拉变化回调。"""
        mode = self.display_mode_combo.currentData()
        if isinstance(mode, str):
            self.pet.on_set_display_mode(mode)

    def _on_instance_count_spin_changed(self, value: int):
        """设置页实例数量变化回调。"""
        self.pet.on_set_instance_count(value)

    def _on_instance_count_decrease(self):
        """多开数量减少按钮回调。"""
        self.instance_count_spin.stepDown()

    def _on_instance_count_increase(self):
        """多开数量增加按钮回调。"""
        self.instance_count_spin.stepUp()

    def _on_opacity_slider_changed(self, value: int):
        """设置页透明度滑块变化回调。"""
        self.opacity_value_label.setText(f"{int(value)}%")
        self.pet.on_set_opacity_percent(int(value))

    def _on_close_behavior_changed(self):
        """设置页关闭行为配置回调。"""
        behavior = self.close_behavior_combo.currentData()
        if isinstance(behavior, str):
            self.settings_store.set_close_behavior(behavior)

    def eventFilter(self, watched, event):
        """过滤指定下拉框的滚轮事件，避免滚轮误改值。"""
        if (
            hasattr(self, "music_list_widget")
            and watched is self.music_list_widget.viewport()
            and self._music_delete_mode
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            item = self.music_list_widget.itemAt(event.pos())
            if item is not None:
                item.setCheckState(
                    Qt.CheckState.Unchecked
                    if item.checkState() == Qt.CheckState.Checked
                    else Qt.CheckState.Checked
                )
            return True

        if event.type() == QEvent.Type.Wheel and watched in {
            self.display_mode_combo,
            self.close_behavior_combo,
            self.instance_count_spin,
        }:
            event.ignore()
            return True
        return super().eventFilter(watched, event)

    def show_window(self):
        """显示并激活主界面。"""
        self.show()
        self.raise_()
        self.activateWindow()
        self._update_about_gif_size()

    def _on_page_changed(self, index: int):
        """页面切换回调。在关于页显示时同步刷新 GIF 大小。"""
        if index == 2:
            self._update_about_gif_size()

    def _update_about_gif_size(self):
        """根据当前界面尺寸更新关于页 GIF 显示大小。全屏时上限 648x648。"""
        if not hasattr(self, "about_gif_label"):
            return

        if not hasattr(self, "about_movie") or self.about_movie is None:
            return

        if self.pages.currentIndex() != 2:
            return

        if hasattr(self, "about_scroll_area"):
            page_rect = self.about_scroll_area.viewport().contentsRect()
        else:
            page_rect = self.about_page.contentsRect()
        available_width = max(96, page_rect.width() - 64)
        available_height = max(96, int(page_rect.height() * 0.55))

        target_size = min(648, available_width, available_height)
        target_size = max(96, target_size)

        self.about_gif_label.setFixedSize(target_size, target_size)
        self.about_movie.setScaledSize(QSize(target_size, target_size))
        self.about_gif_label.update()

    def set_tray_controller(self, tray_controller):
        """设置托盘控制器引用。用于最小化到托盘时通知。"""
        self.tray_controller = tray_controller

    def prepare_for_exit(self):
        """准备退出。标记当前窗口允许直接关闭。"""
        self._is_exiting = True

        if hasattr(self, "music_list_widget") and self.music_list_widget is not None:
            try:
                self.music_list_widget.viewport().removeEventFilter(self)
            except Exception:
                pass
            try:
                self.music_list_widget.customContextMenuRequested.disconnect(self._on_music_list_context_menu)
            except Exception:
                pass
            try:
                for i in range(self.music_list_widget.count()):
                    item = self.music_list_widget.item(i)
                    row_widget = self.music_list_widget.itemWidget(item)
                    if row_widget is not None:
                        row_widget.deleteLater()
            except Exception:
                pass

        if self.music_player is not None:
            try:
                self.music_player.track_changed.disconnect(self._on_music_track_changed)
            except Exception:
                pass
            try:
                self.music_player.state_changed.disconnect(self._on_music_state_changed)
            except Exception:
                pass
            try:
                self.music_player.playlist_reordered.disconnect(self._on_music_playlist_reordered)
            except Exception:
                pass
            try:
                self.music_player.volume_changed.disconnect(self._on_music_volume_changed)
            except Exception:
                pass
            try:
                self.music_player.mode_changed.disconnect(self._on_music_mode_changed)
            except Exception:
                pass
            try:
                self.music_player.duration_changed.disconnect(self._on_music_duration_changed)
            except Exception:
                pass
            try:
                self.music_player.position_changed.disconnect(self._on_music_position_changed)
            except Exception:
                pass

        if hasattr(self, "music_list_widget") and self.music_list_widget is not None:
            try:
                self.music_list_widget.itemClicked.disconnect(self._on_music_list_item_clicked)
            except Exception:
                pass
            try:
                self.music_list_widget.model().rowsMoved.disconnect(self._on_music_list_rows_moved)
            except Exception:
                pass

        if hasattr(self, "about_movie") and self.about_movie is not None:
            self.about_movie.stop()
            self.about_movie.deleteLater()
            self.about_movie = None

    def closeEvent(self, event: QCloseEvent):
        """拦截关闭事件，应用关闭策略。"""
        if self._is_exiting:
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
            self.request_quit()
            return

        event.ignore()

    def resizeEvent(self, event):
        """窗口尺寸变化时同步更新关于页 GIF 大小。"""
        super().resizeEvent(event)
        self._update_about_gif_size()
    # ---------------------------------------------------------------
    # 音乐播放器辅助工具
    # ---------------------------------------------------------------

    @staticmethod
    def _fmt_ms(ms: int) -> str:
        """将毫秒格式化为 m:ss 字符串。"""
        try:
            s = max(0, int(ms) // 1000)
        except (TypeError, ValueError):
            return "0:00"
        return f"{s // 60}:{s % 60:02d}"

    def _music_refresh_playlist(self):
        """刷新播放列表控件内容。"""
        if not hasattr(self, "music_list_widget"):
            return

        # 先释放旧 item widget，避免残留控件对象堆积。
        for i in range(self.music_list_widget.count()):
            item = self.music_list_widget.item(i)
            row_widget = self.music_list_widget.itemWidget(item)
            if row_widget is not None:
                row_widget.deleteLater()

        self.music_list_widget.blockSignals(True)
        self.music_list_widget.clear()
        if self.music_player is not None:
            for i, track in enumerate(self.music_player.playlist):
                item = QListWidgetItem(f"{i + 1}. {track.stem}")
                if self._music_delete_mode:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                self.music_list_widget.addItem(item)
            self._highlight_current_track()
        self.music_list_widget.blockSignals(False)

    def _highlight_current_track(self):
        """高亮当前播放歌曲行。"""
        if self.music_player is None or not hasattr(self, "music_list_widget"):
            return
        idx = self.music_player.current_index
        for i in range(self.music_list_widget.count()):
            item = self.music_list_widget.item(i)
            font = item.font()
            font.setBold(i == idx)
            item.setFont(font)

    def _sync_music_ui_from_player(self):
        """将播放器当前完整状态同步到 UI。"""
        if self.music_player is None:
            return
        from .music_player import PLAY_MODE_LIST
        # 歌曲名
        self.music_track_label.setText(self.music_player.current_track_name)
        # 播放/暂停按钮
        self.music_play_btn.setText("⏸ 暂停" if self.music_player.is_playing else "▶ 播放")
        # 模式按钮
        for mode_key, btn in self._music_mode_btns.items():
            btn.setChecked(self.music_player.play_mode == mode_key)
        # 音量
        vol_val = int(self.music_player.volume * 100)
        self.music_vol_slider.blockSignals(True)
        self.music_vol_slider.setValue(vol_val)
        self.music_vol_slider.blockSignals(False)
        self.music_vol_label.setText(f"{vol_val}%")
        # 时长
        dur = self.music_player.duration
        self.music_progress_slider.setRange(0, max(0, dur))
        self.music_dur_label.setText(self._fmt_ms(dur))
        # 位置
        pos = self.music_player.position
        if not self._music_seeking:
            self.music_progress_slider.blockSignals(True)
            self.music_progress_slider.setValue(pos)
            self.music_progress_slider.blockSignals(False)
        self.music_pos_label.setText(self._fmt_ms(pos))
        # 高亮
        self._highlight_current_track()

    # ---------------------------------------------------------------
    # 音乐播放器 — 控件回调
    # ---------------------------------------------------------------

    def _on_music_prev(self):
        if self.music_player is not None:
            self.music_player.prev()

    def _on_music_toggle_pause(self):
        if self.music_player is not None:
            self.music_player.toggle_pause()

    def _on_music_next(self):
        if self.music_player is not None:
            self.music_player.next()

    def _on_music_set_mode(self, mode: str):
        if self.music_player is not None:
            self.music_player.set_mode(mode)

    def _on_music_vol_changed(self, value: int):
        self.music_vol_label.setText(f"{value}%")
        if self.music_player is not None:
            self.music_player.set_volume(value / 100.0)

    def _on_music_seek(self):
        self._music_seeking = False
        if self.music_player is not None:
            self.music_player.seek(self.music_progress_slider.value())

    def _on_music_list_context_menu(self, pos):
        """播放列表右键菜单。提供歌曲重命名操作。"""
        if self.music_player is None:
            return
        if self._music_delete_mode:
            return

        item = self.music_list_widget.itemAt(pos)
        if item is None:
            return

        row = self.music_list_widget.row(item)
        if row < 0 or row >= len(self.music_player.playlist):
            return

        menu = QMenu(self.music_list_widget)
        rename_action = menu.addAction("重命名歌曲")
        action = menu.exec(self.music_list_widget.viewport().mapToGlobal(pos))
        menu.deleteLater()

        if action is rename_action:
            self._on_music_rename_track(row)

    def _on_music_rename_track(self, row: int):
        """重命名指定行歌曲，确认后同步修改 music 目录文件名。"""
        if self.music_player is None:
            return
        if not (0 <= row < len(self.music_player.playlist)):
            return

        old_stem = self.music_player.playlist[row].stem
        new_name, ok = QInputDialog.getText(self, "重命名歌曲", "请输入新名称（不含扩展名）：", text=old_stem)
        if not ok:
            return

        new_name = str(new_name).strip()
        if not new_name:
            QMessageBox.warning(self, "提示", "新名称不能为空")
            return

        if new_name == old_stem:
            return

        answer = QMessageBox.question(
            self,
            "确认重命名",
            f"确认将\n\n{old_stem}\n\n重命名为\n\n{new_name}\n\n并同步修改 music 目录中的文件名吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        ok_rename, msg = self.music_player.rename_track(row, new_name)
        if not ok_rename:
            QMessageBox.warning(self, "重命名失败", msg)
            return

        self._music_refresh_playlist()
        self._sync_music_ui_from_player()

    def _on_music_add_local(self):
        """从本地选择音频文件导入到 music/ 目录并加入播放列表。"""
        if self.music_player is None:
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择本地歌曲",
            "",
            "音频文件 (*.ogg *.mp3 *.wav *.flac *.m4a);;所有文件 (*.*)",
        )
        if not files:
            return

        success = 0
        failed_messages = []
        for path in files:
            ok, msg = self.music_player.add_track_from_file(path)
            if ok:
                success += 1
            else:
                failed_messages.append(f"{path}: {msg}")

        self._music_refresh_playlist()
        self._sync_music_ui_from_player()

        if failed_messages:
            QMessageBox.warning(
                self,
                "导入结果",
                f"成功导入 {success} 首，失败 {len(failed_messages)} 首。\n\n"
                + "\n".join(failed_messages[:3]),
            )

    def _on_music_remove_selected(self):
        """点击删除按钮后进入勾选模式，支持多选后统一确认删除。"""
        if self.music_player is None:
            return

        if self._music_delete_mode:
            return

        self._music_delete_mode = True
        self.music_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.music_remove_btn.hide()
        self.music_confirm_delete_btn.show()
        self.music_cancel_delete_btn.show()
        self.music_delete_mode_hint.show()
        self._music_refresh_playlist()

    def _on_music_cancel_batch_remove(self):
        """取消批量删除模式。"""
        self._music_delete_mode = False
        self.music_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.music_remove_btn.show()
        self.music_confirm_delete_btn.hide()
        self.music_cancel_delete_btn.hide()
        self.music_delete_mode_hint.hide()
        self._music_refresh_playlist()

    def _on_music_confirm_batch_remove(self):
        """批量确认删除已勾选歌曲。"""
        if self.music_player is None:
            return

        checked_rows = []
        for i in range(self.music_list_widget.count()):
            item = self.music_list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_rows.append(i)

        if not checked_rows:
            QMessageBox.information(self, "提示", "请先勾选要删除的歌曲")
            return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle("批量删除歌曲")
        dialog.setText(f"已勾选 {len(checked_rows)} 首歌曲，请选择删除方式：")
        dialog.setInformativeText("可仅从列表移除，或同时删除本地文件。")

        remove_only_btn = dialog.addButton("仅从列表移除", QMessageBox.ButtonRole.ActionRole)
        remove_and_delete_btn = dialog.addButton("从列表移除并删除本地文件", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(cancel_btn)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is cancel_btn:
            return

        delete_file = clicked is remove_and_delete_btn
        if clicked not in {remove_only_btn, remove_and_delete_btn}:
            return

        success_count = 0
        failed_msgs = []
        for row in sorted(checked_rows, reverse=True):
            ok, msg = self.music_player.remove_track(row, delete_file=delete_file)
            if ok:
                success_count += 1
            else:
                failed_msgs.append(msg)

        self._music_delete_mode = False
        self.music_list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.music_remove_btn.show()
        self.music_confirm_delete_btn.hide()
        self.music_cancel_delete_btn.hide()
        self.music_delete_mode_hint.hide()
        self._music_refresh_playlist()
        self._sync_music_ui_from_player()

        if failed_msgs:
            QMessageBox.warning(
                self,
                "删除结果",
                f"成功删除 {success_count} 首，失败 {len(failed_msgs)} 首。",
            )

    def _on_music_list_item_clicked(self, item: QListWidgetItem):
        if self.music_player is None:
            return
        if self._music_delete_mode:
            return
        row = self.music_list_widget.row(item)
        if row != self.music_player.current_index:
            self.music_player.play(row)
        else:
            self.music_player.toggle_pause()

    def _on_music_list_rows_moved(self, parent, src_start, src_end, dest_parent, dest_row):
        """拖拽排序完成后同步播放器内部列表顺序。"""
        if self.music_player is None:
            return
        if self._music_delete_mode:
            return
        to_index = dest_row if dest_row <= src_start else dest_row - 1
        self.music_player.move_track(src_start, to_index)
        # 刷新编号显示
        for i in range(self.music_list_widget.count()):
            item = self.music_list_widget.item(i)
            if self.music_player and i < len(self.music_player.playlist):
                item.setText(f"{i + 1}. {self.music_player.playlist[i].stem}")
        self._highlight_current_track()

    # ---------------------------------------------------------------
    # 音乐播放器 — Signal 回调（来自 MusicPlayer）
    # ---------------------------------------------------------------

    def _on_music_track_changed(self, index: int):
        if self.music_player is None:
            return
        self.music_track_label.setText(self.music_player.current_track_name)
        self._highlight_current_track()

    def _on_music_state_changed(self, state: str):
        if not hasattr(self, "music_play_btn"):
            return
        self.music_play_btn.setText("⏸ 暂停" if state == "playing" else "▶ 播放")

    def _on_music_playlist_reordered(self):
        self._music_refresh_playlist()

    def _on_music_volume_changed(self, volume: float):
        if not hasattr(self, "music_vol_slider"):
            return
        val = int(volume * 100)
        self.music_vol_slider.blockSignals(True)
        self.music_vol_slider.setValue(val)
        self.music_vol_slider.blockSignals(False)
        self.music_vol_label.setText(f"{val}%")

    def _on_music_mode_changed(self, mode: str):
        if not hasattr(self, "_music_mode_btns"):
            return
        for mode_key, btn in self._music_mode_btns.items():
            btn.setChecked(mode_key == mode)

    def _on_music_duration_changed(self, duration: int):
        if not hasattr(self, "music_progress_slider"):
            return
        self.music_progress_slider.setRange(0, max(0, duration))
        self.music_dur_label.setText(self._fmt_ms(duration))

    def _on_music_position_changed(self, position: int):
        if not hasattr(self, "music_progress_slider") or self._music_seeking:
            return
        self.music_progress_slider.blockSignals(True)
        self.music_progress_slider.setValue(position)
        self.music_progress_slider.blockSignals(False)
        self.music_pos_label.setText(self._fmt_ms(position))