# Elevate once: install WSL + Ubuntu, then (after reboot if asked) build Linux package.
# Usage: right-click PowerShell → Run as administrator, then:
#   cd path\to\pomodo
#   .\scripts\setup_wsl_and_build_linux.ps1

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "==> Enabling WSL features" -ForegroundColor Cyan
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host "==> wsl --install -d Ubuntu" -ForegroundColor Cyan
wsl --install -d Ubuntu --no-launch

Write-Host ""
Write-Host "If Windows asks to reboot, reboot, then run:" -ForegroundColor Yellow
Write-Host "  .\scripts\build_linux_in_wsl.ps1"
Write-Host ""
Write-Host "First Ubuntu boot may ask for a Linux username/password."
