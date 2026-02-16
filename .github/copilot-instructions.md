# Ameath Desktop Pet Instructions

## 目录与文件功能索引

### 根目录
- `main.py`：应用入口，负责初始化设置存储、实例管理器、桌宠窗口、前端窗口与系统托盘。
- `requirements.txt`：项目依赖列表（PySide6、PyInstaller）。
- `README.md`：用户使用说明、交互说明、打包说明与项目结构说明。

### `.github`
- `.github/copilot-instructions.md`：Copilot 工作指引与项目文件功能快速索引。

### `pet` 包
- `pet/__init__.py`：包级说明文件。
- `pet/config.py`：全局常量与资源路径配置（动画路径、显示模式、实例数量、透明度范围等）。
- `pet/animation.py`：GIF 播放、缩放与镜像绘制能力。
- `pet/state_machine.py`：桌宠核心状态机（拖拽、跟随、休息、移动）。
- `pet/movement.py`：桌宠移动控制（自动移动、跟随、边界检测、触边停顿）。
- `pet/input.py`：鼠标输入处理（左键拖拽、右键菜单、释放状态恢复）。
- `pet/idle.py`：随机休息调度与休息状态切换。
- `pet/menu.py`：右键菜单构建（移动/跟随/缩放/透明度/显示优先级/多开/关闭菜单）。
- `pet/autostart.py`：Windows 开机自启注册表读写。
- `pet/window.py`：单个桌宠窗口主类，负责动画调度、事件处理、菜单动作响应与本地应用设置。
- `pet/instance_manager.py`：多开实例管理与全局同步中心，负责实例增减、批量设置同步、显示策略轮询。
- `pet/app_window.py`：前端应用窗口（设置页、关于页），支持与右键设置实时双向同步。
- `pet/tray_controller.py`：系统托盘图标与托盘菜单控制（打开/退出/提示）。
- `pet/settings_store.py`：本地 JSON 设置持久化（关闭行为、显示优先级、多开数量、透明度）。
- `pet/close_policy.py`：点击关闭按钮时的策略弹窗与“记住选择”逻辑。

### `exe`
- `exe/build_exe.ps1`：EXE 打包脚本（PyInstaller）。
- `exe/README.md`：EXE 目录与打包产物说明。

### 资源目录
- `gifs/`：桌宠动画与图标资源（`move.gif`、`drag.gif`、`ameath.gif`、`idle*.gif`、`ameath.ico`）。

## 常见定位建议
- 修改桌宠行为优先看：`pet/window.py`、`pet/movement.py`、`pet/state_machine.py`。
- 修改右键菜单优先看：`pet/menu.py`、`pet/window.py`。
- 修改设置页与联动优先看：`pet/app_window.py`、`pet/instance_manager.py`、`pet/settings_store.py`。
- 修改启动流程与多开初始化优先看：`main.py`、`pet/instance_manager.py`。
