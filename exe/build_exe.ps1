Param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# 统一终端编码，避免中文提示在不同 PowerShell 终端中出现乱码。
try {
    chcp 65001 | Out-Null
} catch {
}
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::InputEncoding = $utf8NoBom
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch {
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

if ($Clean) {
    Remove-Item -Recurse -Force "$root\exe\build" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$root\exe\dist" -ErrorAction SilentlyContinue
}

& "$root\.venv\Scripts\pyside6-rcc.exe" "$root\resources.qrc" -o "$root\pet\resources_rc.py"

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name AemeathDesktopPet `
    --icon "$root\gifs\aemeath.ico" `
    --distpath "$root\exe\dist" `
    --workpath "$root\exe\build" `
    --specpath "$root\exe" `
    "$root\main.py"

$distRoot = Join-Path $root "exe\dist\AemeathDesktopPet"

# 同步聊天/表情等文件资源目录。
$distGifs = Join-Path $distRoot "gifs"
if (Test-Path $distGifs) {
    Remove-Item -Recurse -Force $distGifs -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $distGifs -Force | Out-Null

$srcGifs = Join-Path $root "gifs"
if (Test-Path $srcGifs) {
    Copy-Item -Path (Join-Path $srcGifs "*") -Destination $distGifs -Recurse -Force
}

# 将 music 目录放到产物根目录，但不拷贝任何音频文件。
# 仅保留占位文件，避免分发包携带本地音乐资源。
$distMusic = Join-Path $distRoot "music"
if (Test-Path $distMusic) {
    Remove-Item -Recurse -Force $distMusic -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $distMusic -Force | Out-Null

$srcMusic = Join-Path $root "music"
if (Test-Path $srcMusic) {
    @('.gitignore', '.gitkeep') |
        ForEach-Object {
            $placeholder = Join-Path $srcMusic $_
            if (Test-Path $placeholder) {
                Copy-Item -Path $placeholder -Destination (Join-Path $distMusic $_) -Force
            }
        }
}

# 同步普通用户说明文档到产物根目录（排除开发用 requirements.txt）。
Get-ChildItem -Path $root -File -Filter "*.txt" |
    Where-Object { $_.Name -ne "requirements.txt" } |
    ForEach-Object {
        Copy-Item -Path $_.FullName -Destination (Join-Path $distRoot $_.Name) -Force
    }

# 同步安全模板配置文件（不含本地密钥）。
# EXE 运行时本地密钥写入 AppData 下的 config_local.yaml。
$projectConfig = Join-Path $root "config.yaml"
if (Test-Path $projectConfig) {
    Copy-Item -Path $projectConfig -Destination (Join-Path $distRoot "config.yaml") -Force
}

# 删除 PyInstaller 生成的 spec 文件，保持项目整洁。
$specFile = Join-Path $root "exe\AemeathDesktopPet.spec"
if (Test-Path $specFile) {
    Remove-Item -Force $specFile -ErrorAction SilentlyContinue
}

Write-Host "打包完成，输出目录: $distRoot" -ForegroundColor Green
