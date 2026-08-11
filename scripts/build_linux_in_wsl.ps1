# Build Linux portable tarball inside WSL Ubuntu → downloads/Linux/
# Prerequisites: WSL + Ubuntu installed and you can run: wsl -d Ubuntu
# Usage:  .\scripts\build_linux_in_wsl.ps1

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "==> check WSL Ubuntu" -ForegroundColor Cyan
wsl -d Ubuntu -- echo "wsl-ok"
if ($LASTEXITCODE -ne 0) {
    throw "Ubuntu WSL not ready. Run .\scripts\setup_wsl_and_build_linux.ps1 as Administrator first (reboot if asked)."
}

# Windows path → /mnt/c/...
$wslRoot = wsl -d Ubuntu -- wslpath -a "$Root"
$wslRoot = ($wslRoot | Out-String).Trim()
Write-Host "WSL project path: $wslRoot"

$bash = @"
set -euo pipefail
cd '$wslRoot'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-venv python3-tk libportaudio2 portaudio19-dev
python3 -m venv .venv-wsl
. .venv-wsl/bin/activate
pip install -U pip
pip install -r requirements.txt pyinstaller
chmod +x scripts/build_unix.sh scripts/make_release_unix.sh
./scripts/make_release_unix.sh
ls -lh dist/releases/
"@

Write-Host "==> build inside Ubuntu" -ForegroundColor Cyan
$bash | wsl -d Ubuntu -- bash -s
if ($LASTEXITCODE -ne 0) { throw "WSL build failed" }

$outDir = Join-Path $Root "downloads\Linux"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Copy-Item (Join-Path $Root "dist\releases\AquaFocus-Linux-Portable-*.tar.gz") $outDir -Force
Remove-Item (Join-Path $outDir "PLACE_PACKAGE_HERE.txt") -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "OK → downloads\Linux\" -ForegroundColor Green
Get-ChildItem $outDir | Format-Table Name, Length -AutoSize
