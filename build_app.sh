#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export PIP_CACHE_DIR="$PWD/.pip-cache"
export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"

mkdir -p "$PIP_CACHE_DIR" "$PYINSTALLER_CONFIG_DIR"
ICON_PATH="/private/tmp/wzrd_vid.icns"
APP_VERSION="0.1.1"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

VENV_PYTHON="$PWD/.venv/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt
"$VENV_PYTHON" scripts/generate_branding.py
"$VENV_PYTHON" scripts/generate_icon.py
"$VENV_PYTHON" scripts/generate_ui_textures.py
cp "$PWD/assets/wzrd_vid.icns" "$ICON_PATH"

"$VENV_PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "WZRD.VID" \
  --icon "$ICON_PATH" \
  --osx-bundle-identifier "com.samhowell.wzrdvid" \
  --add-data "$PWD/assets/wzrd_vid_icon.png:assets" \
  --add-data "$PWD/assets/logo:assets/logo" \
  --add-data "$PWD/assets/branding:assets/branding" \
  --add-data "$PWD/assets/ui:assets/ui" \
  --specpath build \
  --hidden-import cv2 \
  --exclude-module PySide6.Qt3DAnimation \
  --exclude-module PySide6.Qt3DCore \
  --exclude-module PySide6.Qt3DExtras \
  --exclude-module PySide6.Qt3DInput \
  --exclude-module PySide6.Qt3DLogic \
  --exclude-module PySide6.Qt3DRender \
  --exclude-module PySide6.QtAsyncio \
  --exclude-module PySide6.QtBluetooth \
  --exclude-module PySide6.QtCharts \
  --exclude-module PySide6.QtDataVisualization \
  --exclude-module PySide6.QtDesigner \
  --exclude-module PySide6.QtGraphs \
  --exclude-module PySide6.QtHelp \
  --exclude-module PySide6.QtHttpServer \
  --exclude-module PySide6.QtLocation \
  --exclude-module PySide6.QtMultimedia \
  --exclude-module PySide6.QtMultimediaWidgets \
  --exclude-module PySide6.QtNfc \
  --exclude-module PySide6.QtNetwork \
  --exclude-module PySide6.QtOpenGL \
  --exclude-module PySide6.QtOpenGLWidgets \
  --exclude-module PySide6.QtPdf \
  --exclude-module PySide6.QtPdfWidgets \
  --exclude-module PySide6.QtPositioning \
  --exclude-module PySide6.QtPrintSupport \
  --exclude-module PySide6.QtQml \
  --exclude-module PySide6.QtQuick \
  --exclude-module PySide6.QtQuick3D \
  --exclude-module PySide6.QtQuickControls2 \
  --exclude-module PySide6.QtQuickWidgets \
  --exclude-module PySide6.QtRemoteObjects \
  --exclude-module PySide6.QtScxml \
  --exclude-module PySide6.QtSensors \
  --exclude-module PySide6.QtSerialBus \
  --exclude-module PySide6.QtSerialPort \
  --exclude-module PySide6.QtSpatialAudio \
  --exclude-module PySide6.QtSql \
  --exclude-module PySide6.QtStateMachine \
  --exclude-module PySide6.QtSvg \
  --exclude-module PySide6.QtSvgWidgets \
  --exclude-module PySide6.QtTextToSpeech \
  --exclude-module PySide6.QtUiTools \
  --exclude-module PySide6.QtWebChannel \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineQuick \
  --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module PySide6.QtWebSockets \
  --exclude-module PySide6.QtWebView \
  --exclude-module PySide6.scripts \
  app.py

APP_BUNDLE="dist/WZRD.VID.app"
QT_ROOT="$APP_BUNDLE/Contents/Frameworks/PySide6/Qt"
QT_RESOURCES="$APP_BUNDLE/Contents/Resources/PySide6/Qt"
INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"

# PyInstaller's PySide6 hook is conservative. WZRD.VID uses QWidget, QtGui, and
# QtCore only, so remove QML/Quick/PDF/virtual-keyboard/plugin payloads that are
# not needed for Finder launch, previews, rendering, or project presets.
if [ -d "$QT_ROOT" ]; then
  rm -rf \
    "$QT_ROOT/lib/QtNetwork.framework" \
    "$QT_ROOT/lib/QtOpenGL.framework" \
    "$QT_ROOT/lib/QtPdf.framework" \
    "$QT_ROOT/lib/QtQml.framework" \
    "$QT_ROOT/lib/QtQmlMeta.framework" \
    "$QT_ROOT/lib/QtQmlModels.framework" \
    "$QT_ROOT/lib/QtQmlWorkerScript.framework" \
    "$QT_ROOT/lib/QtQuick.framework" \
    "$QT_ROOT/lib/QtSvg.framework" \
    "$QT_ROOT/lib/QtVirtualKeyboard.framework" \
    "$QT_ROOT/lib/QtVirtualKeyboardQml.framework" \
    "$QT_ROOT/plugins/generic" \
    "$QT_ROOT/plugins/iconengines" \
    "$QT_ROOT/plugins/networkinformation" \
    "$QT_ROOT/plugins/platforminputcontexts" \
    "$QT_ROOT/plugins/tls"
  if [ -d "$QT_ROOT/plugins/platforms" ]; then
    find "$QT_ROOT/plugins/platforms" -type f ! -name 'libqcocoa.dylib' -delete
  fi
  if [ -d "$QT_ROOT/plugins/imageformats" ]; then
    find "$QT_ROOT/plugins/imageformats" -type f \
      ! -name 'libqjpeg.dylib' \
      ! -name 'libqgif.dylib' \
      ! -name 'libqicns.dylib' \
      ! -name 'libqwebp.dylib' \
      -delete
  fi
fi

if [ -d "$QT_RESOURCES/translations" ]; then
  rm -rf "$QT_RESOURCES/translations"
fi

if [ -f "$INFO_PLIST" ]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $APP_VERSION" "$INFO_PLIST"
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $APP_VERSION" "$INFO_PLIST" 2>/dev/null || \
    /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $APP_VERSION" "$INFO_PLIST"
fi

# Pruning after bundling changes the resource envelope, so refresh the ad-hoc
# signature that PyInstaller creates for local double-click launch.
codesign --force --deep --sign - "$APP_BUNDLE" >/dev/null

rm -rf "dist/WZRD.VID"


echo "Built: dist/WZRD.VID.app"
