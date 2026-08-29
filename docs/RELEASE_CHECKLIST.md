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
- [ ] Validate normal browser/Finder quarantine and first-launch behavior. Fresh command-line public downloads had provenance but no quarantine; `spctl` rejected the intentionally ad-hoc/unnotarized DMG/app, so this remains manual.
- [x] Commit and push release source `7b2333fe0a7656e3e6058b56a9deb0b265199482`; tag `v0.3.0`; publish the GitHub Release; upload and fresh-download-verify the exact DMG/ZIP; update public guidance to DMG-primary with ZIP fallback.

## v0.3.0 Publication Evidence — 2026-08-25

- [x] `main` and `origin/main` contained release source commit `7b2333fe0a7656e3e6058b56a9deb0b265199482` before tagging.
- [x] Lightweight tag `v0.3.0` resolves exactly to the release source commit locally and remotely.
- [x] GitHub Release `WZRD.VID v0.3.0` is published, non-draft, and non-prerelease at https://github.com/wzrdgang/wzrdVID/releases/tag/v0.3.0.
- [x] GitHub DMG asset ID `530032899`, 82,977,353 bytes, digest `sha256:67999c6a8533e61cbaef5b46c500c96794f8511a9545239a26836a31c22a021b`.
- [x] GitHub ZIP asset ID `530032896`, 79,429,475 bytes, digest `sha256:f096b7c9364c526b44731b5ccccd46ee6aff6ccea2e6a83374562f81832f7e08`.
- [x] Fresh public downloads matched both authoritative hashes; downloaded DMG/ZIP apps remained arm64, v0.3.0, ad-hoc/no-Team, strict-valid, link-clean, and matched the approved executable SHA/CDHash.
- [x] A freshly downloaded ZIP app launched under an isolated profile with visible title `WZRD.VID v0.3.0`.
- [ ] Real packaged-GUI Messages/Photos HEIC/HEIF remains manual.
- [ ] Physical-iPhone Lite source-audio listening and saved-Photos playback remains manual and separate from the desktop release.
- [ ] Human Finder DMG presentation and existing-app **Replace** wording remains manual.
- [ ] Normal browser/Finder quarantine and Gatekeeper first-launch behavior remains manual; command-line public downloads did not receive `com.apple.quarantine`.

## v0.4.0 Local Preparation Evidence — 2026-08-27

This records the feature-frozen, locally prepared release candidate. It does not authorize or claim a commit, tag, upload, release, deployment, or publication.

- [x] `VERSION`, desktop fallback, bundled resource, and both macOS bundle version fields report `0.4.0`; Apple Lite version/identity is unchanged.
- [x] The complete accumulated-diff, source, syntax/static, dependency, privacy, UI/state/migration, performance, media/audio/transport/failure, and Apple Lite non-regression gates pass.
- [x] The 18-case Full Frame oracle remains `441f9150b0f8c2d79fadb5a653a4b930d777959c37e458099a3b28eee3baa80a`; exact Zone eligibility remains the five Material Dynamics effects plus SKRRT, with ShShSHa Zone-ineligible.
- [x] The single fresh arm64 app build has 205 thin-arm64 Mach-O files, zero dangling links, strict deep ad-hoc codesign, no TeamIdentifier, and Bundle ID `com.samhowell.wzrdvid`.
- [x] Frozen newly built modules pass application/schema/six-row UI, Style FX, Material/organic, all five codec modes, historical/reverse Layer, Full Frame/Zone SKRRT, Preview/Random/Loop, mixed media, H.264/yuv420p/AAC, one main encode/one safe transcode, source immutability, and failure cleanup.
- [x] Final local DMG: 82,303,287 bytes; SHA-256 `90383e2eaf877dd9121368a019b3f17a896f51750e4746936f818f45784ead03`.
- [x] Final local ZIP fallback: 79,584,462 bytes; SHA-256 `396c3bd70ad91e446f046a488da1ea98d7d3b0878a2192121451934abe3730ff`.
- [x] The `dist`, mounted-DMG, and freshly extracted-ZIP app trees have identical 577-entry manifests, executable SHA-256, CDHash, identity, version, architecture, signature state, and Team state.
- [x] Isolated prior-app replacement with the final DMG app removes the old marker, validates the new bundle, and leaves nonempty external settings, ImportedMedia, StillCache, Previews, and recipe hashes unchanged.
- [ ] Run the packaged GUI test with a suitable real Messages/Photos HEIC/HEIF readable/rejection pair when available.
- [ ] Human-check Finder DMG presentation and the existing-app **Replace** dialog.
- [ ] Validate normal browser/Finder quarantine and first-launch behavior; the package remains intentionally ad-hoc signed and unnotarized.
- [ ] Run physical-iPhone Lite source-audio listening and saved-Photos playback when an iPhone and the separately required Apple release context are available.
- [x] Commit and push release source `c66d846283f3d2c81863569e3ed8d083545f7681`; tag `v0.4.0`; publish the GitHub Release; upload and fresh-download-verify the exact DMG/ZIP; update public guidance to v0.4.0 DMG-primary with ZIP fallback.

