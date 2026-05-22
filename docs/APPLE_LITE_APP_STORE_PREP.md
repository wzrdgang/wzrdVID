# WZRD.VID Lite App Store Prep Drafts

Date: 2026-05-22
Status: draft metadata and privacy-policy assets only; Apple Developer organization enrollment is still pending

This document prepares App Store Connect and TestFlight review materials for WZRD.VID Lite without submitting anything and without changing app code, signing IDs, Bundle IDs, App Store/DUNS account metadata, GitHub Releases, or GitHub Pages configuration.

## Current Source Facts

- App display name in `Info.plist`: `WZRD.VID Lite`.
- Current local/dev Bundle ID in the Xcode project: `com.samhowell.wzrdvid.lite`. Treat this as repo evidence only, not the production identity.
- Preferred production Bundle ID candidate: `com.worky.wzrdvid.lite`, unless Apple/account setup later requires a different AMPYX-controlled reverse-DNS identity.
- Current project team setting: `DEVELOPMENT_TEAM = JKSWZ8682X`. This is current repo evidence only; the final AMPYX organization Team ID must replace or confirm it after enrollment.
- Current app version/build: `0.2.0` / `1`.
- D-U-N-S status: AMPYX LLC has D-U-N-S available/received; the exact number is intentionally not repeated here.
- Platform target in project settings: iOS/iPadOS target with deployment target `17.0`.
- Encryption plist value: `ITSAppUsesNonExemptEncryption = false`.
- Photos usage strings are present for selecting local media and saving rendered clips to Photos.
- Native wrapper loads bundled `LiteWeb` files through `WKWebView.loadFileURL`, cancels non-local navigation, and hides the web back link in the native shell.
- Native export bridge transfers the rendered Lite blob to Swift, validates a video track with AVFoundation, and saves to Photos with add-only `PHPhotoLibrary` permission.
- Lite runtime evidence remains local-only: no accounts, analytics, uploads, backend calls, tracking SDKs, remote config, or unrestricted web browsing.
- `docs/i18n.js` uses `localStorage` only for the UI language preference.
- No `Assets.xcassets`, app icon set, launch storyboard, or `PrivacyInfo.xcprivacy` file is present under `apple-lite/` as of this draft.

## Apple Source Notes

- App Store Connect app information currently limits the localized app name and subtitle to 30 characters each, requires an iOS privacy policy URL, and requires the Bundle ID to match the Xcode project before upload. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/app-information>
- Promotional text is limited to 170 characters; description is required and limited to 4000 characters; keywords allow up to 100 bytes and should not duplicate the app/company name. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information>
- App Privacy can be answered as no data collection only if the implementation remains no-collection/no-tracking; Apple notes that data processed only on device and never sent to a server is not collected for App Privacy disclosure. Sources: <https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/> and <https://developer.apple.com/app-store/app-privacy-details/>
- App Store Connect requires one to ten screenshots per supported display set, with iPad screenshots required if the app runs on iPad. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications>
- Apple generates age ratings from the App Store Connect age-rating questionnaire. Source: <https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions>

## App Store Connect Metadata Draft

### App Name

`WZRD.VID Lite`

Rationale: matches the current display name, stays under Apple's 30-character app-name limit, and avoids changing production identity before Apple Developer enrollment.

### Subtitle

`Local glitch video clips`

Rationale: 24 characters including spaces; describes the local media workflow without duplicating the app name.

### Promotional Text

`Turn local photos, videos, and audio into short glitch clips on device. No sign-in, no uploads, no tracking.`

Rationale: 108 characters including spaces; emphasizes current privacy and workflow boundaries.

### Description

Draft:

```text
WZRD.VID Lite makes short chaos-cut video clips from media you choose on your device.

Add local photos, videos, GIFs, or audio, choose a 15, 30, or 60 second render, and generate a glitchy clip with ANSI-style texture, motion, and audio-reactive treatment. When the clip is ready, WZRD.VID Lite saves the rendered video to Photos.

The Lite app is built for quick local experiments, not full desktop WZRD.VID parity. It runs from bundled app files, does not require an account, and does not upload your media. Media stays on your device unless you choose to share the saved output yourself.

Current Lite boundaries:
- Local media selection only
- On-device browser/native Lite rendering
- No accounts or sign-in
- No analytics
- No tracking
- No uploads or backend processing
- Output saved to Photos when you tap Download
```

