#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_BUNDLE="dist/WZRD.VID.app"
DMG_NAME="WZRD.VID-macOS.dmg"
VOLUME_NAME="WZRD.VID"
EXPECTED_BUNDLE_ID="com.samhowell.wzrdvid"
EXPECTED_VERSION="$(tr -d '[:space:]' < VERSION)"

DMG_WORK_DIR=""
DMG_MOUNT_POINT=""
DMG_MOUNT_DEVICE=""

fail() {
  echo "Error: $*" >&2
  exit 1
}

cleanup() {
  local phase6_exit_code=$?
  trap - EXIT INT TERM
  set +e

  if [ -n "$DMG_MOUNT_DEVICE" ]; then
    hdiutil detach "$DMG_MOUNT_DEVICE" >/dev/null 2>&1 || \
      hdiutil detach -force "$DMG_MOUNT_DEVICE" >/dev/null 2>&1
  elif [ -n "$DMG_MOUNT_POINT" ] && mount | grep -Fq " on $DMG_MOUNT_POINT "; then
    hdiutil detach "$DMG_MOUNT_POINT" >/dev/null 2>&1 || \
      hdiutil detach -force "$DMG_MOUNT_POINT" >/dev/null 2>&1
  fi

  if [[ "$DMG_WORK_DIR" == /tmp/wzrdvid-dmg.* ]] && [ -d "$DMG_WORK_DIR" ]; then
    rm -rf -- "$DMG_WORK_DIR"
  fi

  exit "$phase6_exit_code"
}
trap cleanup EXIT INT TERM

bundle_value() {
  local bundle_path="$1"
  local plist_key="$2"
  /usr/libexec/PlistBuddy -c "Print :$plist_key" "$bundle_path/Contents/Info.plist"
}

validate_app_bundle() {
  local bundle_path="$1"
  local bundle_label="$2"
  local dangling_link=""
  local bundle_id=""
  local bundle_version=""
  local verification_details=""
  local signature_details=""

  [ -d "$bundle_path" ] || fail "$bundle_label is missing: $bundle_path"
  [ -f "$bundle_path/Contents/Info.plist" ] || fail "$bundle_label has no Info.plist"

  dangling_link="$(find -L "$bundle_path" -type l -print -quit)"
  if [ -n "$dangling_link" ]; then
    echo "Error: dangling symlink(s) found in $bundle_label:" >&2
    find -L "$bundle_path" -type l -print >&2
    exit 1
  fi

  if ! verification_details="$(codesign --verify --deep --strict --verbose=4 "$bundle_path" 2>&1)"; then
    printf '%s\n' "$verification_details" >&2
    fail "$bundle_label failed strict codesign verification"
  fi

  bundle_id="$(bundle_value "$bundle_path" CFBundleIdentifier)"
  bundle_version="$(bundle_value "$bundle_path" CFBundleShortVersionString)"
  [ "$bundle_id" = "$EXPECTED_BUNDLE_ID" ] || \
    fail "$bundle_label Bundle ID is $bundle_id; expected $EXPECTED_BUNDLE_ID"
  [ "$bundle_version" = "$EXPECTED_VERSION" ] || \
    fail "$bundle_label version is $bundle_version; expected $EXPECTED_VERSION"

  signature_details="$(codesign -dv --verbose=4 "$bundle_path" 2>&1)"
  grep -qx 'Signature=adhoc' <<<"$signature_details" || \
    fail "$bundle_label is not ad-hoc signed"
  grep -qx 'TeamIdentifier=not set' <<<"$signature_details" || \
    fail "$bundle_label unexpectedly has a TeamIdentifier"

  echo "Validated $bundle_label: $bundle_id $bundle_version, ad-hoc, no TeamIdentifier"
}

for required_tool in hdiutil ditto codesign shasum; do
  command -v "$required_tool" >/dev/null 2>&1 || fail "required macOS tool not found: $required_tool"
done

validate_app_bundle "$APP_BUNDLE" "source app"

