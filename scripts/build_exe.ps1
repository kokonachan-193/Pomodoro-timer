# Aqua Focus — Windows build (Windows 10 / 11)
# Usage (from repo root):  .\scripts\build_exe.ps1
# macOS / Ubuntu / Linux:  ./scripts/build_unix.sh

$ErrorActionPreference = "Stop"

if (-not $PSScriptRoot) {
    throw "Run this script as a file: .\scripts\build_exe.ps1"
}
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "==> deps (pyinstaller)" -ForegroundColor Cyan
py -m pip install -q -r requirements.txt pyinstaller

Write-Host "==> clean dist/build" -ForegroundColor Cyan
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

Write-Host "==> PyInstaller (onedir, windowed)" -ForegroundColor Cyan
py -m PyInstaller --noconfirm aqua_focus.spec

$exe = Join-Path $Root "dist\AquaFocus\AquaFocus.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build failed: $exe not found"
}

$dataDir = Join-Path $Root "dist\AquaFocus\data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

Write-Host ""
Write-Host "OK: $exe" -ForegroundColor Green
Write-Host "Distribute the whole folder: dist\AquaFocus\"
Write-Host ""
Write-Host "Installer (optional):" -ForegroundColor Yellow
Write-Host "  & 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' .\installer\aqua-focus.iss"
Write-Host "  -> dist\installer\AquaFocusSetup-*.exe"
