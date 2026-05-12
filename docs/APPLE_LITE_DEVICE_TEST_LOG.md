# WZRD.VID Lite Real-Device Test Log

Date: 2026-05-10
Status: real-device import, added audio, direct Photos save, and video playback pass; random source coverage remains a separate follow-up

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

Signing/provisioning recheck:

- Xcode Signing & Capabilities was set to `Samuel Howell (Personal Team)` for the `WZRDVIDLite` target, with automatic signing enabled.
- `xcodebuild -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -configuration Debug -destination 'platform=iOS,id=00008110-001C4D410C85401E' -derivedDataPath apple-lite/DerivedData build` succeeded.
- Xcode created an Xcode-managed iOS Team Provisioning Profile for `com.samhowell.wzrdvid.lite`.
- `xcrun devicectl device install app --device E3AA485E-F6D0-51A3-848F-9143BA1FC07E apple-lite/DerivedData/Build/Products/Debug-iphoneos/WZRDVIDLite.app` installed the app successfully.
- `xcrun devicectl device info apps --device E3AA485E-F6D0-51A3-848F-9143BA1FC07E` listed `WZRD.VID Lite`, bundle ID `com.samhowell.wzrdvid.lite`, version `0.2.0`, build `1`.
- Launching `com.samhowell.wzrdvid.lite` with the debug smoke harness failed before app startup because iOS reported the profile has not been explicitly trusted by the user.

The developer profile was trusted on-device after the first blocked launch.

Physical-device launch/smoke result:

- `xcrun devicectl device process launch --device E3AA485E-F6D0-51A3-848F-9143BA1FC07E --terminate-existing --console --environment-variables '{"WZRDVID_LITE_SMOKE":"1"}' com.samhowell.wzrdvid.lite` launched the app, ran the Debug smoke harness, and exited with code `0`.
- Smoke result passed with no errors or warnings.
- Smoke capabilities on the physical iPhone WKWebView: `Blob`, `URL.createObjectURL`, `File`, `DataTransfer`, `MediaRecorder`, `canvas.captureStream`, and `navigator.share` were available.
- Smoke checks passed: bundled Lite load, file input surface, export blob surface, Spanish language switching, 15-second duration control, Random clip assembly checkbox, synthetic local file import, random render completion, and generated `wzrdvid-lite-15s` download link readiness.
- A normal non-smoke `devicectl` launch of `com.samhowell.wzrdvid.lite` also succeeded.

Current blocker: added-audio output needs one more manual iPhone retest after the Web Audio fallback. The manual device test confirmed real Photos/Files import, visual preview, and post-bridge download/export worked. It also confirmed rendered/previewed clips were still silent before the Web Audio fallback.

Manual interaction attempt:

- A normal non-smoke launch of `com.samhowell.wzrdvid.lite` succeeded again for this pass.
- Xcode Devices `Take Screenshot` captured the running WZRD.VID Lite UI on the physical iPhone, confirming the native shell was open to bundled Lite rather than a remote website.
- CoreDevice/Xcode tooling available in this session supports launch, install, process inspection, app listing, display info, and screenshots, but it did not expose remote tap/gesture control for the physical iPhone.
- Because the remaining checks require interacting with the iOS Photos/Files picker and tapping the rendered blob download/export link, they still require hand testing on the unlocked iPhone.
- At that point, no native import/share bridge was added because no real Photos/Files import failure or export/share failure had been confirmed.

Manual user results after this handoff:

- Real Photos/Files import worked on the installed iPhone app.
- Visual preview worked with real media.
- Audio did not come through from either added audio or clip audio.
- Tapping Download opened the rendered clip for playback instead of providing a save/share/export handoff, so export failed.
- Decision update: implement a narrow native export/share bridge for rendered blobs. Treat the no-audio result as a separate Apple Lite audio-capture blocker, not as part of the export bridge.

Native export bridge implementation result:

