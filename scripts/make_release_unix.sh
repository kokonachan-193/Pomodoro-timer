#!/usr/bin/env bash
# Build downloadable packages for macOS or Ubuntu/Linux (run ON that OS).
# Output: dist/releases/
#   macOS  -> AquaFocus-macOS-2.1.4.zip  (contains AquaFocus.app)
#   Linux  -> AquaFocus-Linux-Portable-2.1.4.tar.gz

set -euo pipefail
VERSION="${VERSION:-2.1.4}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> build app"
bash "$ROOT/scripts/build_unix.sh"

REL="$ROOT/dist/releases"
mkdir -p "$REL"
OS="$(uname -s)"

if [[ "$OS" == "Darwin" ]]; then
  APP="$ROOT/dist/AquaFocus.app"
  if [[ ! -d "$APP" ]]; then
    # onedir fallback some PyInstaller layouts
    if [[ -d "$ROOT/dist/AquaFocus/AquaFocus.app" ]]; then
      APP="$ROOT/dist/AquaFocus/AquaFocus.app"
    else
      echo "AquaFocus.app not found under dist/"
      exit 1
    fi
  fi
  OUT="$REL/AquaFocus-macOS-$VERSION.zip"
  rm -f "$OUT"
  ditto -c -k --sequesterRsrc --keepParent "$APP" "$OUT"
  echo "OK: $OUT"
  echo "User: unzip → drag AquaFocus.app to Applications (or double-click)"
elif [[ "$OS" == "Linux" ]]; then
  DIR="$ROOT/dist/AquaFocus"
  [[ -x "$DIR/AquaFocus" ]] || { echo "dist/AquaFocus/AquaFocus missing"; exit 1; }
  OUT="$REL/AquaFocus-Linux-Portable-$VERSION.tar.gz"
  rm -f "$OUT"
  tar -C "$ROOT/dist" -czf "$OUT" AquaFocus
  echo "OK: $OUT"
  echo "User: tar xzf … && ./AquaFocus/AquaFocus"
else
  echo "Run on macOS or Linux. For Windows use scripts/make_release_win.ps1"
  exit 1
fi

ls -lh "$REL"
