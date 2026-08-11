#!/usr/bin/env bash
# Build Aqua Focus for macOS (.app) or Ubuntu/Linux (folder)
# Supported OS family: Windows 11 / Windows 10 / macOS / Ubuntu / Linux
#   - Windows builds: use scripts/build_exe.ps1 on Windows
#   - This script: macOS (Darwin) or Linux (Ubuntu and other distros)
# Usage: ./scripts/build_unix.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> deps"
python3 -m pip install -q -r requirements.txt pyinstaller

echo "==> clean"
rm -rf dist/AquaFocus dist/AquaFocus.app build

OS="$(uname -s)"
ICON_PNG="$ROOT/assets/icons/aqua-focus-app.png"
ICON_ICO="$ROOT/assets/icons/aqua-focus.ico"

echo "==> target platforms (docs): Windows 11, Windows 10, macOS, Ubuntu, Linux"
echo "==> building on: $OS"

if [[ "$OS" == "Darwin" ]]; then
  echo "==> macOS app bundle"
  # Convert png to icns if iconutil available
  ICON_ARG=()
  if [[ -f "$ICON_PNG" ]]; then
    ICONSET="$ROOT/build/AquaFocus.iconset"
    mkdir -p "$ICONSET" "$ROOT/build"
    for s in 16 32 128 256 512; do
      s2=$((s*2))
      sips -z "$s" "$s" "$ICON_PNG" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
      sips -z "$s2" "$s2" "$ICON_PNG" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1 || true
    done
    iconutil -c icns "$ICONSET" -o "$ROOT/build/AquaFocus.icns" 2>/dev/null || true
    if [[ -f "$ROOT/build/AquaFocus.icns" ]]; then
      ICON_ARG=(--icon "$ROOT/build/AquaFocus.icns")
    fi
  fi
  python3 -m PyInstaller --noconfirm --windowed --name AquaFocus \
    --add-data "assets:assets" --add-data "docs:docs" \
    "${ICON_ARG[@]}" \
    main.py
  mkdir -p dist/AquaFocus.app/Contents/Resources/data 2>/dev/null || true
  echo "OK: dist/AquaFocus.app"
  echo "Supported: macOS (Apple Silicon / Intel)"
  echo "配布: .app を /Applications へドラッグ、または create-dmg で DMG 化"
elif [[ "$OS" == "Linux" ]]; then
  echo "==> Linux / Ubuntu onedir"
  python3 -m PyInstaller --noconfirm --windowed --name AquaFocus \
    --add-data "assets:assets" --add-data "docs:docs" \
    --icon "$ICON_ICO" \
    main.py
  mkdir -p dist/AquaFocus/data
  # .desktop helper
  cat > dist/AquaFocus/AquaFocus.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Aqua Focus
Comment=Pomodoro focus timer — Ubuntu / Linux
Exec=$(pwd)/dist/AquaFocus/AquaFocus
Icon=$(pwd)/dist/AquaFocus/_internal/assets/icons/aqua-focus-app.png
Terminal=false
Categories=Utility;Office;
EOF
  echo "OK: dist/AquaFocus/AquaFocus"
  echo "Supported: Ubuntu 22.04/24.04 LTS and other Linux (glibc)"
  echo "Ubuntu deps (if needed):"
  echo "  sudo apt install python3-tk libportaudio2 fonts-noto-cjk"
else
  echo "Unsupported build host: $OS"
  echo "Use scripts/build_exe.ps1 on Windows 10 / Windows 11"
  exit 1
fi
