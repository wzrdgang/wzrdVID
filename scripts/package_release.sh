#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_BUNDLE="dist/WZRD.VID.app"
ZIP_NAME="WZRD.VID-macOS.zip"

if [ "${1:-}" = "--build" ] || [ ! -d "$APP_BUNDLE" ]; then
  echo "Building WZRD.VID.app..."
  ./build_app.sh
fi

if [ ! -d "$APP_BUNDLE" ]; then
  echo "Error: $APP_BUNDLE does not exist. Run ./build_app.sh first." >&2
  exit 1
fi

rm -f "$ZIP_NAME"
ditto -c -k --sequesterRsrc --keepParent "$APP_BUNDLE" "$ZIP_NAME"

if command -v du >/dev/null 2>&1; then
  echo "Created: $ZIP_NAME ($(du -h "$ZIP_NAME" | awk '{print $1}'))"
else
  echo "Created: $ZIP_NAME"
fi

echo "Upload $ZIP_NAME to GitHub Releases."
