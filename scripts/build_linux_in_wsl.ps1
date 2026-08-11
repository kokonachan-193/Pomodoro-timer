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

# Robust Windows → /mnt/... (avoid broken wslpath on some hosts)
$drive = $Root.Substring(0, 1).ToLowerInvariant()
$rest = ($Root.Substring(2) -replace "\\", "/")
$wslRoot = "/mnt/$drive$rest"
Write-Host "WSL project path: $wslRoot"

$tmpSh = Join-Path $env:TEMP "aqua_focus_wsl_build.sh"
$bash = @"
#!/bin/bash
set -euo pipefail
cd '$wslRoot'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-venv python3-tk libportaudio2 portaudio19-dev
python3 -m venv .venv-wsl
. .venv-wsl/bin/activate
pip install -U pip
pip install -r requirements.txt pyinstaller
# normalize CRLF on shell scripts if copied from Windows
sed -i 's/\r$//' scripts/build_unix.sh scripts/make_release_unix.sh || true
chmod +x scripts/build_unix.sh scripts/make_release_unix.sh
./scripts/make_release_unix.sh
# smoke: binary exists and --help / file type
test -x dist/AquaFocus/AquaFocus
file dist/AquaFocus/AquaFocus || true
ls -lh dist/releases/
"@
# Write UTF-8 without BOM, then force LF
[System.IO.File]::WriteAllText($tmpSh, ($bash -replace "`r`n", "`n" -replace "`r", "`n"))

$wslTmp = "/mnt/c/Users/kaihu.KOKONA/AppData/Local/Temp/aqua_focus_wsl_build.sh"
# Prefer wslpath for temp when available
$wslTmpResolved = (wsl -d Ubuntu -- wslpath -a $tmpSh 2>$null | Out-String).Trim()
if ($wslTmpResolved -and $wslTmpResolved.StartsWith("/")) { $wslTmp = $wslTmpResolved }

Write-Host "==> build inside Ubuntu" -ForegroundColor Cyan
wsl -d Ubuntu -- bash $wslTmp
if ($LASTEXITCODE -ne 0) { throw "WSL build failed" }

$outDir = Join-Path $Root "downloads\Linux"
$ubuntuDir = Join-Path $Root "downloads\Ubuntu"
New-Item -ItemType Directory -Force -Path $outDir, $ubuntuDir | Out-Null
$tarball = Get-ChildItem (Join-Path $Root "dist\releases\AquaFocus-Linux-Portable-*.tar.gz") | Select-Object -First 1
if (-not $tarball) { throw "Linux tarball missing" }
Copy-Item $tarball.FullName $outDir -Force
Copy-Item $tarball.FullName (Join-Path $ubuntuDir "AquaFocus-Ubuntu-Portable-1.0.0.tar.gz") -Force
Remove-Item (Join-Path $outDir "PLACE_PACKAGE_HERE.txt") -ErrorAction SilentlyContinue
Remove-Item (Join-Path $ubuntuDir "PLACE_PACKAGE_HERE.txt") -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "OK → downloads\Linux\ and downloads\Ubuntu\" -ForegroundColor Green
Get-ChildItem $outDir, $ubuntuDir | Format-Table Name, Length -AutoSize
