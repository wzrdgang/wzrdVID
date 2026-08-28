# Changelog

## Unreleased

- Fixed desktop product-surface handoffs so Download Update and rendered Preview report external-open failures instead of silently doing nothing, fresh profiles label the 5-second Preview action correctly, and manual Preview cache cleanup clears the now-stale Open Preview state.
- Added deterministic Drift and Pulse motion to desktop Zones for the five frame-domain Material effects. Motion follows absolute full-output time in full renders and Preview slices, preserves hard Zone containment and Loop closure, keeps moving Circuit history bounded by stable Zone ID, and deliberately leaves SKRRT on each Zone's saved static base rectangle.
- Fixed desktop Preview so Random source selection, transitions, delayed audio, ending/Loop behavior, audio fades, and Stutter timing match the selected interval of the planned full output.

## v0.4.0 — 2026-08-27

### More organic Style corruption

- Reworked Pixel Sorting, Databending, Circuit Bending, Hex Editing, and Random Noise B/W around deterministic, material-responsive scheduling. Corruption now follows source motion, luminance, edges, texture, and transitions through irregular lulls, clusters, damage, and recovery while preserving seeded repeatability and clean Style boundaries.

### DATAMOSH MODES

- Expanded the codec-art palette into five clearly named modes: transition-aware `DATAMOSHING`, recursively accumulating `spILL!`, reverse-prediction `SKRRT`, spatial-fragment `ShShSHa`, and transition-flow `FLOWs`.
- Strengthened auxiliary-stream validation and fail-closed behavior so SKRRT and ShShSHa accept only their intended single-I-anchor/P-only structures before prediction data reaches the final render.

### Layer

- Added persistent user-controlled ordering for all five DATAMOSH modes. Ordered complete-VOP writers use deterministic last-writer semantics while sharing one controlled MPEG-4 Part 2 encode and one safe H.264/yuv420p transcode.
- Preserved the historical order for older state, malformed or missing Layer data, and Reset; duplicate or unknown operation identifiers are rejected.

### Style FX Coverage

- Added an independent Style FX Coverage control with full, random-clean, manual-clean, and combined modes. It gates optional Style effects separately from ANSI Coverage and protects temporal clean intervals across frame and codec effects.

### Zones and spatial SKRRT

- Added up to three static named Zones in normalized final-output space with create, rename, duplicate, delete, move, resize, and percentage geometry controls.
- Added six assignment rows: Pixel Sorting, Databending, Circuit Bending, Hex Editing, and Random Noise B/W remain hard-contained to their assigned rectangle; SKRRT uses authentic spatial reverse prediction with bounded decoded codec leakage and explicit recovery.
- Advanced newly saved desktop state to schema 6. Schema 3/4/5 state migrates to no Zones/Full Frame, malformed Zone data repairs safely, and ShShSHa plus every other codec mode remain deliberately Zone-ineligible.

### Reliability and presentation

- Fixed spatial-fragment frame-clock alignment for long prepared branches, kept the five DATAMOSH activation controls compact and readable, and gave the activation strip one continuous themed background.
- Renamed the visible direct-cut transition to `None` while retaining its compatible persisted identity. Source media, audio timing, Preview, Random, Loop, framing, and the final H.264/AAC transport contracts remain unchanged.

## v0.3.0 — 2026-08-25

- Added a macOS DMG packaging workflow with the conventional `WZRD.VID.app` → `Applications` drag-install layout. The package path validates the ad-hoc app before and after imaging, and isolated replacement testing confirms app-support settings, ImportedMedia, StillCache, Previews, and external recipe files remain outside the replaced bundle.
- Added optional source-video audio to WZRD.VID Lite and Apple Lite. The new default-on `Include Source Audio` control follows normal and random visual cuts, keeps still sections silent on the source bus, and can mix source sound with explicitly added audio into one recorded track.
- Fixed macOS app pruning so intentionally removed Qt frameworks and translations no longer leave dangling bundle symlinks. Fresh builds now stop on any dangling link and pass strict codesign verification without restoring unused Qt payload.
- Added authentic desktop DATAMOSHING using controlled MPEG-4 Part 2 I/P-frame prediction manipulation after the visual render and before the existing H.264/AAC finalization. Temporary prediction streams remain app-owned; source media is never modified and final exports remain normal MP4 files.
- Added five desktop frame-domain Style Stack effects: Pixel Sorting, in-memory Databending, software-emulated Circuit Bending, in-memory Hex Editing, and luminance-driven Random Noise B/W. They share the existing Effect Intensity and Reroll Weirdness controls, obey `Style begins at`, and persist as default-off flags in schema-version-5 recipes.
- Added desktop `.3gp` and `.3g2` visual video-container support across import, drag/drop, recipe restore, preview/render, and selected source-audio handling.
- Added a desktop `Style begins at` output-timeline control that keeps earlier frames clean, starts the existing WZRD treatment on the first eligible frame, and persists through local settings and schema-version-5 recipes while older recipes default to `0:00`.
- Improved desktop Glitch Hell/ASCII text render performance by caching per-render glyph masks before drawing ANSI frames. This preserves ASCII text-art pixels while avoiding repeated glyph rasterization in `ImageDraw.text`.
- Added more detailed desktop renderer timing logs for still/proxy loading, HEIC motion frame generation, resize/framing, ANSI prep effects, text sampling, glyph drawing, ANSI output effects, transitions/effects/endings, and frame-pipe writes.
- Fixed desktop HEIC/HEIF render failure handling so macOS privacy/access-denied source errors fail during preflight with the exact file path and copy/export guidance instead of being mislabeled as missing HEIC support or retried through PNG staging.
- Improved desktop HEIC/HEIF photo import from protected macOS Messages/Photos containers by copying readable protected sources into WZRD.VID's app-owned `ImportedMedia` cache while keeping the original filename visible in the timeline.
- Changed protected HEIC/HEIF import copy failures to fail at import time instead of adding unreadable protected paths to the timeline, while leaving renderer preflight as fallback safety for recipes and older timelines.
- Hardened protected HEIC/HEIF import caching with staged copies and content-only/Qt copy fallbacks so readable user-selected files can still import if metadata-preserving copy fails.

