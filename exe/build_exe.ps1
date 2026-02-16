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

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name AmeathDesktopPet `
    --icon "$root\gifs\ameath.ico" `
    --add-data "$root\gifs;gifs" `
    --distpath "$root\exe\dist" `
    --workpath "$root\exe\build" `
    --specpath "$root\exe" `
    "$root\main.py"

Write-Host "打包完成，输出目录: $root\exe\dist\AmeathDesktopPet" -ForegroundColor Green
