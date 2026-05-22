# WZRD.VID Lite App Icon and Screenshot Asset Plan

Date: 2026-05-22
Status: asset plan plus implemented AppIcon catalog and screenshot-capture workflow; no screenshots, signing IDs, Bundle IDs, App Store Connect records, release assets, GitHub Pages config, or runtime behavior changed

This plan prepares Apple Lite asset work while AMPYX LLC Apple Developer organization enrollment is pending. It records the current Xcode asset state, identifies repo-safe brand source candidates, captures the implemented AppIcon result, and separates work that can proceed now from work that should wait for the final AMPYX Team ID and production Bundle ID.

## Current Apple Lite Asset State

- `apple-lite/WZRDVIDLite/App/Assets.xcassets/AppIcon.appiconset/` is generated and committed for the Apple Lite target.
- The Xcode project sets `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon` for Debug and Release and includes `Assets.xcassets` as a target resource.
- `Info.plist` has no `CFBundleIcons` / app-icon dictionary. `CFBundleIdentifier` is still `$(PRODUCT_BUNDLE_IDENTIFIER)`.
- `Info.plist` uses an empty `UILaunchScreen` dictionary. There is no branded launch screen asset or launch storyboard yet.
- No screenshot files or sample media are committed.
- Current local/dev Bundle ID evidence remains `com.samhowell.wzrdvid.lite`; this should not be treated as the production identity.
- Preferred production Bundle ID candidate remains `com.worky.wzrdvid.lite`, unless Apple/account setup later requires a different AMPYX-controlled reverse-DNS identity.
- Current repo team setting evidence remains `DEVELOPMENT_TEAM = JKSWZ8682X`; the final AMPYX organization Team ID must replace or confirm it after enrollment.

## Apple Source Notes

- Apple says the app icon is used across the Home Screen, search results, notifications, system settings, share sheets, and TestFlight, and that icons can be created with Icon Composer or added to an Xcode asset catalog before uploading a build to App Store Connect. Source: <https://developer.apple.com/help/app-store-connect/manage-app-information/add-an-app-icon/>
- App Store Connect currently requires one to ten screenshots in `.jpeg`, `.jpg`, or `.png` format. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications>
- For the current screenshot matrix, a 6.9-inch iPhone screenshot set satisfies current iPhone-first coverage; 6.5-inch is required if 6.9-inch screenshots are not provided. If the app runs on iPad, 13-inch iPad screenshots are required. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications>

## Existing Brand Source Candidates

Primary candidate:

- `assets/branding/wzrdvid_app_icon_source.png`
  - 1024 x 1024 PNG.
  - Current branding source of truth for generated desktop app icon output.
  - Best repo-safe starting point for an Apple Lite icon source decision.

Secondary candidates:

- `assets/branding/wzrdvid_compact.png`
  - 1024 x 1024 PNG.
  - Useful if the primary icon source needs a more compact mark.
- `assets/branding/wzrdvid_compact_dark.png`
  - 1024 x 1024 PNG.
  - Useful for dark-background tests, but final App Store icon should not rely on transparency.
- `assets/logo/wzrdvid_logo_square.png`
  - 1024 x 1024 PNG.
  - Compatibility fallback if the branding source is rejected after small-size previews.

Not recommended as direct Apple Lite source assets:

- `assets/wzrd_vid.icns`, `assets/wzrd_vid_icon.png`, and `assets/wzrd_vid.iconset/*`: generated desktop/macOS icon outputs, not an intentional iOS asset catalog.
- Wide wordmarks, banners, favicons, and website-specific assets: likely to be unreadable or incorrectly framed at small iOS icon sizes.

Current candidate caveat:

- The 1024 x 1024 PNG candidates currently have alpha. The Apple Lite app-icon implementation should flatten the selected source onto an intentional opaque background before App Store validation, rather than relying on transparent edges.

## Temporary Preview Findings

Preview date: 2026-05-22

Temporary preview outputs were generated under `/tmp` only. No generated PNGs, icon files, `.appiconset`, Apple Lite source assets, release assets, signing settings, Bundle IDs, App Store Connect records, GitHub Pages config, or runtime files were committed.

Source comparison:

