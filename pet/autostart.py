"""该模块控制 Windows 开机自启。通过当前用户 Run 注册表项实现。"""

import sys
from pathlib import Path

from .config import APP_AUTOSTART_NAME, ROOT_DIR


def _build_launch_command() -> str:
    """构造启动命令。兼容源码运行与打包运行两种场景。"""
    if getattr(sys, "frozen", False):
        # 打包模式直接启动可执行文件。入口由打包器固化。
        return f'"{Path(sys.executable).resolve()}"'
    # 源码模式启动 main.py。使用当前解释器执行脚本入口。
    main_py = (ROOT_DIR / "main.py").resolve()
    return f'"{Path(sys.executable).resolve()}" "{main_py}"'


def is_autostart_enabled() -> bool:
    """检测自启是否启用。读取当前用户 Run 键值。"""
    if not sys.platform.startswith("win"):
        # 非 Windows 直接返回。该实现依赖 Windows 注册表。
        return False

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            value, _ = winreg.QueryValueEx(key, APP_AUTOSTART_NAME)
            return bool(value)
    except OSError:
        return False


def set_autostart_enabled(enabled: bool):
    """设置自启开关。根据布尔值写入或删除 Run 键值。"""
    if not sys.platform.startswith("win"):
        return

    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            # 启用时写入键值。用户登录后系统会自动执行。
            winreg.SetValueEx(key, APP_AUTOSTART_NAME, 0, winreg.REG_SZ, _build_launch_command())
            return
        try:
            winreg.DeleteValue(key, APP_AUTOSTART_NAME)
        except OSError:
            pass
