<div align="center">
  <h2 style="font-size: 4em;">Ameath Desktop Pet on Windows</h2>
</div>

<div align="center">
  <img src="gifs/ameath.gif" alt="ameath" width="648" height="648"/>
</div>

---

<div align="center">
  <h1>❤️❤️❤️ Made by jhy &amp; Codex &amp; Ameath ❤️❤️❤️</h1>
</div>

<div align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" />
  <img alt="PySide6" src="https://img.shields.io/badge/PySide6-Qt%20for%20Python-41CD52?logo=qt&logoColor=white" />
  <img alt="Windows" src="https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows&logoColor=white" />
</div>

## 运行

1. 克隆项目

```powershell
git clone https://github.com/sleepingjhy/Ameath-Desktop-Pet-on-Windows.git
cd Ameath-Desktop-Pet-on-Windows
```

2. 安装依赖（建议使用虚拟环境）

```powershell
pip install -r requirements.txt
```

3. 启动

```powershell
python main.py
```

---

## v1.2.0

### 🌐 新增多语言界面支持（中文 / English / 日本語 / 한국어 / Français）

- 为可视化界面新增 5 种语言选项：
  - 中文
  - English
  - 日本語
  - 한국어
  - Français
- 在以下位置新增 **语言** 选择项：
  - 应用前端的 **关于** 页面
  - 桌宠 **右键菜单**
- 语言列表使用对应语言自描述显示（例如：`中文`、`English`、`日本語`、`한국어`、`Français`）。
- 用户选择会写入本地设置，并在下次启动时自动恢复。

### 🎵 托盘菜单新增音乐控制

- 托盘右键菜单新增 **🎵 音乐** 子菜单，支持：
  - 显示当前歌曲（只读）
  - 上一首 / 播放·暂停 / 下一首
  - 播放模式切换（列表循环 / 单曲循环 / 随机播放）
- 托盘音乐菜单与主播放器状态实时同步。

---

## v1.1.0

### 🎵 音乐播放器

在右键菜单与应用前端界面中新增音乐播放功能，播放 `music/` 目录下的歌曲。

> 说明：仓库会保留 `music/` 目录结构，但默认不提交目录内音频文件；请自行放入本地音乐文件使用。

- 修复了若干内存泄露问题。
- 全面检查并修复了退出链路中的内存泄漏风险（菜单信号、播放器资源、定时器与列表控件清理）。

#### 右键菜单（简化控制）

- 右键任意桌宠实例 → **🎵 音乐** 子菜单：
  - 显示当前播放歌曲名（只读）
  - ◀◀ 上一首 / ▶/⏸ 播放·暂停 / ▶▶ 下一首
  - 播放模式切换（三选一互斥）：
    - 🔁 列表循环
    - 🔂 单曲循环
    - 🔀 随机播放
  - 音量滑条（仅调整本应用音量，不影响系统音量）

#### 应用前端界面（完整播放器）

- 左侧导航新增 **🎵 音乐** 标签页，包含：
  - 当前歌曲名 + 播放进度条（可拖拽跳转）
  - 主控按钮行：◀◀ 上一首 / ▶/⏸ 播放·暂停 / ▶▶ 下一首
  - 播放模式按钮（循环点击切换，按钮旁显示对应图标 🔁/🔂/🔀）
  - 音量横向滑条（0~100%）
  - 加入本地歌曲：可从本地选择音频文件并导入到 `music/` 目录
  - 右键重命名歌曲：在播放列表中右键歌曲可触发重命名，确认后会同步修改 `music/` 目录中的文件名
  - 删除列表歌曲（批量）：先点击“删除歌曲”进入勾选模式，再在每首歌右侧方框打勾，最后一次性确认删除多首
    - 删除确认支持两种方式：仅从列表移除 / 从列表移除并删除本地文件
    - 删除模式会显示提示“已进入删除模式，请勾选歌曲后确认”
    - 点击“删除列表歌曲”后会隐藏该按钮，确认或取消后自动恢复显示
  - 播放列表（显示所有 `music/` 目录中的歌曲）：
    - **单击/双击**跳播对应歌曲，当前播放行高亮
    - **拖拽**行项目可重新排序播放列表
    - 拖拽改序后列表滚动条位置保持不变，不会自动跳动
