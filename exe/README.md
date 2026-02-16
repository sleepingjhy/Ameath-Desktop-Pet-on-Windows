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