## v0.4.0 Publication Evidence — 2026-08-27

- [x] `main` and `origin/main` contained release source commit `c66d846283f3d2c81863569e3ed8d083545f7681` before tagging.
- [x] Lightweight tag `v0.4.0` resolves exactly to the release source commit locally and remotely.
- [x] GitHub Release `WZRD.VID v0.4.0` is published, non-draft, and non-prerelease at https://github.com/wzrdgang/wzrdVID/releases/tag/v0.4.0.
- [x] GitHub DMG asset ID `533036335`, 82,303,287 bytes, digest `sha256:90383e2eaf877dd9121368a019b3f17a896f51750e4746936f818f45784ead03`.
- [x] GitHub ZIP asset ID `533036338`, 79,584,462 bytes, digest `sha256:396c3bd70ad91e446f046a488da1ea98d7d3b0878a2192121451934abe3730ff`.
- [x] Fresh public downloads matched both authoritative hashes; downloaded DMG/ZIP apps remained thin arm64, v0.4.0, ad-hoc/no-Team, strict-valid, link-clean, and matched the approved executable SHA/CDHash and 577-entry manifest.
- [x] A freshly downloaded ZIP app launched from its temporary extraction with visible title `WZRD.VID v0.4.0`; the exact task PID was stopped and real settings remained byte-identical.
- [ ] Real packaged-GUI Messages/Photos HEIC/HEIF remains manual.
- [ ] Physical-iPhone Lite source-audio listening and saved-Photos playback remains manual and separate from the desktop release.
- [ ] Human Finder DMG presentation and existing-app **Replace** wording remains manual.
- [ ] Normal browser/Finder quarantine and Gatekeeper first-launch behavior remains manual; command-line public downloads carried provenance but no `com.apple.quarantine`.

## v0.5.0 Local Preparation Evidence — 2026-08-28

This records the locally qualified desktop release candidate. It does not authorize or claim a tag, GitHub Release, upload, Pages deployment, production signature, notarization, or website transition.

- [x] `VERSION`, desktop fallback, bundled resource, and both macOS bundle version fields report `0.5.0`; desktop schema remains `6` and Apple Lite identity/version/signing remains unchanged.
- [x] The governed pre-bump 92-test suite passed twice normally and once in reverse-module order; the post-bump source suite, static matrix, exact Material/planning/spILL! oracles, Phase 19B Lite contract, and Apple Lite simulator smoke passed.
- [x] Source and frozen qualification cover Preview/full-output parity, Static/Drift/Pulse and three-Zone behavior, bounded Circuit history, static-base SKRRT, all codec modes and Layer reversal, frame-pipe/PNG/fallback paths, HEIC/HEIF handling, audio, media identity, failure cleanup, source immutability, and exact selected semantic parity.
- [x] The single fresh app build is thin arm64 with 205 Mach-O files, zero dangling links, strict deep ad-hoc codesign, no TeamIdentifier, Bundle ID `com.samhowell.wzrdvid`, and executable SHA-256 `3ecaaa86cf2f49f4ab23497fece3f4d907dc73ad09d6305823c7817e6ff86ab4`.
- [x] Final local DMG: 82,525,127 bytes; SHA-256 `cd4e4c7be0588480e698187ec82bab57682442d37bc9c9a057694ab24b078c85`.
- [x] Final local ZIP fallback: 79,605,131 bytes; SHA-256 `e46afcde714ea1378ccae632fedeb814b87f4d5df65a503b1f12372ce5fb05e6`.
- [x] Both independently generated DMGs and the extracted ZIP match the `dist` app's 669-entry manifest SHA-256 `bb93b4df08d5ec1419c112f90af77ede0456832d838b3fb3d2039e5b18ca5c75`; both DMGs mount with only the app and Applications link and detach cleanly.
- [x] Isolated replacement from the actual published v0.4.0 DMG changes only the app bundle; external settings, ImportedMedia, StillCache, Previews, and recipe files remain hash-identical, and the new app launches from the isolated replacement path.
- [x] Rights-safe temporary Source/Style/Output screenshot candidates were captured from the accepted frozen candidate; deployed v0.4.0 screenshots remain unchanged.
- [x] Paste-ready release notes and exact local artifact evidence are recorded in `docs/V0.5.0_RELEASE_NOTES.md` and `docs/V0.5.0_ARTIFACTS.md`.
- [ ] Run the packaged GUI test with a suitable real Messages/Photos HEIC/HEIF readable/rejection pair when available (`PACKAGED PRIVATE HEIC: MANUAL / NOT RUN`).
- [ ] Human-check Finder DMG presentation and the existing-app **Replace** dialog.
- [ ] Validate normal browser/Finder quarantine and Gatekeeper first-launch behavior; the package remains intentionally ad-hoc signed and unnotarized.
- [ ] Run physical-iPhone Lite source-audio listening and saved-Photos playback only in the separate Apple release context.
- [x] The qualified release-candidate source is prepared for the exact Phase 20 commit and normal push; tagging, publishing, uploading the exact candidate artifacts, fresh-download verification, and site transition remain separately authorized Phase 20R work.