- 右键菜单与应用界面播放器状态实时双向同步（切歌/模式在两端均有反映）

### 🔵 右键菜单固定 + 实例描边

- 右键菜单**不再跟随桌宠移动**，弹出后位置固定。
- 右键某一桌宠实例时，该实例边缘出现 **天蓝色（`#00BFFF`）描边**，直观提示当前操作对象。
- 菜单关闭后描边立即消失。

---

## v1.0.0

### 交互

- 左键按住并拖动：显示 `drag.gif` 并拖动桌宠
- 右键桌宠：打开菜单（菜单位置固定，不随桌宠移动；被右键的实例显示天蓝色描边直至菜单关闭）
  - 打开应用界面（快速唤起前端主窗口）
  - 停止移动 / 恢复移动（仅作用于当前右键实例）
  - 跟随鼠标（开关）
  - 缩放比例（0.1x ~ 2.0x，步进 0.1）
  - 透明度（10% ~ 100%，步进 10%，右键列表）
  - 显示优先级（始终置顶 / 其他应用全屏时隐藏 / 仅在桌面显示）
  - 多开模式（设置桌宠数量 0~50，立即生效）
  - 开机自启（开关，Windows）
  - 关闭桌宠（二级菜单）
    - 仅关闭当前桌宠
    - 关闭_个桌宠（输入数量，非法值提示数量过少/数量过多）
    - 一键关闭所有桌宠并退出

### 动画规则

- 向右移动：`move.gif`
- 向左移动：`move.gif` 镜像
- 休息动画：随机播放 `ameath.gif`、`idle1.gif`、`idle2.gif`、`idle3.gif`、`idle4.gif`
- 自动移动速度按当前屏幕分辨率计算：约 20 秒从左边界移动到右边界，上下浮动20%
- 移动时会随机出现上下左右移动
- 触达屏幕边缘后会立即反弹（不穿屏）

### EXE前端界面

- 主界面包含"设置""关于"两个页面。
- 左上角显示 `gifs/ameath.ico`，并作为应用与托盘图标。
- "设置"页面覆盖右键菜单可配置功能：停止移动、跟随鼠标、缩放比例、透明度、显示优先级、多开数量、开机自启、退出应用、关闭行为策略。
- 设置页"移动控制"的按钮文案会在"停止移动 / 恢复移动"之间切换，且作用范围为全部实例。
- 右键菜单中的"停止移动 / 恢复移动"仅作用于当前实例，用于单独控制某一只桌宠。
- 设置页中可配置项（如跟随、缩放、显示优先级、多开数量、透明度、关闭行为）会写入本地记录，重启后自动恢复。
- 透明度在设置页使用横向滑动条无级设置（0% ~ 100%，默认 100%），并与右键菜单实时同步。
- 显示优先级与多开数量支持设置页和右键菜单双向实时同步。
- "关于"页面居中显示 `ameath.gif`（648×648），下方区域为作者发电文字。
- 显示优先级：
  - 所有处于显示状态的桌宠实例都会保持在窗口化应用之上（置顶层级）。
  - 始终置顶：桌宠保持置顶显示。
  - 其他应用全屏时隐藏：检测到当前顶层可见窗口为全屏或最大化时会立即隐藏，优先级高于动作等待时间；若该窗口最小化后顶层变为普通窗口会立即恢复显示，若顶层仍是全屏或最大化窗口则继续隐藏。
  - 仅在桌面显示：只在桌面前台时显示，打开其他应用窗口后隐藏。
- 多开模式：
  - 可设置桌宠实例数量为 0~50。
  - 修改数量后立即补齐或缩减到目标数量。
  - 当实例数量 >= 2 时，原有实例与新生成实例都会临时保持在最顶图层，便于直观看到多开效果。
  - 当实例数量恢复为 1 时，自动取消该临时置顶并回到当前显示优先级策略。
- 透明度设置：
  - 设置页：0%~100% 横向滑动条无级设置（默认 100%）。
  - 右键菜单：10%~100% 列表设置（10% 步进）。
  - 两端操作实时同步到当前应用状态。