DMG_WORK_DIR="$(mktemp -d /tmp/wzrdvid-dmg.XXXXXX)"
STAGING_DIR="$DMG_WORK_DIR/staging"
STAGED_APP="$STAGING_DIR/WZRD.VID.app"
TEMP_DMG="$DMG_WORK_DIR/$DMG_NAME"
DMG_MOUNT_POINT="$DMG_WORK_DIR/mount"

mkdir -p "$STAGING_DIR" "$DMG_MOUNT_POINT"
DMG_MOUNT_POINT="$(cd "$DMG_MOUNT_POINT" && pwd -P)"
ditto "$APP_BUNDLE" "$STAGED_APP"
ln -s /Applications "$STAGING_DIR/Applications"

validate_app_bundle "$STAGED_APP" "staged app"
[ -L "$STAGING_DIR/Applications" ] || fail "staged Applications shortcut is not a symlink"
[ "$(readlink "$STAGING_DIR/Applications")" = "/Applications" ] || \
  fail "staged Applications shortcut does not point to /Applications"

hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGING_DIR" \
  -format UDZO \
  -imagekey zlib-level=9 \
  -ov \
  "$TEMP_DMG"
hdiutil verify "$TEMP_DMG"

ATTACH_OUTPUT="$(hdiutil attach -readonly -nobrowse -mountpoint "$DMG_MOUNT_POINT" "$TEMP_DMG")"
DMG_MOUNT_DEVICE="$(awk '$1 ~ /^\/dev\// && NF >= 3 { device = $1 } END { print device }' <<<"$ATTACH_OUTPUT")"
ACTUAL_MOUNT_POINT="$(awk '$1 ~ /^\/dev\// && NF >= 3 { point = $NF } END { print point }' <<<"$ATTACH_OUTPUT")"

[ -n "$DMG_MOUNT_DEVICE" ] || fail "could not identify the mounted DMG device"
[ "$ACTUAL_MOUNT_POINT" = "$DMG_MOUNT_POINT" ] || \
  fail "DMG mounted at unexpected path: ${ACTUAL_MOUNT_POINT:-unknown}"

# Validation-only failure injection proves the cleanup trap without altering the
# normal packaging path or the already-created final DMG.
if [ "${WZRDVID_DMG_TEST_FAIL_AFTER_MOUNT:-0}" = "1" ]; then
  fail "injected failure after DMG mount"
fi

MOUNTED_APP="$ACTUAL_MOUNT_POINT/WZRD.VID.app"
MOUNTED_APPLICATIONS="$ACTUAL_MOUNT_POINT/Applications"
[ -L "$MOUNTED_APPLICATIONS" ] || fail "mounted DMG Applications shortcut is not a symlink"
[ "$(readlink "$MOUNTED_APPLICATIONS")" = "/Applications" ] || \
  fail "mounted DMG Applications shortcut does not point to /Applications"

while IFS= read -r -d '' mounted_item; do
  case "$(basename "$mounted_item")" in
    WZRD.VID.app|Applications|.DS_Store) ;;
    *) fail "unexpected top-level DMG content: $(basename "$mounted_item")" ;;
  esac
done < <(find "$ACTUAL_MOUNT_POINT" -mindepth 1 -maxdepth 1 -print0)

validate_app_bundle "$MOUNTED_APP" "mounted DMG app"

hdiutil detach "$DMG_MOUNT_DEVICE" >/dev/null
DMG_MOUNT_DEVICE=""
DMG_MOUNT_POINT=""

mv -f -- "$TEMP_DMG" "$DMG_NAME"
hdiutil verify "$DMG_NAME"

DMG_BYTES="$(stat -f '%z' "$DMG_NAME")"
DMG_HUMAN="$(du -h "$DMG_NAME" | awk '{print $1}')"
DMG_SHA256="$(shasum -a 256 "$DMG_NAME" | awk '{print $1}')"

echo "Created: $DMG_NAME"
echo "Size: $DMG_BYTES bytes ($DMG_HUMAN)"
echo "SHA-256: $DMG_SHA256"
echo "Install: drag WZRD.VID.app onto Applications in the mounted image."
