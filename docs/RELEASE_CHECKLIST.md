# Release Checklist

Use this before tagging or publishing a public WZRD.VID release.

## Legal / Docs

- [ ] `LICENSE` exists and contains the WZRD.VID Source-Available License.
- [ ] `NOTICE.md` exists and preserves Sam Howell branding ownership language.
- [ ] `THIRD_PARTY_NOTICES.md` lists ffmpeg/ffprobe, PySide6/Qt, OpenCV, Pillow, numpy, and PyInstaller.
- [ ] README has current install, run, build, source-available rights, and media-rights sections.
- [ ] No copyrighted sample media is included.

## Hygiene

- [ ] `.gitignore` excludes virtualenvs, caches, build outputs, rendered media, logs, and temp folders.
- [ ] No local absolute paths are present in source/docs.
- [ ] No stale project names, third-party show references, fantasy-themed copy, or forbidden dither labels remain.
- [ ] No large media files are tracked.

## Verification

```bash
python3 -m py_compile app.py app_i18n.py renderer.py datamosh.py ffmpeg_utils.py still_cache.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py
node --check docs/i18n.js
node --check docs/lite/app.js
bash -n build_app.sh
bash -n scripts/package_dmg.sh
bash -n scripts/package_release.sh
./build_app.sh
scripts/package_dmg.sh
```

- [ ] `dist/WZRD.VID.app` exists.
- [ ] `find -L dist/WZRD.VID.app -type l -print` returns no paths.
- [ ] `codesign --verify --deep --strict --verbose=4 dist/WZRD.VID.app` passes.
- [ ] Finder-style launch works.
- [ ] Branding assets are bundled.
- [ ] App icon appears correctly in Finder/Dock.
- [ ] `WZRD.VID-macOS.dmg` mounts with only `WZRD.VID.app`, `Applications -> /Applications`, and intentional Finder metadata.
- [ ] The app inside the mounted DMG and an isolated replacement install have zero dangling links and pass strict codesign.
- [ ] The mounted/replacement app keeps the expected Bundle ID/version and remains ad-hoc signed with no TeamIdentifier.
- [ ] An isolated old-app replacement leaves test `settings.json`, `ImportedMedia`, `StillCache`, `Previews`, and external recipe hashes unchanged.
- [ ] Human Finder checks confirm the drag-to-Applications layout is clear and dragging over an existing isolated app offers Replace.
- [ ] Gatekeeper guidance remains honest: this workflow does not add Developer ID signing or notarization, and it never strips quarantine.


## Release Asset

- [ ] Run `./build_app.sh`.
- [ ] Run `scripts/package_dmg.sh` and record its exact size and SHA-256.
- [ ] Run `scripts/package_release.sh` only if the fallback ZIP is part of the authorized release.
- [ ] Confirm `WZRD.VID-macOS.dmg` exists; confirm `WZRD.VID-macOS.zip` if the fallback was requested.
- [ ] Verify the tag and release title match the current `VERSION`; do not use a future version before stabilization and release authorization.
- [ ] Upload the DMG and optional fallback ZIP only during the separately authorized publication phase.
- [ ] Release notes mention that the packaged Mac build is tested primarily on Apple Silicon Macs, remains ad-hoc/unnotarized unless later release evidence says otherwise, and Intel Mac users should run from source for now.
- [ ] Release notes include:

```text
//wzrdVID
ANSI broadcast lab // lo-fi fragment synthesis // public-access hallucinations

Summarize the release highlights for the current version.
```

- [ ] Confirm download instructions point normal users to Releases, not the Code ZIP.

## GitHub Metadata

Suggested description:

```text
//wzrdVID — ANSI broadcast lab for lo-fi fragment synthesis and public-access hallucinations.
```

Suggested topics:

```text
video-art, ansi-art, ascii-art, glitch-art, ffmpeg, pyside6, video-effects, creative-tools, lo-fi, compression-art, macos
```

## v0.3.0 Local Preparation Evidence — 2026-08-25

This records the locally prepared release candidate. It does not authorize or claim publication.

- [x] `VERSION`, desktop fallback, bundled resource, and both macOS bundle version fields report `0.3.0`.
- [x] The complete syntax/static, dependency, version-comparison, Lite privacy, and protected-identity matrix passes.
- [x] The fresh arm64 app has zero dangling links, passes strict codesign, launches as `WZRD.VID v0.3.0`, and remains ad-hoc signed with no TeamIdentifier.
- [x] Frozen packaged-code default-pipe and forced-PNG renders pass with `.3gp`, source AAC, mid-output Style, all five Phase 2 effects, authentic DATAMOSHING, source preservation, and temp cleanup.
- [x] Final local DMG: 82,977,353 bytes; SHA-256 `67999c6a8533e61cbaef5b46c500c96794f8511a9545239a26836a31c22a021b`.
- [x] Final local ZIP fallback: 79,429,475 bytes; SHA-256 `f096b7c9364c526b44731b5ccccd46ee6aff6ccea2e6a83374562f81832f7e08`.
- [x] The `dist`, mounted-DMG, and freshly extracted-ZIP app trees have identical full-content manifests, executable SHA-256, CDHash, identity, version, architecture, and signature state.
- [x] Isolated replacement from a simulated v0.2.1 app to the final v0.3.0 DMG app passes; external settings, ImportedMedia, StillCache, Previews, and recipe hashes remain unchanged.
- [ ] Run the packaged-GUI test with suitable real Messages/Photos HEIC/HEIF media when available.
- [ ] Run physical-iPhone Lite source-audio listening and saved-Photos playback when an iPhone is available.
- [ ] Human-check Finder DMG presentation and the existing-app **Replace** dialog.
- [ ] After publication, validate Gatekeeper behavior from a genuinely downloaded/quarantined DMG.
- [ ] Commit, push, tag, create the GitHub Release, upload the exact artifacts, and update public download guidance only in a separately authorized publication phase.