## v0.2.1 — 2026-05-14

- Fixed a desktop PUBLIC ACCESS preview/render crash that could occur with JPEG stills and ANSI output effects when image arrays were read-only. This patch keeps v0.2.0 behavior intact and only hardens the desktop render effect path.
- Bumped app/release metadata to v0.2.1.

## v0.2.0 — 2026-05-13

- Started v0.2.0 performance hardening with in-process ffprobe metadata caching for repeated duration and stream helper calls.
- Added render-stage timing logs and long-media warnings for 30+ minute source video/audio inputs.
- Ran synthetic long-media stress smokes covering max length, random clip assembly, source/external audio, worky mode, match-to-music rejection, and preview-like renders.
- Documented WZRD.VID Lite Apple app groundwork as research only while Apple Developer/D-U-N-S setup is pending.
- Started WZRD.VID Lite Apple packaging groundwork with SwiftUI/WKWebView shell sources and a local Lite web-bundle prep script.
- Added a simulator-ready WZRD.VID Lite Xcode project plus a debug simulator smoke harness for bundled Lite load, local import surface, language switching, random clips, and export/download readiness.
- Added a narrow WZRD.VID Lite Apple native export/share bridge after real-device testing showed WKWebView blob downloads opened rendered clips for playback instead of giving a reliable save/share handoff.
- Added a WZRD.VID Lite Web Audio fallback for the explicit Add Audio bus on iOS WKWebView, where `HTMLAudioElement.captureStream()` is unavailable.
- Tightened WZRD.VID Lite Apple export by seeding/requesting canvas frames before recording, fixing native Blob payload transfer for MP4 codec strings, adding export diagnostics, and saving validated MP4 exports directly to Photos from the native wrapper.
- Improved WZRD.VID Lite random clip assembly so shuffled random timelines use all loaded media before reusing a source.
- Restored more WZRD.VID Lite visual texture with shorter black fadeouts, stronger Ken Burns/tunnel motion, audio-reactive bump, brighter source treatment, and less destructive ANSI overlay.
- Raised WZRD.VID Lite render cadence from the old 15 fps cap to a 30 fps target for Fast 480p exports, while keeping Better 720p at 24 fps to avoid overloading iPhone renders.
- Tuned Apple Lite's browser renderer back toward the live WZRD.VID Lite visual baseline with stronger tunnel zoom, punch/wobble, and harder ANSI treatment while preserving iPhone export/audio fixes.
- Fixed a hue-shift overflow crash that could appear during long desktop renders.
- Prototyped an experimental direct ffmpeg frame-pipe renderer behind `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1`; PNG frame staging remains the default and fallback while validation continues.
- Added explicit frame-pipe startup logging and a local desktop developer toggle so packaged-app tests do not depend on macOS `open` propagating shell environment variables.
- Added automatic and manual cleanup for WZRD.VID-managed preview/cache files.
- Improved desktop random-normal/ANSI-bypass frame selection for long renders with many normal sections.
- Improved HEIC/HEIF and photo slideshow import/render performance with deferred decode, reusable still proxies, and detailed still-frame timing logs.
- Fixed desktop Max Video Length auto/default saved-state handling and clarified external music requested trim, read window, and output placement logs.
- Fixed delayed external music placement when worky music mode is enabled.
- Fixed a desktop PUBLIC ACCESS preview/render crash caused by read-only image arrays after scanline processing.
- Bumped app/release metadata to v0.2.0.

## v0.1.9 — 2026-05-10