## v0.5.0 Publication Evidence — 2026-08-28

- [x] Release source commit `921f1a198342a2deb78919359a52b3798630e939` was clean and synchronized on `main`/`origin/main` before publication; the lightweight local and remote `v0.5.0` tag resolves exactly to that commit.
- [x] GitHub Release `WZRD.VID v0.5.0` is published, non-draft, and non-prerelease at https://github.com/wzrdgang/wzrdVID/releases/tag/v0.5.0.
- [x] GitHub DMG asset ID `534605869`, 82,525,127 bytes, digest `sha256:cd4e4c7be0588480e698187ec82bab57682442d37bc9c9a057694ab24b078c85`.
- [x] GitHub ZIP asset ID `534605868`, 79,605,131 bytes, digest `sha256:e46afcde714ea1378ccae632fedeb814b87f4d5df65a503b1f12372ce5fb05e6`.
- [x] Fresh public downloads matched both authoritative hashes. The downloaded DMG and ZIP retained the exact executable SHA-256 `3ecaaa86cf2f49f4ab23497fece3f4d907dc73ad09d6305823c7817e6ff86ab4` and 669-entry manifest SHA-256 `bb93b4df08d5ec1419c112f90af77ede0456832d838b3fb3d2039e5b18ca5c75`; both remained thin arm64, v0.5.0, Bundle ID `com.samhowell.wzrdvid`, strict-valid ad-hoc/no-Team packages.
- [x] `/releases/latest` resolves to v0.5.0. An isolated v0.4.0 source environment resolved the real GitHub API state as v0.5.0/newer, displayed the update, exposed Download Update, made exactly one external-open request to the exact v0.5.0 release, and made no download/install/replacement filesystem mutation. An isolated v0.5.0 environment resolved v0.5.0 as current/no-update and retained its visible warning/log when the opener refused.
- [x] Site transition commit `52053e8b4e971a4d50f63de5c3ae3aab9a3073a1` (`Publish WZRD.VID v0.5.0 site`) updated the bounded publication copy, exact DMG/ZIP/release links, JSON-LD, install help, and paired rights-safe Source/Style/Output screenshots without changing desktop or Lite runtime behavior.
- [x] GitHub Pages build `1181352492` built the exact site commit from `main:/docs` in 39,738 ms. Cache-busted live `index.html`, `i18n.js`, and all three screenshots matched committed bytes; `/`, `/lite/`, `/support/`, and `/privacy/` returned HTTP 200, and the live site truthfully reports Published desktop v0.5.0 while preserving Lite as a separate browser product.
- [ ] Run the packaged GUI test with a suitable real Messages/Photos HEIC/HEIF readable/rejection pair when available (`PACKAGED PRIVATE HEIC: MANUAL / NOT RUN`).
- [ ] Human-check Finder DMG presentation and the existing-app **Replace** dialog.
- [ ] Validate normal browser/Finder quarantine and Gatekeeper first-launch behavior; the package remains intentionally ad-hoc signed and unnotarized.
- [ ] Run physical-iPhone Lite source-audio listening and saved-Photos playback only in the separate Apple release context.