- `assets/branding/wzrdvid_app_icon_source.png` remains the recommended source. It has the clearest source-of-truth relationship to the current desktop icon workflow and survives small iOS-style sizes as well as or better than the alternatives.
- `assets/branding/wzrdvid_compact.png` and `assets/logo/wzrdvid_logo_square.png` are viable alternates, but the preview did not show a meaningful advantage over the primary source.
- `assets/branding/wzrdvid_compact_dark.png` is not recommended for the first Apple Lite icon pass because it loses too much contrast at 20, 29, and 40 px contexts.

Visual findings:

- All inspected 1024 x 1024 candidates have alpha and need an intentional opaque background flatten before App Store validation.
- The CRT/screen silhouette and slash mark remain recognizable at the smallest preview sizes; the `wzrd VID` lettering is not meaningfully readable at 20 or 29 px and becomes useful only around the larger iOS contexts.
- Treat tiny lettering as texture, not as the primary recognition mechanism. If the production direction requires readable text at notification/settings sizes, the icon should be simplified or the lettering should be enlarged.
- The current art fills the square closely enough that the implemented `AppIcon.appiconset` pass tested a small safe-area inset across 4%, 6%, and 8%; the committed catalog uses 6% so iOS corner masking does not make the frame feel clipped.
- The preview rendered the requested 83.5 px context as 84 px because PNG dimensions are integer pixels.

## Recommended Icon Source Workflow For Future Revisions

1. Choose and approve the source master before generating files. Recommended default: `assets/branding/wzrdvid_app_icon_source.png`.
2. Create a scratch preview matrix first, outside committed source or in an ignored temporary folder, showing the icon at 20, 29, 40, 60, 76, 83.5, 167, 180, and 1024 pixel contexts.
3. Flatten the selected source to an opaque 1024 x 1024 master with the final AMPYX/WZRD visual treatment and test a 4-8% safe-area inset before finalizing revised generated slots.
4. Keep future icon revisions in the Apple Lite-specific asset catalog at `apple-lite/WZRDVIDLite/App/Assets.xcassets/AppIcon.appiconset/`.
5. Add revised generated `AppIcon.appiconset` files through Xcode or a deterministic script with a valid `Contents.json`, then keep the Apple Lite target build setting pointed at `AppIcon`.
6. Keep this separate from the desktop icon generator. Do not overwrite `assets/wzrd_vid.*` or the existing macOS iconset.
7. Validate with Xcode build/archive checks after AMPYX signing and the production Bundle ID are configured.

Manual `.appiconset` slot checklist if not using Xcode/Icon Composer automation:

- iPhone notification/settings/Spotlight/app slots: 20pt, 29pt, 40pt, 60pt at the required 2x/3x scales.
- iPad notification/settings/Spotlight/app slots: 20pt, 29pt, 40pt at the required 1x/2x scales, plus 76pt at 2x for current iPad app icon coverage. The 76pt 1x slot is legacy-only for this iOS 17+ target and is intentionally omitted from the implemented catalog.
- iPad Pro app slot: 83.5pt at 2x.
- App Store marketing slot: 1024 x 1024.

## Implemented AppIcon Catalog

Implementation date: 2026-05-22

Implemented path:

`apple-lite/WZRDVIDLite/App/Assets.xcassets/AppIcon.appiconset/`

Implementation summary:

- Source: `assets/branding/wzrdvid_app_icon_source.png`.
- Chosen inset: 6%, after comparing 4%, 6%, and 8% temporary preview candidates.
- Master treatment: opaque dark 1024 x 1024 PNG derived from the source image, with no alpha.
- Generated slots: 17 PNG slots plus `Contents.json`.
- Xcode project change: added `Assets.xcassets` as an Apple Lite target resource and set `ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon` for both Debug and Release.
- Omitted slot: iPad `76x76@1x`, because Xcode 26 reports that slot only applies to iPad apps targeting releases before iOS 10. The Apple Lite deployment target remains iOS 17.0.
- Scope not changed: no signing ID, Bundle ID, App Store Connect record, App Store/DUNS account metadata, GitHub Release asset, GitHub Pages config, Info.plist privacy string, Swift runtime behavior, Lite runtime behavior, or desktop renderer behavior changed.

Generated slot set:

- iPhone: 20x20 @2x/@3x, 29x29 @2x/@3x, 40x40 @2x/@3x, 60x60 @2x/@3x.
- iPad: 20x20 @1x/@2x, 29x29 @1x/@2x, 40x40 @1x/@2x, 76x76 @2x, 83.5x83.5 @2x.
- Marketing: 1024x1024 @1x.

## Screenshot Capture Checklist

Use clean sample media and production-like app state. Do not show personal files, account identifiers, private paths, email addresses, D-U-N-S values, or Apple account screens.

- Launch/import screen: WZRD.VID Lite open with Add Media visible.
- Selected media state: at least one local image or video selected and visible in the Lite media list.
- Render settings: duration, quality, random assembly, and optional audio controls visible.
- Rendering/export state: render progress, preview, or completed export controls visible.
- Saved output result: rendered output saved to Photos after the user taps Download.
- Support/privacy reference readiness: use the live `https://wzrdvid.com/support/` and `https://wzrdvid.com/privacy/` routes in App Store prep once final AMPYX contact details are approved.

Recommended screenshot sets:

- iPhone 6.9-inch display set in portrait.
- iPad 13-inch display set in portrait if WZRD.VID Lite remains available on iPad.
- Optional landscape captures only if the final UI looks materially better and does not hide core controls.
- Optional app preview video only after the still screenshot package is stable.

## Sample Media Requirements

- Use generated, licensed, or intentionally repo-safe media only.
- Include one short video clip, one still image, and one optional local audio clip.
- Keep media visually distinctive enough to show the Lite render result, but avoid faces, private locations, license ambiguity, private documents, and visible personal metadata.
- For screenshot consistency, use the same sample set for simulator and physical-device captures.
- Do not imply full desktop parity. If audio appears in screenshots, show the explicit audio input path; source clip audio from visual timeline media remains future work.

## Temporary Screenshot Sample Media

Sample date: 2026-05-22

Temporary repo-safe sample media was generated under `/tmp/wzrdvid-lite-screenshot-sample-20260522/` only. Do not commit these generated files unless a later prompt explicitly approves a committed screenshot-asset package.

Generated files:

- `/tmp/wzrdvid-lite-screenshot-sample-20260522/wzrdvid-lite-sample-video.mp4`
  - 4 seconds, 1280 x 720, H.264, 30 fps, no embedded audio.
- `/tmp/wzrdvid-lite-screenshot-sample-20260522/wzrdvid-lite-sample-still.png`
  - 1600 x 1200 PNG.
- `/tmp/wzrdvid-lite-screenshot-sample-20260522/wzrdvid-lite-sample-audio.m4a`
  - 4 seconds, AAC mono, 44.1 kHz.

Metadata/string safety checks found no exact D-U-N-S number, personal names, current local/dev Bundle ID, current team ID, or private `/Users` paths in the generated media.

The still and video were successfully imported into the booted iPhone 17 simulator Photos library with `xcrun simctl addmedia`. Simulator screenshot capture was also verified by writing `/tmp/wzrdvid-lite-screenshot-sample-20260522/screenshots/tooling-smoke-iphone17.png`.

## Simulator Screenshot Capture Workflow

Current local feasibility:

- iPhone 6.9-inch set: feasible from current tooling with the available `iPhone 17 Pro Max` simulator.
- iPad 13-inch set: feasible from current tooling with the available `iPad Pro 13-inch (M5)` simulator; `iPad Air 13-inch (M3)` is also available.
- Capture method: use the existing Apple Lite app and manual Simulator interaction, then write screenshots to `/tmp`. Do not add runtime hooks or force screenshot states in the Lite runtime.
- Current local/dev launch identifier: `com.samhowell.wzrdvid.lite`, used only as current repo evidence for simulator launch. The final production Bundle ID direction remains `com.worky.wzrdvid.lite` unless Apple/account setup requires a different AMPYX-controlled namespace.

Suggested iPhone 6.9-inch dry-run:

```bash
export SAMPLE_DIR=/tmp/wzrdvid-lite-screenshot-sample-20260522
export SHOT_DIR=/tmp/wzrdvid-lite-screenshots-20260522/iphone-69
mkdir -p "$SHOT_DIR"

python3 apple-lite/scripts/prepare_lite_web_bundle.py
xcodebuild -project apple-lite/WZRDVIDLite.xcodeproj \
  -scheme WZRDVIDLite \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max' \
  -derivedDataPath apple-lite/DerivedData \
  build CODE_SIGNING_ALLOWED=NO

DEVICE="$(xcrun simctl list devices available | awk -F'[()]' '/iPhone 17 Pro Max/ {print $2; exit}')"
xcrun simctl boot "$DEVICE" || true
xcrun simctl bootstatus "$DEVICE" -b
xcrun simctl install "$DEVICE" apple-lite/DerivedData/Build/Products/Debug-iphonesimulator/WZRDVIDLite.app
xcrun simctl addmedia "$DEVICE" \
  "$SAMPLE_DIR/wzrdvid-lite-sample-video.mp4" \
  "$SAMPLE_DIR/wzrdvid-lite-sample-still.png"
xcrun simctl launch --terminate-running-process "$DEVICE" com.samhowell.wzrdvid.lite
xcrun simctl io "$DEVICE" screenshot "$SHOT_DIR/01-launch-import.png"
```

Suggested iPad 13-inch dry-run: repeat the same flow with `-destination 'platform=iOS Simulator,name=iPad Pro 13-inch (M5)'`, a matching `DEVICE` selector, and an iPad-specific output directory such as `/tmp/wzrdvid-lite-screenshots-20260522/ipad-13/`.

Manual capture states:

- Launch/import screen: capture immediately after normal app launch, before selecting media.
- Selected media state: use Add Media and choose the imported sample video or still from Photos, then capture the populated media state.
- Render settings state: set duration/quality/random assembly and optional audio controls, then capture before rendering.
- Rendering/export or completed render state: start the render and capture progress if timing permits, or capture the completed preview with Download available.
- Saved output/result state: tap Download and capture the saved-result state if the simulator grants Photos save permission and the output appears in Photos; otherwise document this as a simulator limitation and rely on the existing native export smoke plus a later physical-device screenshot pass.

Optional audio note: the generated `.m4a` is available under `/tmp`, but `simctl addmedia` is intended for Photos media. Use the audio clip only if it can be made available through the simulator Files picker without changing runtime behavior, or skip audio in the first screenshot set.

## Can Proceed Before AMPYX Enrollment

- Refine future icon revisions with temporary preview matrices before changing the committed AppIcon catalog.
- Regenerate or refine clean sample media for screenshots under `/tmp`.
- Dry-run simulator screenshots for layout and content only, using the existing app and generated sample media.
- Keep validating the live support/privacy routes as App Store prep references.
- Decide whether the empty `UILaunchScreen` dictionary is acceptable for first TestFlight or whether a minimal branded launch screen should be added later.

## Must Wait For AMPYX Team ID and Production Bundle ID

- Register or confirm the final production Bundle ID, preferably `com.worky.wzrdvid.lite` unless Apple/account setup requires a different AMPYX-controlled namespace.
- Replace or confirm the final AMPYX Team ID in signing settings.
- Create the App Store Connect app record.
- Run final physical-device install and TestFlight archive/upload validation.
- Capture final screenshots from a production-signed build if the simulator-only captures do not reflect the final app identity or behavior.
- Attach final App Store icon/build assets to App Store Connect.
- Submit anything to TestFlight external testing or App Review.

## Validation Checklist For Future Asset Passes

- Confirm only Apple Lite icon/launch assets and directly related project references changed.
- Confirm desktop renderer, Lite runtime, Apple Lite runtime, signing IDs, Bundle IDs, GitHub Releases, GitHub Pages config, and App Store/DUNS account metadata remain unchanged unless explicitly authorized.
- Run the existing Lite and desktop syntax checks.
- Run `xcodebuild` target checks after the asset catalog exists.
- Run the Apple Lite simulator smoke harness after rebuilding the LiteWeb bundle.
- Re-check `git diff --check` and staged diff whitespace before commit.

## Known Gaps

- Apple Lite app icon assets are now generated and committed, but final archive/App Store Connect validation under AMPYX signing remains pending.
- No screenshots were captured or committed in this pass.
- No launch screen asset was added.
- No AMPYX signing, production Bundle ID, App Store Connect, TestFlight archive, release asset, GitHub Pages config, or runtime behavior changed.