- `docs/lite/app.js` now keeps the latest rendered Blob in memory and exposes a native-only `window.WZRDVID_LITE_EXPORT` handoff.
- `LiteWebView.swift` now installs a local `WKScriptMessageHandler`, intercepts the rendered clip button inside the native shell, writes a temporary local file, and opens the iOS share sheet.
- Simulator smoke passed with `nativeExportBridge: true` and `nativeRenderedClipReady: true`.
- Physical iPhone Debug build, install, and smoke passed with `nativeExportBridge: true` and `nativeRenderedClipReady: true`; the updated app was launched normally after install.
- Manual tapping of the post-bridge share sheet still needs a direct iPhone retest.

Manual user results after native export bridge:

- Download/export worked on the installed iPhone app.
- Added audio and source clip audio were still silent in preview and the downloaded clip.
- Decision update: keep the export bridge. Add a browser-side Web Audio fallback for the explicit Add Audio bus because physical-device smoke shows `Audio.prototype.captureStream` is unavailable while `AudioContext` and `createMediaStreamDestination()` are available.

Added-audio Web Audio fallback implementation result:

- `docs/lite/app.js` now tries `HTMLAudioElement.captureStream()` first, then falls back to `AudioContext.createMediaElementSource()` plus `createMediaStreamDestination()` for the explicit Add Audio bus.
- The fallback also connects to `audioContext.destination` so added audio should be audible during render/preview and captured into the MediaRecorder stream.
- Simulator smoke passed with `audioCaptureStream: false`, `audioContext: true`, `mediaStreamDestination: true`, `audioMode: "webAudio"`, and `audioPipelineReady: true`.
- Physical iPhone Debug build, install, and smoke passed with `audioCaptureStream: false`, `audioContext: true`, `mediaStreamDestination: true`, `audioMode: "webAudio"`, and `audioPipelineReady: true`; the updated app was launched normally after install.
- Manual audible/output audio retest confirmed explicit added audio became audible during render/preview, but it also exposed a new blocker: the preview/render had audio but no visible video, and the share-sheet Save Video path opened a save screen but did not add a video to Photos. Source clip audio remains out of scope for this fallback because Lite samples/seeks source media as visual timeline material rather than preserving source audio.

Direct Photos save bridge implementation result:

- `docs/lite/app.js` now draws the initial canvas frame before starting `canvas.captureStream()` so the MediaRecorder stream is seeded with video before audio playback starts.
- Follow-up retest still produced the `Export needs video` alert. The native validation smoke then reproduced the failure and revealed the root cause: the native export bridge sliced the Blob Data URL at the first comma, but the MP4 MIME type includes a comma inside the codec string (`avc1...,mp4a...`). Swift decoded part of the MIME header as base64, producing an invalid file with no AVFoundation-readable tracks.
- The bridge now slices at the `;base64,` marker, with `lastIndexOf(',')` only as a fallback, so codec strings with commas do not corrupt the native payload.
- The bridge chunk size was reduced for safer WKScriptMessage transfer.
- Lite now exposes native export diagnostics for the latest rendered blob: requested/actual MIME type, blob type, blob size, filename, video track count, audio track count, and selected audio mode.
- The debug smoke harness now requires the native export payload to report a video track and non-trivial blob size.
- `LiteWebView.swift` now validates the temporary rendered movie with `AVURLAsset.loadTracks(withMediaType:)` and saves valid video exports directly to Photos with add-only `PHPhotoLibrary` access instead of depending on the generic share sheet's Save Video action.
- `Info.plist` now includes `NSPhotoLibraryAddUsageDescription` for the direct Save Video path.
- Simulator smoke passed with `blobType: "video/mp4; codecs=avc1.42000a,mp4a.40.2"`, one browser-side video track, one browser-side audio track, native export bridge validation of one AVFoundation video track and one AVFoundation audio track, nonzero blob size, `audioMode: "webAudio"`, and all existing Lite smoke checks passing.
- Physical iPhone Debug build, install, and smoke passed with the same MP4/browser-side/native-validation video-track/audio-track diagnostics; the updated app was launched normally afterward.
- Manual hand retests confirmed added music, direct Photos save/download, and saved video playback now work. Source clip audio remains out of scope for the current Lite visual timeline.

