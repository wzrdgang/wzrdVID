# WZRD.VID Lite Apple App Research

Date: 2026-05-10

This began as a research memo for post-D-U-N-S work. The repo now also includes first-pass Apple Lite packaging groundwork under `apple-lite/`. It does not create an App Store submission, change release packaging, or change WZRD.VID Lite browser behavior.

## Recommendation

Start with a free WZRD.VID Lite app built as a small native shell around bundled local Lite assets. The first practical path is a SwiftUI app with a `WKWebView` that loads the static Lite experience from the app bundle, plus native file import/export affordances only where the browser runtime needs platform help.

Do not try to ship the desktop renderer, bundled ffmpeg, or full desktop feature parity in this first Apple app. The product promise should stay narrow: local-only WZRD.VID Lite, browser/native-lite rendering, no uploads, no accounts, no analytics, no remote config, and no subscription.

## Current Apple Requirements Checked

- Apple Developer Program organization enrollment requires legal entity status and a D-U-N-S Number for organization accounts. Apple says the organization website must be publicly available and associated with the organization domain. Source: <https://developer.apple.com/help/account/membership/program-enrollment/>
- App Review guideline 4.2 says apps should include features, content, and UI beyond a repackaged website. A Lite wrapper needs app-like local media utility, not just a remote webpage. Source: <https://developer.apple.com/app-store/review/guidelines/>
- Starting April 28, 2026, uploaded iOS/iPadOS apps need to be built with the iOS and iPadOS 26 SDK or later. Source: <https://developer.apple.com/app-store/submitting/>
- Before uploading a build, App Store Connect needs an app record with platform, app name, primary language, bundle ID, SKU, and access settings. Source: <https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app/>
- App information includes fields such as localized name, subtitle, privacy policy URL, bundle ID, SKU, age rating, primary language, and category. Apple states privacy policy URL is required for iOS and macOS apps. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/app-information>
- App privacy details must accurately disclose collected data and tracking. If the app has no analytics, accounts, backend calls, or third-party tracking SDKs, the implementation should preserve that before claiming no data collection. Source: <https://developer.apple.com/app-store/app-privacy-details/>
- `WKWebView` supports loading local files, and `loadFileURL(_:allowingReadAccessTo:)` grants read access to a file or directory of bundled web content. Sources: <https://developer.apple.com/documentation/webkit/wkwebview> and <https://developer.apple.com/documentation/webkit/wkwebview/loadfileurl(_:allowingreadaccessto:)>

## Feasible Paths

### Path A - Native shell around bundled Lite assets

- Bundle `docs/lite/` and shared static assets into an iOS/iPadOS app.
- Load `index.html` with `WKWebView.loadFileURL(..., allowingReadAccessTo: bundledLiteDirectory)`.
- Keep all media selected by the user local to the device.
- Use native document/photo import and share/export only if the bundled web runtime cannot handle the file and download flows reliably.
- Best fit for v0.2.0 because it preserves the existing Lite surface while adding enough native app structure to avoid a thin remote website wrapper.

### Path B - Remote website wrapper

- Load `https://wzrdvid.com/lite/` in a WebView.
- This is not recommended. It is more likely to look like a repackaged website under App Review guideline 4.2, and it weakens the local bundled/no-remote-config story.

### Path C - Native rewrite

- Rebuild Lite rendering as native Swift/Metal/AVFoundation.
- This may become the best long-term Apple-quality app, but it is too large for the first Apple/Lite rollout and risks becoming a separate renderer project.

## Implementation Checklist After D-U-N-S

1. Finish Apple Developer organization enrollment and confirm legal seller name.
2. Decide first platform target: iPhone/iPad first; macOS/Catalyst later only if the Lite shell tests well.
3. Create Bundle ID and App Store Connect app record for `WZRD.VID Lite`.
4. Build a SwiftUI `WKWebView` shell that loads bundled static Lite files, not the public website.
5. Add native import/export bridges only if required for reliable local media access and output sharing.
6. Verify the app runs without network access and that no analytics, accounts, backend calls, tracking SDKs, or remote config exist.
7. Test local file import, 15/30/60 duration controls, random clip assembly, language switching, output generation, and export/share on real devices.
8. Prepare privacy policy text that accurately describes local-only processing and any file permissions.
9. Fill App Store Connect metadata, privacy details, age rating, screenshots, and accessibility support.
10. Submit an internal TestFlight build before public review.

## Groundwork Added

- `apple-lite/WZRDVIDLite/App/` contains starter SwiftUI/WKWebView shell sources.
- `apple-lite/WZRDVIDLite.xcodeproj` contains a simulator-ready app target using the current starter sources.
- `apple-lite/scripts/prepare_lite_web_bundle.py` prepares an ignored `LiteWeb/` bundle from `docs/lite/`, `docs/i18n.js`, and referenced static assets.
- `apple-lite/scripts/run_simulator_smoke.py` builds the project, installs the app on an available iPhone simulator, and launches a debug-only WKWebView smoke harness for bundled Lite load, local import surface, language switching, random clip rendering, and download-link readiness.
- `apple-lite/README.md` documents the Xcode project, target setup, local-only boundaries, and required simulator/device smokes.
- `docs/APPLE_LITE_DEVICE_TEST_LOG.md` tracks the guided real-device manual test and native import/share bridge decision.
- No signing state, Team ID, App Store Connect app record, TestFlight build, or native export bridge has been added yet.

## Product Boundaries

- Name: WZRD.VID Lite.
- Price: free.
- Promise: local-only media transformation on device.
- Do not promise desktop renderer parity.
- Do not add accounts, uploads, analytics, subscriptions, backend services, AI translation, remote config, or desktop ffmpeg complexity.
- Keep the desktop performance hardening frozen while Apple Lite packaging is being tested, unless a v0.2.0 blocker appears.
