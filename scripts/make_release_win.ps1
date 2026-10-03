# Build Windows release assets for GitHub Releases (download & run, no build needed)
# Usage (repo root):  .\scripts\make_release_win.ps1
# Outputs:
#   dist\releases\AquaFocus-Windows-Portable-$Version.zip
#   dist\releases\AquaFocusSetup-$Version.exe

$ErrorActionPreference = "Stop"
$Version = if ($env:VERSION) { $env:VERSION } else { "2.1.9" }

if (-not $PSScriptRoot) { throw "Run as: .\scripts\make_release_win.ps1" }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "==> build exe" -ForegroundColor Cyan
& (Join-Path $Root "scripts\build_exe.ps1")

$exeDir = Join-Path $Root "dist\AquaFocus"
$exe = Join-Path $exeDir "AquaFocus.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "Missing $exe" }

$relDir = Join-Path $Root "dist\releases"
New-Item -ItemType Directory -Force -Path $relDir | Out-Null

$zipName = "AquaFocus-Windows-Portable-$Version.zip"
$zipPath = Join-Path $relDir $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host "==> zip portable" -ForegroundColor Cyan
$stage = Join-Path $env:TEMP "AquaFocus-portable-stage-$Version"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
Copy-Item $exeDir $stage -Recurse -Force
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$setupOut = Join-Path $relDir "AquaFocusSetup-$Version.exe"
if (Test-Path -LiteralPath $iscc) {
    Write-Host "==> Inno Setup installer" -ForegroundColor Cyan
    $iss = Join-Path $Root "installer\aqua-focus.iss"
    & $iscc "/DMyAppVersion=$Version" $iss
    $built = Join-Path $Root "dist\installer\AquaFocusSetup-$Version.exe"
    if (Test-Path -LiteralPath $built) {
        Copy-Item $built $setupOut -Force
    } else {
        $fallback = Get-ChildItem -Path (Join-Path $Root "dist\installer") -Filter "AquaFocusSetup-*.exe" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($fallback) {
            Write-Host "WARN: Expected setup not found at $built; renaming $($fallback.Name)" -ForegroundColor Yellow
            Copy-Item $fallback.FullName $setupOut -Force
        } else {
            throw "Setup installer was not created: $built"
        }
    }
} else {
    Write-Host "WARN: Inno Setup not found - portable zip only" -ForegroundColor Yellow
}

if (-not (Test-Path -LiteralPath $setupOut)) {
    throw "Missing release installer asset: $setupOut"
}

Write-Host ""
Write-Host "Release assets ready:" -ForegroundColor Green
Get-ChildItem $relDir | ForEach-Object { Write-Host ("  {0}  ({1:N1} MB)" -f $_.Name, ($_.Length/1MB)) }
Write-Host ""
Write-Host "Upload these on GitHub -> Releases -> New release (tag v$Version)"
Write-Host "  https://github.com/kokonachan-193/Pomodoro-timer/releases/new"