### Keywords

`video,glitch,ASCII,ANSI,local,clips,canvas,VHS,retro,media`

Rationale: 58 ASCII bytes, avoids duplicating the app name and company name, and fits the current Lite workflow.

### Category Recommendation

- Primary category: `Photo & Video`.
- Secondary category candidate: `Entertainment`, if App Store Connect allows and the final product page needs a broader creative-placement signal.

Rationale: the primary user action is transforming user-selected media into video output.

### Age-Rating Notes

Draft questionnaire posture:

- Not Made for Kids.
- No unrestricted web access; the wrapper cancels non-local navigation.
- No user-generated content distribution; users can process their own local media, but the app does not publish, host, browse, or distribute user content.
- No messaging, chat, social feed, advertising, purchases, gambling, contests, health/medical claims, location use, or user account system.
- App-provided content should be benign. User-selected local media may contain arbitrary user-owned content, but it is not app-provided or broadly distributed by WZRD.VID Lite.
- Let App Store Connect generate the final age rating from the questionnaire; expected direction is a low rating if the implementation and screenshots remain as currently described.

### Support URL Needs

Need a public support URL before App Store Connect submission. Draft candidate:

`https://wzrdvid.com/support/`

Draft route added: `docs/support/index.html`. It is GitHub Pages-ready once pushed to the Pages branch, but AMPYX LLC support contact details still need to be finalized before App Store submission.

Required content for that page:

- Contact path for app issues and feedback.
- Short WZRD.VID Lite FAQ covering local-only import/render/export.
- Photos permission explanation.
- Current limitations: Lite is not full desktop parity; source clip audio is not preserved from visual timeline sources; output saves to Photos.
- Legal/company contact information appropriate for AMPYX LLC once account setup is finalized.

This prep does not submit the support URL in App Store Connect.

### Privacy Policy URL Needs

Need a public privacy policy URL before App Store Connect submission. Draft candidate:

`https://wzrdvid.com/privacy/`

Draft route added: `docs/privacy/index.html`. It is GitHub Pages-ready once pushed to the Pages branch, but final AMPYX LLC contact details and any legal review still need to be completed before App Store submission.

This prep does not submit the privacy URL in App Store Connect.

## App Privacy Draft

Recommended App Store Connect answer, if the current implementation remains unchanged:

`No, we do not collect data from this app.`

Supporting implementation facts:

- Media is selected by the user from local Photos/Files surfaces and processed locally.
- Rendered clips are generated locally and saved to Photos only when the user taps Download.
- The app has no account creation, sign-in, analytics, ads, tracking SDKs, backend upload, remote config, or server processing.
- The native wrapper loads bundled app files rather than a remote website.
- Non-local WebView navigation is canceled.
- The only observed persistent local browser storage is the UI language preference in `localStorage`.
- Temporary export files are written locally so the native shell can validate and save the generated movie to Photos.

Data categories draft:

- Contact Info: not collected.
- Health & Fitness: not collected.
- Financial Info: not collected.
- Location: not collected.
- Sensitive Info: not collected.
- Contacts: not collected.
- User Content: not collected by WZRD.VID Lite. User-selected media is processed locally and is not uploaded or sent to AMPYX LLC.
- Browsing History: not collected.
- Search History: not collected.
- Identifiers: not collected by the app.
- Purchases: not collected.
- Usage Data: not collected.
- Diagnostics: not collected by the app.
- Other Data: not collected.
- Tracking: no.

Photos and file access note:

WZRD.VID Lite asks for Photos/file access only when users choose local media and when users save rendered output. Photos add-only permission is used for the direct Save Video path. These permissions should be described in the privacy policy and review notes, but local-only processing does not become App Privacy data collection unless media or metadata is sent off-device.

## Privacy Policy Draft

Draft public-page text:

