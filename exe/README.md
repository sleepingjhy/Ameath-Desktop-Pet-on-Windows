# EXE 打包目录

- `build_exe.ps1`：一键打包脚本（PyInstaller onedir）。
- `dist/`：生成的可分发应用目录。
- `build/`：中间构建产物。
- `*.spec`：PyInstaller 规范文件（由脚本生成）。

## 使用方式

```powershell
./exe/build_exe.ps1
```

## 说明

- 产物默认放在 `exe/dist/AmeathDesktopPet`。
- 启动可执行文件后，桌宠窗口与前端主界面会同时显示。
- 打包后会在产物根目录自动生成独立 `music/` 文件夹，普通用户可直接自行添加音乐文件。
- 打包后会在产物根目录自动放置 `使用说明.txt`，用于指导普通用户使用各项功能。
