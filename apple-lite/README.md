# WZRD.VID Lite Apple App Groundwork

This folder is the first Apple packaging groundwork for WZRD.VID Lite. It is not an App Store submission, does not change the desktop renderer, and does not replace the static Lite app under `docs/lite/`.

## Current Shape

- Native shell: SwiftUI plus `WKWebView`.
- Web app source of truth: `docs/lite/`, `docs/i18n.js`, and the referenced static assets under `docs/assets/`.
- Bundled runtime: generated locally into `apple-lite/WZRDVIDLite/Resources/LiteWeb/`.
- Network stance: the wrapper loads bundled local files and cancels non-local navigation.
- Product stance: WZRD.VID Lite remains free, local-only, no upload, no backend, no analytics, no accounts, no desktop renderer parity.

## Prepare The Local Web Bundle

Run from the repository root:

```bash
python3 apple-lite/scripts/prepare_lite_web_bundle.py
```

The script copies only the Lite app and the asset folders it references:

- `docs/lite/` -> `apple-lite/WZRDVIDLite/Resources/LiteWeb/lite/`
- `docs/i18n.js` -> `apple-lite/WZRDVIDLite/Resources/LiteWeb/i18n.js`
- `docs/assets/branding/`, `docs/assets/logo/`, and `docs/assets/ui/` -> `apple-lite/WZRDVIDLite/Resources/LiteWeb/assets/`

`LiteWeb/` is generated and ignored by git. Re-run the script whenever the static Lite app changes.

## Xcode Project

This folder includes a first-pass simulator-ready Xcode project at `WZRDVIDLite.xcodeproj`.

Current local defaults:

- Bundle identifier: `com.samhowell.wzrdvid.lite`
- Version: `0.2.0` / build `1`
- Signing: local simulator builds should pass `CODE_SIGNING_ALLOWED=NO` until the Apple Developer team and final bundle ID are ready.
- Bundled web resources: generated during Xcode builds by the `Prepare Lite Web Bundle` build phase.

Open `apple-lite/WZRDVIDLite.xcodeproj` in Xcode for local simulator work. Adjust signing, Team ID, and Bundle ID only when the Apple Developer account/App Store Connect setup is ready.

CLI simulator build:

```bash
xcodebuild -project apple-lite/WZRDVIDLite.xcodeproj \
  -scheme WZRDVIDLite \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  -derivedDataPath apple-lite/DerivedData \
  build CODE_SIGNING_ALLOWED=NO
```

## Simulator Smoke Harness

Run the automated simulator smoke from the repo root:

```bash
python3 apple-lite/scripts/run_simulator_smoke.py
```

The smoke builds the app, installs it on an available iPhone simulator, launches with the debug-only `WZRDVID_LITE_SMOKE=1` harness, and checks:

- bundled Lite UI load
- local file input surface and synthetic local image import through the Lite browser code path
- language switching to Spanish
- 15-second duration control
- Random clip assembly checkbox
- browser render/export surface and generated download link

The smoke harness is compiled into Debug builds only and stays dormant unless `WZRDVID_LITE_SMOKE=1` or `--lite-smoke` is supplied.

## Required Manual Smokes

Use `../docs/APPLE_LITE_DEVICE_TEST_LOG.md` for the guided real-device checklist and bridge decision log.

- Launch with network disabled or blocked.
- Confirm the Lite UI loads from bundled files.
- Confirm language switching works.
- Confirm Add Media opens the local picker.
- Confirm 15/30/60 duration controls work.
- Confirm Random clip assembly appears and can be toggled.
- Attempt a short render with local media.
- Verify the output download/share path. This is the most likely place a native bridge may be needed because WKWebView blob downloads can behave differently than Safari.
- Confirm no external navigation is allowed from inside the wrapper.

## Known Gaps

- Final Apple Developer Team ID, production Bundle ID, App Store Connect record, and signing/export settings are not configured yet.
- No native export/share bridge yet. If the browser download link does not work reliably in WKWebView, add a narrow JavaScript-to-native export bridge instead of changing Lite into a remote or backend app.
- No TestFlight/App Store metadata yet.
- No App Store submission, notarization, signing automation, or release packaging is included here.