- 关闭桌宠菜单：
  - "仅关闭当前桌宠"只关闭当前右键操作的桌宠实例。
  - "关闭_个桌宠"支持输入自定义数量，范围外会提示"数量过少/数量过多"。
  - "一键关闭所有桌宠并退出"可直接结束全部桌宠实例并退出应用。

### 托盘与关闭行为

- 托盘右键菜单提供"打开""退出"选项。
- 点击右上角"×"默认弹窗询问"退出应用/最小化到托盘"，支持"记住选择"。
- 用户可在设置页的"点击×行为"中修改该策略。

### EXE 打包（普通用户分发）

```powershell
./exe/build_exe.ps1
```

- 打包产物在 `exe/dist/AmeathDesktopPet/`。
- `exe` 目录包含构建脚本、spec、build、dist 等 EXE 相关文件。

---

## 项目结构

```text
📦 Ameath_Desktop_Pet
├── 🐍 main.py               # 程序入口，启动桌宠事件循环
├── 📄 requirements.txt      # Python 依赖列表
├── 📁 music                 # 音乐目录（仓库仅保留目录结构，不包含音频文件）
├── 📁 exe
│   ├── ⚙️ build_exe.ps1      # EXE 打包脚本（PowerShell）
│   └── 📘 README.md          # EXE 构建与分发说明
└── 📁 pet
    ├── ⚙️ config.py          # 全局配置与资源路径
    ├── 🎞️ animation.py       # GIF 播放、缩放、镜像绘制
    ├── 🎵 music_player.py    # 全局音乐播放器单例（QMediaPlayer）
    ├── 🖥️ app_window.py      # 应用主界面（设置/音乐/关于页面）
    ├── 🪟 window.py          # 桌宠窗口与状态调度中心
    ├── 🧩 tray_controller.py # 系统托盘控制与菜单行为
    ├── 💾 settings_store.py  # 设置持久化存储与读取
    ├── ❎ close_policy.py    # 关闭策略弹窗与记忆逻辑
    ├── 🧠 state_machine.py   # 状态机（拖拽/跟随/休息/移动）
    ├── 🧭 movement.py        # 位移控制、边界检测与转向
    ├── 🖱️ input.py           # 鼠标输入（拖拽/右键菜单）
    ├── 😴 idle.py            # 随机休息控制器
    ├── 🚀 autostart.py       # Windows 开机自启管理
    └── 📋 menu.py            # 右键菜单与二级菜单构建
```

---

## English Documentation

### Overview

Ameath Desktop Pet is a Windows desktop pet application built with **PySide6**.
It supports draggable animated pets, multi-instance control, display policies, system tray integration, and a built-in music player.

### Requirements

- Windows 10 / 11
- Python 3.11+
- Dependencies in `requirements.txt`

### Quick Start

1. Clone the repository

```powershell
git clone https://github.com/sleepingjhy/Ameath-Desktop-Pet-on-Windows.git
cd Ameath-Desktop-Pet-on-Windows
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Run the app

```powershell
python main.py
```

### Core Features

#### v1.2.0

- Multilingual UI support:
  - Added 5 language options for all visual UI: `中文 / English / 日本語 / 한국어 / Français`.
  - Added `Language` selector in:
    - Frontend app `About` page.
    - Pet right-click menu.
  - Language list uses native self-names (for example: `中文`, `English`, `日本語`, `한국어`, `Français`).
  - Selected language is persisted locally and restored automatically on next startup.
- Tray music controls:
  - Added `🎵 Music` submenu in tray right-click menu, supporting:
    - Current track display (read-only).
    - `Previous / Play·Pause / Next`.
    - Play mode switch (`List Loop / Single Loop / Random`).
  - Tray music submenu remains synchronized with main player state in real time.

#### v1.1.0

- Music playback:
  - Added music playback to both right-click menu and frontend app window, playing tracks from `music/`.
  - Repository keeps the `music/` folder structure, but audio files are not committed by default; add local files yourself.
- Stability and memory cleanup:
  - Fixed several memory-leak issues.
  - Fully audited and reinforced exit-path cleanup for menu signals, player resources, timers, and list widgets.
- Right-click menu (simplified controls):
  - Right-click any pet instance → `🎵 Music` submenu:
    - Current track name (read-only).
    - `Previous / Play·Pause / Next`.
    - Play mode switch (exclusive): `List Loop / Single Loop / Random`.
    - Volume slider (app volume only; does not affect system volume).
- Frontend app window (full player):
  - Added `🎵 Music` tab in left navigation, including:
    - Current track name + seekable progress bar.
    - Main controls: `Previous / Play·Pause / Next`.
    - Play mode button (cycles with icon `🔁/🔂/🔀`).
    - Horizontal volume slider (`0` to `100%`).
    - Import local audio files into `music/`.
    - Right-click rename with synchronized file rename in `music/`.
    - Batch delete mode with two confirmation options:
      - Remove from playlist only.
      - Remove from playlist and delete local files.
    - Playlist supports jump-play, current-row highlight, drag-and-drop reorder, and stable scrollbar position.
  - Right-click menu and frontend player stay synchronized in both directions in real time.
- Context menu + instance highlight:
  - Context menu no longer follows pet movement.
  - Right-clicked instance shows sky-blue (`#00BFFF`) outline while the menu is open.
  - Outline is removed immediately when menu closes.

