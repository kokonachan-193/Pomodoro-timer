# After reboot: finish Ubuntu install (if needed) and build Linux package.
# Usage:  .\scripts\after_reboot_build_linux.ps1

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "==> wsl status" -ForegroundColor Cyan
wsl --status 2>&1 | Out-Host

Write-Host "==> ensure Ubuntu" -ForegroundColor Cyan
$listed = & wsl -l -q 2>$null
if (-not ($listed -match "Ubuntu")) {
    Write-Host "Installing Ubuntu (first time may open a window for username/password)..."
    wsl --install -d Ubuntu --no-launch
    # Launch once to finish registration
    Start-Process "wt.exe" -ArgumentList "wsl -d Ubuntu -- echo setup-ok" -ErrorAction SilentlyContinue
    Start-Sleep 5
    wsl -d Ubuntu -- bash -lc "echo ubuntu-ready"
}

Write-Host "==> build Linux package" -ForegroundColor Cyan
& (Join-Path $Root "scripts\build_linux_in_wsl.ps1")
