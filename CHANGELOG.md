# Changelog

## v0.2.0 — Unreleased

- Started v0.2.0 performance hardening with in-process ffprobe metadata caching for repeated duration and stream helper calls.
- Added render-stage timing logs and long-media warnings for 30+ minute source video/audio inputs.
- Ran synthetic long-media stress smokes covering max length, random clip assembly, source/external audio, worky mode, match-to-music rejection, and preview-like renders.
- Documented WZRD.VID Lite Apple app groundwork as research only while Apple Developer/D-U-N-S setup is pending.
- Started WZRD.VID Lite Apple packaging groundwork with SwiftUI/WKWebView shell sources and a local Lite web-bundle prep script.

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