#### v1.0.0

- Interaction:
  - Hold left mouse button and drag: the pet shows `drag.gif` and moves with the cursor.
  - Right-click opens a fixed-position context menu; the selected instance shows a sky-blue outline until the menu closes.
  - Context menu includes:
    - Open app window.
    - Stop movement / Resume movement (affects current right-clicked instance only).
    - Follow mouse (toggle).
    - Scale (`0.1x` to `2.0x`, step `0.1`).
    - Opacity (`10%` to `100%`, step `10%`, list style in context menu).
    - Display priority (`Always on Top` / `Hide when other apps are fullscreen` / `Desktop only`).
    - Multi-instance mode (`0` to `50`, effective immediately).
    - Auto-start on system boot (Windows toggle).
    - Close submenu:
      - Close current pet only.
      - Close _ pets (custom number with validation and "too few / too many" prompts).
      - Close all pets and exit in one click.
- Animation rules:
  - Moving right: `move.gif`.
  - Moving left: mirrored `move.gif`.
  - Idle animations randomly selected from `ameath.gif`, `idle1.gif`, `idle2.gif`, `idle3.gif`, `idle4.gif`.
  - Auto-move speed adapts to screen resolution, targeting about 20 seconds from left boundary to right boundary, with ±20% fluctuation.
  - Random movement includes up/down/left/right motion.
  - Pet bounces immediately at screen edges (never moves out of screen).
- EXE frontend UI:
  - Main window includes `Settings` and `About` pages.
  - `gifs/ameath.ico` is used as both app icon and tray icon.
  - Settings page covers move control, follow mouse, scale, opacity, display priority, instance count, auto-start, app exit, and close behavior.
  - Settings-page move control applies to all instances; right-click move control applies to current instance only.
  - Configurable settings are persisted locally and restored after restart.
  - Opacity in Settings uses continuous slider (`0%` to `100%`, default `100%`) and syncs with context menu.
  - Display priority and instance count support real-time two-way synchronization between Settings and context menu.
  - About page centers `ameath.gif` (`648 × 648`) with author-support text below.
- Display priority and multi-instance behavior:
  - Visible pet instances stay above normal windowed apps.
  - `Always on Top`: always displayed on top.
  - `Hide when other apps are fullscreen`: hides immediately when top visible window is fullscreen or maximized; restores when conditions no longer match.
  - `Desktop only`: visible only when desktop is foreground.
  - Instance count is configurable from `0` to `50`, effective immediately.
  - When instance count is `>= 2`, instances are temporarily forced topmost for visibility.
  - When instance count returns to `1`, temporary topmost is removed and normal display-priority policy is restored.
- Opacity and close policy:
  - Settings page: continuous slider (`0%` to `100%`, default `100%`).
  - Context menu: list options (`10%` to `100%`, `10%` step).
  - Changes from either side synchronize in real time.
  - Tray context menu provides `Open` and `Exit`.
  - Clicking top-right `×` prompts `Quit app` or `Minimize to tray` with `Remember my choice`.
  - The click-`×` behavior is configurable in Settings.

### Build EXE

```powershell
./exe/build_exe.ps1
```

Build output is generated under `exe/dist/AmeathDesktopPet/`.