Manual user results after native MP4 payload fix:

- Added music worked.
- Download saved the rendered video as expected.
- Saved video played with video.
- Remaining issue: the saved video only showed a small section from a GIF and did not visibly include the other selected photo/video media.

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
| Launch | App opens to bundled WZRD.VID Lite, not a remote website | pass | Automated physical-device smoke loaded bundled Lite; normal non-smoke launch also succeeded. |
| Offline | With network disabled, app still loads bundled UI | pending | Needs hand test with network disabled on device. |
| Navigation | Back link is hidden in native shell | pending | Needs visual hand check on device. |
| Language | Switch to Spanish; main labels update | pass | Automated device smoke switched to Spanish and verified translated text. |
| Language | Switch to Japanese; main labels update and layout remains usable | pending | Needs hand test on device. |
| Language | Switch to Arabic; document direction is structurally RTL | pending | Needs hand test on device. |
| Import | Add Media opens iOS local picker | pass | Manual user test confirmed real Photos/Files import works. |
| Import | Import one video from Photos | pass | Manual user test confirmed real Photos/Files import works; exact media split was not independently observed by Codex. |
| Import | Import one image from Photos | pass | Manual user test confirmed real Photos/Files import works; exact media split was not independently observed by Codex. |
| Import | Import one media file from Files | pass | Manual user test confirmed real Photos/Files import works. |
| Duration | 15 second duration changes render button/status copy | pass | Automated device smoke verified 15-second control. |
| Duration | 30 second duration remains usable | pending | Needs hand test on device. |
| Duration | 60 second duration remains usable | pending | Needs hand test on device. |
| Random | Random clip assembly checkbox appears | pass | Automated device smoke found and toggled the checkbox. |
| Random | Random clip assembly can be toggled on/off | pass | Automated device smoke toggled it on. |
| Render | 15 second image-only render completes | pass | Automated device smoke rendered with a synthetic local image through MediaRecorder/canvas. |
| Render | 15 second video render completes | pending | Needs hand test with real local video. |
| Render | 15 second random video+photo render completes | pending | Needs hand test with real local video/photo media. |
| Render | Optional 30 second random video+photo render completes | pending | Needs hand test with real local video/photo media. |
| Audio | Optional local audio import arms audio bus | pass | Manual user retest after Web Audio fallback heard added music during preview/render. |
| Audio | Optional audio render completes or fails clearly | pass | Added audio is audible through Web Audio in real-device manual testing. Source clip audio remains out of scope for Lite's visual timeline. |
| Export | Download/export control appears after render | pass | Automated device smoke verified a generated blob download link. |
| Export | Tapping export/download produces a user-accessible file, share sheet, Files save, or another clear handoff | pass | Generic share-sheet Save Video failed earlier, so the native wrapper now saves validated video directly to Photos. Manual retest confirmed saved video appears and plays. |
| Export | Exported file can be opened or shared outside the app | pass | Manual user retest confirmed Download saved a video and the saved video played. |
| Privacy | No sign-in, upload, remote config, analytics, or network prompt appears | pass | Automated smoke completed without sign-in/upload/network prompt; static no-network boundary unchanged. |
| Stability | No crash during import/render/export loop | pass | Automated smoke exited cleanly after import/render/download-link readiness. |

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

Current decision: native export/save bridge is needed and has been implemented for rendered blobs. Native import bridge is not needed based on this manual test.

Reason: build, install, launch, bundled Lite load, synthetic local import, language switching, random rendering, generated download-link readiness, real Photos/Files import, added music, direct Photos save, and saved video playback pass on the physical iPhone. The browser blob download handoff failed by opening rendered clips for playback, and the share-sheet Save Video path later failed to add a video to Photos after added-audio playback was fixed. The narrow bridge now intercepts the rendered blob, validates that the generated movie has a video track, and saves directly to Photos with add-only Photos access. Source clip audio is not implemented for Lite's visual source timeline and remains future work.
