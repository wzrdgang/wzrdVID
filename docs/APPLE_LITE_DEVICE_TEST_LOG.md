# WZRD.VID Lite Real-Device Test Log

Date: 2026-05-10
Status: pending real-device execution

This is the guided manual test log for WZRD.VID Lite on a physical iPhone or iPad. It is intentionally manual because the simulator smoke can verify the bundled WKWebView surface, but it cannot prove the real iOS document/photo picker and user-facing export/share behavior.

## Current Device Availability

`xcrun devicectl list devices` saw `rivers' iPhone`, model `iPhone 14`, but the device state was `unavailable`.

`xcrun xctrace list devices` also listed `rivers' iPhone (26.3)` under `Devices Offline`.

No real-device pass was executed in this repo session.

## Boundaries

- Do not change desktop renderer/performance behavior during this pass.
- Do not change Lite browser rendering behavior unless a specific blocker is found and isolated.
- Do not add uploads, analytics, backend calls, accounts, remote config, or desktop renderer parity.
- Do not create TestFlight/App Store records from this pass.
- Keep generated `LiteWeb/`, `DerivedData/`, device logs, and test media out of git.

## Preflight

1. Connect the iPhone/iPad by USB or local network.
2. Unlock the device and trust the Mac if prompted.
3. Confirm Developer Mode is enabled on the device if Xcode requires it.
4. Open `apple-lite/WZRDVIDLite.xcodeproj` in Xcode.
5. Select the `WZRDVIDLite` scheme.
6. Select the physical iPhone/iPad destination.
7. Set a local development team and temporary bundle identifier only as needed for a local device build.
8. Build and run from Xcode.
9. Prepare at least:
   - one short local video in Photos
   - one local still image in Photos
   - one local video or image in Files
   - optional local audio file in Files

Useful read-only commands:

```bash
xcrun devicectl list devices
xcrun xctrace list devices
xcodebuild -showdestinations -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite
```

If signing is already configured, a CLI build/install path can be used:

```bash
xcodebuild -project apple-lite/WZRDVIDLite.xcodeproj \
  -scheme WZRDVIDLite \
  -configuration Debug \
  -destination 'platform=iOS,id=DEVICE_ID' \
  -derivedDataPath apple-lite/DerivedData \
  build

xcrun devicectl device install app --device DEVICE_ID \
  apple-lite/DerivedData/Build/Products/Debug-iphoneos/WZRDVIDLite.app
```

## Manual Test Matrix

Record each item as `pass`, `fail`, or `blocked`.

| Area | Test | Result | Notes |
| --- | --- | --- | --- |
| Launch | App opens to bundled WZRD.VID Lite, not a remote website | pending | |
| Offline | With network disabled, app still loads bundled UI | pending | |
| Navigation | Back link is hidden in native shell | pending | |
| Language | Switch to Spanish; main labels update | pending | |
| Language | Switch to Japanese; main labels update and layout remains usable | pending | |
| Language | Switch to Arabic; document direction is structurally RTL | pending | |
| Import | Add Media opens iOS local picker | pending | |
| Import | Import one video from Photos | pending | |
| Import | Import one image from Photos | pending | |
| Import | Import one media file from Files | pending | |
| Duration | 15 second duration changes render button/status copy | pending | |
| Duration | 30 second duration remains usable | pending | |
| Duration | 60 second duration remains usable | pending | |
| Random | Random clip assembly checkbox appears | pending | |
| Random | Random clip assembly can be toggled on/off | pending | |
| Render | 15 second image-only render completes | pending | |
| Render | 15 second video render completes | pending | |
| Render | 15 second random video+photo render completes | pending | |
| Render | Optional 30 second random video+photo render completes | pending | |
| Audio | Optional local audio import arms audio bus | pending | |
| Audio | Optional audio render completes or fails clearly | pending | |
| Export | Download/export control appears after render | pending | |
| Export | Tapping export/download produces a user-accessible file, share sheet, Files save, or another clear handoff | pending | |
| Export | Exported file can be opened or shared outside the app | pending | |
| Privacy | No sign-in, upload, remote config, analytics, or network prompt appears | pending | |
| Stability | No crash during import/render/export loop | pending | |

## Bridge Decision

Native import/share bridge is not needed before TestFlight if all of these are true:

- iOS picker reliably imports local videos and images from Photos and Files.
- Lite can render at least 15 second photo/video/random clips on device.
- The post-render export/download control creates a file the user can actually save, share, or reopen.
- Failure states are understandable and do not trap the user.

Native bridge is needed before TestFlight if any of these are true:

- Add Media cannot reliably import from Photos or Files in WKWebView.
- Rendered blob downloads do not produce a user-accessible file.
- The user cannot share/save/open the rendered clip after export.
- iOS permissions or picker behavior is confusing enough that a native import flow would be required for App Review/user clarity.

Prefer the narrowest bridge:

1. Native export/share bridge for rendered blobs, if import works but export does not.
2. Native import bridge only if WKWebView file input is unreliable with Photos/Files.
3. Avoid a full native renderer rewrite for this decision.

## Decision

Current decision: pending.

Reason: real device was visible to tooling but offline/unavailable, so the manual device pass could not be executed from this session.
