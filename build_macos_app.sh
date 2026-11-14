#!/bin/bash
set -euo pipefail

APP_NAME="AI Meeting Assistant"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This build must run on macOS."
  exit 1
fi

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "This build is intended for Apple Silicon (arm64)."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.12 is required. Install it, then rerun this script."
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info[:2] != (3, 12):
    raise SystemExit("Use Python 3.12 to build this application.")
PY

VENV_DIR="$ROOT_DIR/.build-venv"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements-macos-build.txt

echo "Compiling the native macOS system-audio helper..."
mkdir -p build_support
swiftc -O -parse-as-library -target arm64-apple-macos13.0 \
  audio/macos_system_audio.swift \
  -o build_support/system_audio_capture
chmod 755 build_support/system_audio_capture

echo "Building $APP_NAME.app..."
python -m PyInstaller --noconfirm --clean "AI Meeting Assistant.spec"

APP_PATH="$ROOT_DIR/dist/$APP_NAME.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "Build failed: expected app bundle was not created at $APP_PATH"
  exit 1
fi

echo "Creating DMG installer..."
DMG_PATH="$ROOT_DIR/dist/$APP_NAME.dmg"
rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_PATH" \
  -ov -format UDZO "$DMG_PATH"

echo
echo "Build complete:"
echo "  App: $APP_PATH"
echo "  Installer: $DMG_PATH"
echo
echo "Open the DMG and drag the app into Applications."
echo "This personal build is unsigned; macOS may require right-click > Open on first launch."
