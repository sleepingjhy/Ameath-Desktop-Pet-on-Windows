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

1. 安装依赖（建议使用虚拟环境）

```powershell
pip install -r requirements.txt
```

2. 启动

```powershell
python main.py
```

## 交互

- 左键按住并拖动：显示 `drag.gif` 并拖动桌宠
- 右键桌宠：打开菜单（菜单会跟随桌宠一起移动）
  - 停止移动
  - 跟随鼠标（开关）
  - 缩放比例（0.1x ~ 2.0x，步进 0.1）
  - 透明度（10% ~ 100%，步进 10%，右键列表）
  - 显示优先级（始终置顶 / 其他应用全屏时隐藏 / 仅在桌面显示）
  - 多开模式（设置桌宠数量 1~50，立即生效）
  - 开机自启（开关，Windows）
  - 关闭桌宠（二级菜单）
    - 仅关闭当前桌宠
    - 关闭_个桌宠（输入数量，非法值提示数量过少/数量过多）
    - 一键关闭所有桌宠

## 动画规则

- 向右移动：`move.gif`
- 向左移动：`move.gif` 镜像
- 休息动画：随机播放 `ameath.gif`、`idle1.gif`、`idle2.gif`、`idle3.gif`、`idle4.gif`
- 自动移动速度按当前屏幕分辨率计算：约 20 秒从左边界移动到右边界
- 移动时会随机出现上下移动
- 触达屏幕边缘后会自动停顿并转向

## EXE前端界面

- 主界面包含“设置”“关于”两个页面。
- 左上角显示 `gifs/ameath.ico`，并作为应用与托盘图标。
- “设置”页面覆盖右键菜单可配置功能：停止移动、跟随鼠标、缩放比例、透明度、显示优先级、多开数量、开机自启、退出应用、关闭行为策略。
- 透明度在设置页使用横向滑动条无级设置（0% ~ 100%，默认 100%），并与右键菜单实时同步。
- 显示优先级与多开数量支持设置页和右键菜单双向实时同步。
- “关于”页面居中显示 `ameath.gif`（648×648），下方区域为作者发电文字。
- 显示优先级：
  - 始终置顶：桌宠保持置顶显示。
  - 其他应用全屏时隐藏：检测到前台全屏窗口后自动隐藏，退出全屏后恢复显示。
  - 仅在桌面显示：只在桌面前台时显示，打开其他应用窗口后隐藏。
- 多开模式：
  - 可设置桌宠实例数量为 1~50。
  - 修改数量后立即补齐或缩减到目标数量。
- 透明度设置：
  - 设置页：0%~100% 横向滑动条无级设置（默认 100%）。
  - 右键菜单：10%~100% 列表设置（10% 步进）。
  - 两端操作实时同步到当前应用状态。
- 关闭桌宠菜单：
  - “仅关闭当前桌宠”只关闭当前右键操作的桌宠实例。
  - “关闭_个桌宠”支持输入自定义数量，范围外会提示“数量过少/数量过多”。
  - “一键关闭所有桌宠”可直接结束全部桌宠实例。

## 托盘与关闭行为

- 托盘右键菜单提供“打开”“退出”选项。
- 点击右上角“×”默认弹窗询问“退出应用/最小化到托盘”，支持“记住选择”。
- 用户可在设置页的“点击×行为”中修改该策略。

## EXE 打包（普通用户分发）

```powershell
./exe/build_exe.ps1
```

- 打包产物在 `exe/dist/AmeathDesktopPet/`。
- `exe` 目录包含构建脚本、spec、build、dist 等 EXE 相关文件。

## 项目结构

```text
📦 Ameath_Desktop_Pet
├── 🐍 main.py               # 程序入口，启动桌宠事件循环
├── 📄 requirements.txt      # Python 依赖列表
├── 📁 exe
│   ├── ⚙️ build_exe.ps1      # EXE 打包脚本（PowerShell）
│   └── 📘 README.md          # EXE 构建与分发说明
└── 📁 pet
    ├── ⚙️ config.py          # 全局配置与资源路径
    ├── 🎞️ animation.py       # GIF 播放、缩放、镜像绘制
    ├── 🖥️ app_window.py      # 应用主界面（设置/关于页面）
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
