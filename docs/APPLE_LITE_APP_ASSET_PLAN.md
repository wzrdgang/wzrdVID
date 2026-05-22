# WZRD.VID Lite App Icon and Screenshot Asset Plan

Date: 2026-05-22
Status: docs-only implementation plan; no icon files, screenshots, signing IDs, Bundle IDs, App Store Connect records, release assets, GitHub Pages config, or runtime behavior changed

This plan prepares the next Apple Lite asset work while AMPYX LLC Apple Developer organization enrollment is pending. It records the current Xcode asset state, identifies repo-safe brand source candidates, and separates work that can proceed now from work that should wait for the final AMPYX Team ID and production Bundle ID.

## Current Apple Lite Asset State

- `apple-lite/` currently has no `Assets.xcassets`, `.appiconset`, `AppIcon.appiconset`, `LaunchScreen.storyboard`, `.icon`, or `.iconset` asset container.
- The Xcode project has no `ASSETCATALOG_COMPILER_APPICON_NAME` or asset-catalog build setting for the Apple Lite target.
- `Info.plist` has no `CFBundleIcons` / app-icon dictionary. `CFBundleIdentifier` is still `$(PRODUCT_BUNDLE_IDENTIFIER)`.
- `Info.plist` uses an empty `UILaunchScreen` dictionary. There is no branded launch screen asset yet.
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
- The current art fills the square closely enough that a future `AppIcon.appiconset` pass should test a small safe-area inset, roughly 4-8%, before final generation so iOS corner masking does not make the frame feel clipped.
- The preview rendered the requested 83.5 px context as 84 px because PNG dimensions are integer pixels.

## Recommended Icon Source Workflow

1. Choose and approve the source master before generating files. Recommended default: `assets/branding/wzrdvid_app_icon_source.png`.
2. Create a scratch preview matrix first, outside committed source or in an ignored temporary folder, showing the icon at 20, 29, 40, 60, 76, 83.5, 167, 180, and 1024 pixel contexts.
3. Flatten the selected source to an opaque 1024 x 1024 master with the final AMPYX/WZRD visual treatment and test a 4-8% safe-area inset before finalizing the generated slots.
4. Only after approval, add an Apple Lite-specific asset catalog under the Apple Lite target, for example `apple-lite/WZRDVIDLite/App/Assets.xcassets/AppIcon.appiconset/`.
5. Add the generated `AppIcon.appiconset` through Xcode or a deterministic script with a valid `Contents.json`, then set the Apple Lite target build setting to use `AppIcon`.
6. Keep this separate from the desktop icon generator. Do not overwrite `assets/wzrd_vid.*` or the existing macOS iconset.
7. Validate with Xcode build/archive checks after AMPYX signing and the production Bundle ID are configured.

Manual `.appiconset` slot checklist if not using Xcode/Icon Composer automation:

- iPhone notification/settings/Spotlight/app slots: 20pt, 29pt, 40pt, 60pt at the required 2x/3x scales.
- iPad notification/settings/Spotlight/app slots: 20pt, 29pt, 40pt, 76pt at the required 1x/2x scales.
- iPad Pro app slot: 83.5pt at 2x.
- App Store marketing slot: 1024 x 1024.

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

## Can Proceed Before AMPYX Enrollment

- Approve the icon source direction and produce temporary preview matrices.
- Draft a deterministic icon-generation script or Xcode asset-catalog patch in a separate implementation pass.
- Prepare clean sample media for screenshots.
- Dry-run simulator screenshots for layout and content only.
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

## Validation Checklist For The Future Icon Pass

- Confirm only Apple Lite icon/launch assets and directly related project references changed.
- Confirm desktop renderer, Lite runtime, Apple Lite runtime, signing IDs, Bundle IDs, GitHub Releases, GitHub Pages config, and App Store/DUNS account metadata remain unchanged unless explicitly authorized.
- Run the existing Lite and desktop syntax checks.
- Run `xcodebuild` target checks after the asset catalog exists.
- Run the Apple Lite simulator smoke harness after rebuilding the LiteWeb bundle.
- Re-check `git diff --check` and staged diff whitespace before commit.

## Known Gaps

- No Apple Lite icon assets were generated or committed in this pass.
- No screenshots were captured or committed in this pass.
- No launch screen asset was added.
- No AMPYX signing, production Bundle ID, App Store Connect, TestFlight archive, release asset, GitHub Pages config, or runtime behavior changed.
