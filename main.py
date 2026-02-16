"""这是应用入口模块。负责初始化桌宠窗口、主界面与系统托盘。"""

import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pet.app_window import AppWindow
from pet.close_policy import ClosePolicyManager
from pet.config import APP_ICON_PATH
from pet.instance_manager import PetInstanceManager
from pet.settings_store import SettingsStore
from pet.tray_controller import TrayController
from pet.window import DesktopPet


def main():
    """启动应用主流程。统一拉起桌宠、主界面与托盘控制。"""
    # 先创建 Qt 应用对象。所有 QWidget 生命周期都依赖它。
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    # 初始化设置存储与关闭策略。
    settings_store = SettingsStore()
    close_policy = ClosePolicyManager(settings_store)

    # 准备退出防重入标志。
    is_quitting = False

    # 先声明变量，便于回调里统一访问。
    manager = None
    app_window = None
    tray_controller = None

    def create_pet():
        """创建并注册单个桌宠实例。"""
        nonlocal manager, tray_controller

        pet = DesktopPet(
            on_open_main=open_main_window,
            on_request_quit=request_quit,
            close_policy=close_policy,
            instance_manager=manager,
        )
        manager.register_pet(pet)

        if tray_controller is not None:
            pet.set_tray_controller(tray_controller)

        return pet

    def request_quit():
        """执行统一退出流程。包含防重入、资源清理和应用退出。"""
        nonlocal is_quitting, manager, app_window, tray_controller

        if is_quitting:
            return
        is_quitting = True

        if manager is not None:
            for pet in manager.pets:
                if hasattr(pet, "prepare_for_exit") and callable(pet.prepare_for_exit):
                    pet.prepare_for_exit()
                if hasattr(pet, "close") and callable(pet.close):
                    pet.close()

        if app_window is not None:
            if hasattr(app_window, "prepare_for_exit") and callable(app_window.prepare_for_exit):
                app_window.prepare_for_exit()

        if tray_controller is not None:
            tray_controller.hide()

        app.quit()

    def open_main_window():
        """显示并激活前端主界面。"""
        if app_window is None:
            return
        app_window.show_window()

    # 初始化多开管理器，并创建首个桌宠实例。
    manager = PetInstanceManager(settings_store=settings_store, request_quit=request_quit)
    manager.set_spawn_callback(create_pet)
    create_pet()

    # 初始化主界面实例。
    app_window = AppWindow(
        pet=manager,
        settings_store=settings_store,
        close_policy=close_policy,
        request_quit=request_quit,
        tray_controller=None,
    )

    # 初始化系统托盘并显示。
    tray_controller = TrayController(
        icon_path=APP_ICON_PATH,
        on_open=open_main_window,
        on_exit=request_quit,
    )
    tray_controller.show()

    # 注入托盘控制器。优先走方法注入，不存在时回退为属性注入。
    if not hasattr(app_window, "set_tray_controller") or not callable(getattr(app_window, "set_tray_controller")):
        setattr(
            app_window,
            "set_tray_controller",
            lambda controller: setattr(app_window, "tray_controller", controller),
        )

    for pet in manager.pets:
        if not hasattr(pet, "set_tray_controller") or not callable(getattr(pet, "set_tray_controller")):
            setattr(pet, "set_tray_controller", lambda controller, p=pet: setattr(p, "tray_controller", controller))
        pet.set_tray_controller(tray_controller)
    app_window.set_tray_controller(tray_controller)

    # 按配置补齐到目标实例数量。
    manager.on_set_instance_count(settings_store.get_instance_count())

    # 启动时同时展示桌宠窗口与主界面。
    app_window.show_window()

    # 最后进入事件循环。用户关闭窗口后才会返回。
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
