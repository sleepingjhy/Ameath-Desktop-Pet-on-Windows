Param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

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
    --name AmeathDesktopPet `
    --icon "$root\gifs\ameath.ico" `
    --distpath "$root\exe\dist" `
    --workpath "$root\exe\build" `
    --specpath "$root\exe" `
    "$root\main.py"

$distRoot = Join-Path $root "exe\dist\AmeathDesktopPet"

# 将 music 目录单独放到产物根目录，便于普通用户自行增删音乐文件。
$distMusic = Join-Path $distRoot "music"
if (Test-Path $distMusic) {
    Remove-Item -Recurse -Force $distMusic -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $distMusic -Force | Out-Null

$srcMusic = Join-Path $root "music"
if (Test-Path $srcMusic) {
    Copy-Item -Path (Join-Path $srcMusic "*") -Destination $distMusic -Recurse -Force
}

# 同步普通用户说明文档到产物根目录（排除开发用 requirements.txt）。
Get-ChildItem -Path $root -File -Filter "*.txt" |
    Where-Object { $_.Name -ne "requirements.txt" } |
    ForEach-Object {
        Copy-Item -Path $_.FullName -Destination (Join-Path $distRoot $_.Name) -Force
    }

Write-Host "打包完成，输出目录: $distRoot" -ForegroundColor Green
