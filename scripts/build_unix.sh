#!/usr/bin/env bash
# Build Aqua Focus for macOS (.app) or Ubuntu/Linux (folder)
# Uses aqua_focus.spec (ffmpeg + i18n bundled). Windows: scripts/build_exe.ps1
# Usage: ./scripts/build_unix.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> deps"
python3 -m pip install -q -r requirements.txt pyinstaller

echo "==> clean"
rm -rf dist/AquaFocus dist/AquaFocus.app build/aqua_focus

OS="$(uname -s)"
echo "==> building on: $OS (targets: Win10/11 · macOS · Ubuntu/Linux via CI too)"

if [[ "$OS" == "Darwin" ]]; then
  echo "==> macOS icon"
  PNG="$ROOT/assets/icons/aqua-focus-app.png"
  ICONSET="$ROOT/build/AquaFocus.iconset"
  mkdir -p "$ICONSET" "$ROOT/build"
  if [[ -f "$PNG" ]]; then
    for s in 16 32 128 256 512; do
      s2=$((s * 2))
      sips -z "$s" "$s" "$PNG" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
      sips -z "$s2" "$s2" "$PNG" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null 2>&1 || true
    done
    iconutil -c icns "$ICONSET" -o "$ROOT/build/AquaFocus.icns" 2>/dev/null || true
  fi
  python3 -m PyInstaller --noconfirm aqua_focus.spec
  mkdir -p dist/AquaFocus.app/Contents/Resources/data 2>/dev/null || true
  echo "OK: dist/AquaFocus.app (or dist/AquaFocus/)"
elif [[ "$OS" == "Linux" ]]; then
  python3 -m PyInstaller --noconfirm aqua_focus.spec
  mkdir -p dist/AquaFocus/data
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
  echo "Optional: sudo apt install python3-tk libportaudio2 fonts-noto-cjk"
else
  echo "Unsupported build host: $OS — use scripts/build_exe.ps1 on Windows"
  exit 1
fi
