# Changelog

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
