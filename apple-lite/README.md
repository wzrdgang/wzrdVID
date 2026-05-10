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

## Create The Xcode Project

Until the Apple Developer account, Team ID, and final Bundle ID are ready, create the Xcode project manually:

1. Open Xcode.
2. Create a new iOS App project named `WZRDVIDLite`.
3. Use Swift and SwiftUI.
4. Set the bundle identifier to the final approved identifier, or temporarily use `com.samhowell.wzrdvid.lite` for local simulator testing.
5. Add the Swift files from `apple-lite/WZRDVIDLite/App/` to the app target.
6. Use `apple-lite/WZRDVIDLite/App/Info.plist` as starter metadata, adjusting signing/team/version fields in Xcode as needed.
7. Add `apple-lite/WZRDVIDLite/Resources/LiteWeb/` as a folder reference to the app target. It must be a folder reference so relative paths such as `../i18n.js` and `../assets/ui/...` continue to work.
8. Build and run on iPhone/iPad Simulator.

## Required Manual Smokes

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

- No committed `.xcodeproj` yet. Keep that for the post-D-U-N-S phase when the final Team ID and Bundle ID are known.
- No native export/share bridge yet. If the browser download link does not work reliably in WKWebView, add a narrow JavaScript-to-native export bridge instead of changing Lite into a remote or backend app.
- No TestFlight/App Store metadata yet.
- No App Store submission, notarization, signing automation, or release packaging is included here.
