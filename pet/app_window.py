"""该模块是前端主界面。包含设置页和关于页。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCloseEvent, QIcon, QMovie
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
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
    SCALE_MAX,
    SCALE_MIN,
)


class AppWindow(QMainWindow):
    """应用主界面窗口。负责设置与关于页面展示。"""

    def __init__(self, pet, settings_store, close_policy, request_quit, tray_controller=None):
        """初始化界面、样式和交互绑定。"""
        super().__init__()
        self.pet = pet
        self.settings_store = settings_store
        self.close_policy = close_policy
        self.request_quit = request_quit
        self.tray_controller = tray_controller
        self._is_exiting = False

        self.setWindowTitle("Ameath Desktop Pet")
        self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setMinimumSize(980, 720)

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
        icon_label.setPixmap(QIcon(str(APP_ICON_PATH)).pixmap(28, 28))
        nav_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.settings_btn = QPushButton("设置")
        self.about_btn = QPushButton("关于")
        self.settings_btn.setObjectName("NavButton")
        self.about_btn.setObjectName("NavButton")
        self.settings_btn.setFixedWidth(120)
        self.about_btn.setFixedWidth(120)

        self.settings_btn.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.about_btn.clicked.connect(lambda: self.pages.setCurrentIndex(1))

        nav_layout.addWidget(self.settings_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        nav_layout.addWidget(self.about_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        nav_layout.addStretch(1)

        self.pages = QStackedWidget()
        self.pages.currentChanged.connect(self._on_page_changed)
        self.pages.addWidget(self._build_settings_page())
        self.pages.addWidget(self._build_about_page())

        main_layout.addWidget(nav_card, stretch=0)
        main_layout.addWidget(self.pages, stretch=1)

    def _bind_pet_state_sync(self):
        """绑定桌宠状态信号，实现设置页控件实时同步。"""
        if hasattr(self.pet, "follow_changed"):
            self.pet.follow_changed.connect(self._on_pet_follow_changed)
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

        self._sync_controls_from_pet()

    def _sync_controls_from_pet(self):
        """将设置页控件与当前桌宠状态对齐。"""
        self._on_pet_follow_changed(self.pet.state.follow_mouse)
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
        layout = QVBoxLayout(page)
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

        self.stop_move_btn = QPushButton("停止移动")
        self.stop_move_btn.clicked.connect(lambda: self.pet.on_stop_move())
        form_layout.addRow("移动控制", self.stop_move_btn)
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
        self.display_mode_combo.currentIndexChanged.connect(self._on_display_mode_combo_changed)
        form_layout.addRow("显示优先级", self.display_mode_combo)
        form_layout.addRow(self._create_form_separator())

        self.instance_count_spin = QSpinBox()
        self.instance_count_spin.setRange(INSTANCE_COUNT_MIN, INSTANCE_COUNT_MAX)
        self.instance_count_spin.setSingleStep(1)
        self.instance_count_spin.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.instance_count_spin.setAccelerated(True)
        self.instance_count_spin.setKeyboardTracking(False)
        self.instance_count_spin.setValue(self._resolve_pet_instance_count())
        self.instance_count_spin.valueChanged.connect(self._on_instance_count_spin_changed)
        form_layout.addRow("多开数量", self.instance_count_spin)
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
        self.close_behavior_combo.currentIndexChanged.connect(self._on_close_behavior_changed)
        form_layout.addRow("点击“×”行为", self.close_behavior_combo)
        form_layout.addRow(self._create_form_separator())

        self.quit_btn = QPushButton("退出应用程序")
        self.quit_btn.clicked.connect(self.request_quit)
        form_layout.addRow("应用操作", self.quit_btn)

        layout.addWidget(form_card)
        layout.addStretch(1)
        return page

    def _create_form_separator(self) -> QWidget:
        """创建设置页分隔线。用于在功能模块间留出间隔。"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 8, 0, 8)
        wrapper_layout.setSpacing(0)

        line = QFrame()
        line.setObjectName("FormSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        wrapper_layout.addWidget(line)
        return wrapper

    def _build_about_page(self) -> QWidget:
        """构建关于页。中心显示 648x648 的 ameath.gif。"""
        self.about_page = QWidget()
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
        return self.about_page

    def _apply_theme(self):
        """应用浅粉白主基调样式。"""
        self.setStyleSheet(
            """
            QMainWindow {
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
            QPushButton {
                background: #ffeaf3;
                border: 1px solid #f3c6da;
                border-radius: 10px;
                padding: 10px 14px;
                color: #7a4b60;
                font-weight: 600;
                font-size: 16px;
            }
            QPushButton#NavButton {
                font-size: 18px;
                font-weight: 700;
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
                padding-right: 28px;
                color: #6d4657;
                font-size: 16px;
                min-height: 24px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 20px;
                border-left: 1px solid #f0c7d8;
                background: #fff3f8;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
                border-top-right-radius: 8px;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
                border-bottom-right-radius: 8px;
                border-top: 1px solid #f0c7d8;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #ffe6f1;
            }
            QSpinBox::up-arrow {
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid #b96f90;
            }
            QSpinBox::down-arrow {
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid #b96f90;
            }
            QCheckBox {
                color: #6d4657;
                font-size: 16px;
            }
            """
        )

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

    def _on_display_mode_combo_changed(self):
        """设置页显示模式下拉变化回调。"""
        mode = self.display_mode_combo.currentData()
        if isinstance(mode, str):
            self.pet.on_set_display_mode(mode)

    def _on_instance_count_spin_changed(self, value: int):
        """设置页实例数量变化回调。"""
        self.pet.on_set_instance_count(value)

    def _on_opacity_slider_changed(self, value: int):
        """设置页透明度滑块变化回调。"""
        self.opacity_value_label.setText(f"{int(value)}%")
        self.pet.on_set_opacity_percent(int(value))

    def _on_close_behavior_changed(self):
        """设置页关闭行为配置回调。"""
        behavior = self.close_behavior_combo.currentData()
        if isinstance(behavior, str):
            self.settings_store.set_close_behavior(behavior)

    def show_window(self):
        """显示并激活主界面。"""
        self.show()
        self.raise_()
        self.activateWindow()
        self._update_about_gif_size()

    def _on_page_changed(self, index: int):
        """页面切换回调。在关于页显示时同步刷新 GIF 大小。"""
        if index == 1:
            self._update_about_gif_size()

    def _update_about_gif_size(self):
        """根据当前界面尺寸更新关于页 GIF 显示大小。全屏时上限 648x648。"""
        if not hasattr(self, "about_gif_label"):
            return

        if not self.about_page.isVisible() and self.pages.currentIndex() != 1:
            return

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