- Added UI localization architecture for the desktop app, wzrdvid.com, and WZRD.VID Lite with English fallback and draft translations for the initial target language set.
- Added desktop and web language selectors with local-only UI language persistence.
- Improved Unicode/global readability support with system font fallbacks, wrapping hardening, and structural Arabic `dir` support on the static site and Lite.
- Removed the top homepage Mac install notice block while preserving the remaining release ZIP guidance.
- Tightened high-visibility desktop localization coverage for common tooltips, table type labels, warning/dialog copy, status labels, and header/session-log text.
- Moved the update and language controls into the desktop header for easier access.
- Added a desktop max video length control for capping final render duration.
- Added desktop random clip assembly for building capped-duration videos from uploaded timeline media.
- Added a WZRD.VID Lite random clip assembly checkbox that uses Lite's existing 15/30/60-second duration choices.
- Documented localization resource locations, fallback behavior, and draft/native-review limits.
- Bumped app/release metadata to v0.1.9.

## v0.1.8 — 2026-05-09

- Clarified that current packaged Mac ZIPs are tested primarily on Apple Silicon Macs, with Intel Mac users directed to the source-run path for now.
- Verified PUBLIC ACCESS 0%, mixed, and 100% ANSI Coverage behavior after the v0.1.7 renderer release.
- Improved download, install, first-run, and manual update guidance.
- Bumped app/release metadata to v0.1.8.

## v0.1.7 — 2026-05-09

- Added the real PUBLIC ACCESS renderer path for public-access/VHS source treatment before ANSI coverage is applied.
- Preserved PUBLIC ACCESS compatibility with 0%, mixed, and 100% ANSI/text-art output.
- Added PUBLIC ACCESS parity to WZRD.VID Lite with browser-side VHS/public-access treatment.
- Expanded Lite accepted extensions while documenting browser-dependent decoding limits.
- Bumped app/release metadata to v0.1.7.

## v0.1.6 — 2026-05-09

- Added selectable 5-second and 10-second preview renders.
- Expanded accepted media extensions for video, audio, and photo import.
- Added HEIC/HEIF still-image decode fallback and subtle automatic 3-second motion-loop behavior when supported locally.
- Added worky’s music mode for tiny mono broadcast-style external audio processing.
- Added PUBLIC ACCESS style/profile groundwork while preserving ANSI Coverage controls.
- Bumped app/release metadata to v0.1.6.

## v0.1.5 — 2026-05-09

- Fixed the packaged desktop update checker so GitHub release lookups use a stronger request path, explicit headers, short timeouts, and release-page fallback.
- Improved update-check failure handling with clearer diagnostics and a manual release-page button instead of a dead-end unavailable state.
- Verified semver comparison for older app versions against the current latest release.
- Bumped app/release metadata to v0.1.5.

## v0.1.4 — 2026-05-09

- Renamed project preset controls to recipe import/export while keeping legacy JSON compatibility.
- Polished Reset Project behavior so it clears state without deleting media or output files.
- Changed the default transition from Hard Cut to CRT Flash while preserving saved recipe transition choices.
- Verified Fade Out remains the default ending.
- Improved drag/drop rejection logging for unsupported timeline and audio drops.
- Bumped app/release metadata to v0.1.4.

## v0.1.3 — 2026-05-09

- Added a sanitized COPY REPORT helper for support/debug info without exposing full home-directory media paths.
- Bumped app/release metadata to v0.1.3 for the bugfix-only polish release.
- Ran clean-install validation against the published v0.1.2 ZIP and recorded first-run friction for follow-up.

## v0.1.2 — 2026-05-09

- Verified Lite duration caps and ANSI Coverage behavior for 15/30/60-second browser clips.
- Verified public copy cleanup to worky/fragment-synthesis language.
- Added a simple non-blocking GitHub Releases update checker to the desktop app.
- Bumped release packaging and app metadata to v0.1.2.

## v0.1.1 — 2026-05-08

- Added drag-and-drop media support for timeline videos/photos.
- Added drag-and-drop music/audio support, including video files with audio tracks.
- Fixed rotated phone-photo imports by respecting EXIF orientation.
- Added delayed external music/audio placement inside the rendered video timeline.
- Improved external + selected source audio mixing with delayed audio entry.

## v0.1.0 — Initial Public Release

- Initial ANSI/text-art video rendering pipeline.
- Multi-source timeline for videos and photos.
- Audio system with external audio, source audio, per-row Include Audio, and external/source mixing.
- ANSI, chunky block, dither, glitch, VHS, compression-art, transition, ending, and framing controls.
- Output-size workflows including 29 MB Text Limit and 32 MB Sweet Spot optimization.
- Batch preset rendering.
- Pastel broadcast/ANSI UI identity and procedural branding assets.
- PyInstaller macOS app packaging for `dist/WZRD.VID.app`.
- Clarified source-available licensing before first packaged release.
