# WZRD.VID Lite Real-Device Test Log

Date: 2026-05-10
Status: blocked before real-device app launch by signing/provisioning

This is the guided manual test log for WZRD.VID Lite on a physical iPhone or iPad. It is intentionally manual because the simulator smoke can verify the bundled WKWebView surface, but it cannot prove the real iOS document/photo picker and user-facing export/share behavior.

## Current Device Availability

Initial checks saw the previously paired `rivers' iPhone`, model `iPhone 14`, but the device state was `unavailable`.

Follow-up checks after the phone was connected by USB found two device records:

- Stale CoreDevice record: `rivers' iPhone`, iOS `26.3`, identifier `47F38D01-B5D9-5F4F-8976-808134B26783`, still `unavailable`.
- USB-connected physical record: `iPhone14`, iOS `26.4.2`, UDID `00008110-001C4D410C85401E`, reported as available by `xcrun xcdevice list`.

Evidence collected:

- `xcrun devicectl list devices --timeout 30` still showed `rivers' iPhone` as `unavailable`.
- `xcrun xctrace list devices` listed `rivers' iPhone (26.3)` under `Devices Offline`.
- `xcrun devicectl device info details --device 47F38D01-B5D9-5F4F-8976-808134B26783` reported `developerModeStatus: disabled`, `ddiServicesAvailable: false`, and `tunnelState: unavailable` for the stale record.
- `xcrun devicectl manage pair --device 47F38D01-B5D9-5F4F-8976-808134B26783 --timeout 30` failed with CoreDevice error `4000`.
- `ioreg -p IOUSB -l -w0` showed a physical `iPhone` USB device.
- `xcrun xcdevice list --timeout 10` showed USB device `iPhone14` as available with UDID `00008110-001C4D410C85401E`.
- `xcodebuild -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -configuration Debug -destination 'platform=iOS,id=00008110-001C4D410C85401E' -derivedDataPath apple-lite/DerivedData build` did not build because Xcode reported: `Developer Mode disabled To use iPhone14 for development, enable Developer Mode in Settings -> Privacy & Security.`

No real-device WZRD.VID Lite app launch, import, render, random clip, or export/share pass was executed from that attempt because Xcode could not use the physical phone as a development destination.

Latest recheck after Developer Mode was enabled:

- `xcrun devicectl list devices --timeout 30` showed `iPhone14`, model `iPhone 14`, as `connected`.
- `xcodebuild -showdestinations -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -destination-timeout 30` listed the physical destination `{ platform:iOS, arch:arm64, id:00008110-001C4D410C85401E, name:iPhone14 }`.
- `xcrun devicectl device info details --device E3AA485E-F6D0-51A3-848F-9143BA1FC07E` reported `developerModeStatus: enabled`, `ddiServicesAvailable: true`, `transportType: wired`, `tunnelState: connected`, plus install and launch capabilities.
- `xcodebuild -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -configuration Debug -destination 'platform=iOS,id=00008110-001C4D410C85401E' -derivedDataPath apple-lite/DerivedData -allowProvisioningUpdates DEVELOPMENT_TEAM=3367V5767A build` failed before install with signing/provisioning errors: `No Account for Team "3367V5767A"` and `No profiles for 'com.samhowell.wzrdvid.lite' were found`.
- `~/Library/MobileDevice/Provisioning Profiles` contained zero `.mobileprovision` files.

Current blocker: the iPhone is connected and Developer Mode is enabled, but the Mac/Xcode account provisioning state is not ready to sign and install the app on the device.

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
| Launch | App opens to bundled WZRD.VID Lite, not a remote website | blocked | Device is now eligible, but signing/provisioning blocks build/install. |
| Offline | With network disabled, app still loads bundled UI | blocked | Blocked before app install. |
| Navigation | Back link is hidden in native shell | blocked | Blocked before app install. |
| Language | Switch to Spanish; main labels update | blocked | Blocked before app install. |
| Language | Switch to Japanese; main labels update and layout remains usable | blocked | Blocked before app install. |
| Language | Switch to Arabic; document direction is structurally RTL | blocked | Blocked before app install. |
| Import | Add Media opens iOS local picker | blocked | Blocked before app install. |
| Import | Import one video from Photos | blocked | Blocked before app install. |
| Import | Import one image from Photos | blocked | Blocked before app install. |
| Import | Import one media file from Files | blocked | Blocked before app install. |
| Duration | 15 second duration changes render button/status copy | blocked | Blocked before app install. |
| Duration | 30 second duration remains usable | blocked | Blocked before app install. |
| Duration | 60 second duration remains usable | blocked | Blocked before app install. |
| Random | Random clip assembly checkbox appears | blocked | Blocked before app install. |
| Random | Random clip assembly can be toggled on/off | blocked | Blocked before app install. |
| Render | 15 second image-only render completes | blocked | Blocked before app install. |
| Render | 15 second video render completes | blocked | Blocked before app install. |
| Render | 15 second random video+photo render completes | blocked | Blocked before app install. |
| Render | Optional 30 second random video+photo render completes | blocked | Blocked before app install. |
| Audio | Optional local audio import arms audio bus | blocked | Blocked before app install. |
| Audio | Optional audio render completes or fails clearly | blocked | Blocked before app install. |
| Export | Download/export control appears after render | blocked | Blocked before app install. |
| Export | Tapping export/download produces a user-accessible file, share sheet, Files save, or another clear handoff | blocked | Blocked before app install. |
| Export | Exported file can be opened or shared outside the app | blocked | Blocked before app install. |
| Privacy | No sign-in, upload, remote config, analytics, or network prompt appears | blocked | Blocked before app install. |
| Stability | No crash during import/render/export loop | blocked | Blocked before app install. |

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

Current decision: blocked/inconclusive.

Reason: the connected USB iPhone is now visible to Xcode/CoreDevice with Developer Mode enabled, but local signing/provisioning blocks build/install. No import/export blocker was observed, so there is still no evidence that a native import/share bridge is needed before TestFlight. The bridge decision remains pending until WZRD.VID Lite can be installed and launched on a physical device.