```text
WZRD.VID Lite Privacy Policy

WZRD.VID Lite is a local media tool. It lets you choose photos, videos, GIFs, and audio from your device, render a short stylized video clip, and save the result to Photos.

We do not require an account. We do not upload your media. We do not collect analytics. We do not use tracking. We do not sell personal information.

Media you choose is processed on your device. Rendered output is saved to Photos only when you tap Download. You can then decide whether to keep, delete, or share that saved output.

WZRD.VID Lite requests Photos or file access so you can select local media and save rendered clips. The app may temporarily write a rendered clip on your device so it can validate and save the video to Photos.

WZRD.VID Lite stores your interface language preference locally in the app browser environment. This preference is not uploaded.

If the app changes to collect data in the future, this policy and the App Store privacy information should be updated before release.

Contact: [insert AMPYX LLC support contact or support URL after Apple Developer/App Store setup is finalized]
Effective date: [insert publication date]
```

## App Review Notes Draft

Draft:

```text
WZRD.VID Lite is a bundled local Lite app, not a remote website wrapper. The native shell loads app-bundled LiteWeb files with WKWebView.loadFileURL and cancels non-local navigation.

The app works without sign-in and has no accounts, analytics, tracking, uploads, backend processing, or remote configuration. Users choose local media, render a short clip on device, and tap Download to save the rendered output to Photos.

Photos access is requested for two user-directed actions:
1. selecting local photos/videos for rendering
2. saving the rendered clip to Photos after the user taps Download

The native export bridge receives the locally rendered movie blob, writes a temporary local file, validates that it contains a video track, and saves it to Photos using add-only Photos permission.

Suggested review flow:
1. Launch WZRD.VID Lite.
2. Tap Add Media and choose a local photo/video from Photos or Files.
3. Optional: add local audio.
4. Choose 15 seconds and optionally enable Random clip assembly.
5. Tap Render.
6. After rendering completes, tap Download.
7. Confirm the rendered clip is saved to Photos.
```

## Screenshot Checklist

Capture clean, production-signed screenshots after final AMPYX signing and Bundle ID setup. Use non-private sample media created or licensed for screenshots.

- Launch/import screen: app open to bundled WZRD.VID Lite with Add Media visible.
- Selected media state: at least one local photo/video loaded in the Lite media list.
- Render settings: duration, quality, random assembly, and optional audio controls visible.
- Rendering/export state: render progress or completed render with preview and Download available.
- Saved output result: Photos save confirmation and/or final rendered clip visible in Photos.

Device-class checklist:

- Required iPhone screenshot set for the currently accepted App Store Connect display targets.
- iPad screenshot set if the app remains available on iPad.
- Optional app preview video only after the still screenshot package is stable.

## Required Asset Gaps

- App icon asset catalog for the Xcode app target.
- App Store marketing icon/source asset suitable for Apple's current icon workflow.
- Optional branded launch screen or decision to keep the current empty `UILaunchScreen` dictionary for first TestFlight.
- Production screenshots for each required device class.
- Final AMPYX LLC support contact details and post-push verification for the public support URL.
- Final AMPYX LLC privacy contact details, legal review if needed, and post-push verification for the public privacy policy URL.
- Final review-note package with real signed-build behavior.
- Final AMPYX organization Team ID after Apple Developer enrollment.
- Final production Bundle ID registration, preferably `com.worky.wzrdvid.lite` unless Apple/account setup requires a different AMPYX-controlled reverse-DNS identity.
- App Store Connect app record.
- Release archive/upload validation with the required current Apple SDK.

## Known Gaps

- Apple Developer organization enrollment is still pending.
- No App Store Connect app record has been created.
- No archive, upload, TestFlight distribution, App Review submission, website deployment, release publication, signing change, or Bundle ID change was made for this prep pass.
- Support and privacy page drafts exist under `docs/support/` and `docs/privacy/`, but they still need a pushed Pages deployment, final AMPYX LLC contact details, and live URL verification before App Store Connect use.
- Privacy manifest requirements still need an archive/upload validation pass. No `PrivacyInfo.xcprivacy` file is present in the current Apple Lite source.
- Physical-device testing should be rerun after AMPYX signing and the final production Bundle ID are configured.
