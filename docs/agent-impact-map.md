# wzrdVID Agent Impact Map

This map describes the current repository so future agents can edit with context. It is descriptive, not aspirational. It does not change app behavior.

## 1. Major Modules

### Desktop GUI Shell

- Owning files/directories: `app.py`, `app_i18n.py`, `theme.py`, `assets/ui/`, `assets/branding/`, `assets/logo/`.
- Purpose: PySide6 desktop interface for timeline sources, audio controls, style/effects settings, output controls, preview rendering, preview/cache cleanup, recipe import/export, batch render, and logs.
- Inbound dependencies: `run.py`, `run.sh`, `run_windows.bat`, user file selections, drag/drop events, saved settings JSON, recipe/project preset JSON.
- Outbound dependencies: `state_contract.py`, `renderer.py`, `ffmpeg_utils.py`, `presets.py`, Qt widgets/styles/assets, local filesystem, temp preview/output folders.
- High-risk notes: UI controls feed render settings and audio behavior. Small copy/style changes are usually safe; widget wiring, settings keys, Zone identity/geometry/assignment handling, thread behavior, table columns, cache cleanup safety boundaries, and localization keys can break render, save/load, cleanup, spatial containment, or audio mix flows.

### Desktop Persisted State Contract

- Owning file: `state_contract.py`.
- Purpose: one stdlib-only source of truth for schema 6, schema-3/4/5 migration, canonical fresh/Reset state, load normalization, deterministic serialization preparation, malformed state repair, persisted effect defaults, Zone definitions/eligibility/normalization, codec Layer identifiers/order normalization, Style FX persisted normalization, max-length load repair, and compatible audio/transition identities.
- Inbound dependencies: raw settings/recipe dictionaries and plain UI-collected dictionaries from `app.py`; Zone/Layer/Style state imports from `renderer.py`; direct tests in `tests/test_state_module_contract.py`.
- Outbound dependencies: Python stdlib only. Import direction is `app.py`/`renderer.py` -> `state_contract.py`; the state module must never import Qt, `app.py`, `renderer.py`, `datamosh.py`, `ffmpeg_utils.py`, media probing/decoding, or filesystem/user-data ownership.
- High-risk notes: keep persisted schema exactly 6 unless a separately authorized schema phase changes it. State edits require direct schema-3/4/5/6, malformed/default/Reset/canonicalization/idempotence tests plus isolated offscreen MainWindow settings or recipe integration. Runtime render planning, media inspection, widget mutation, and worker orchestration remain outside this module.

### Desktop Regression Foundation

- Owning files/directories: all `tests/test_*.py` modules and deterministic generated helpers under `tests/fixtures/`.
- Purpose: preserves the authoritative 18-case v0.4.0 Full Frame Material oracle, same/changed-seed Material behavior, binary Random Noise B/W output, five frame-effect Zone containment/order/material isolation, Circuit Bending Zone history/reset, schema-3/4/5/6 migration and malformed repair, exact Zone eligibility, isolated state round-trip/Reset, labeled CURRENT-versus-ACCEPTED canonical full-output/Preview planning semantics, controlled MPEG-4 I/P structure, deterministic DATAMOSHING, exact canonical spILL! intensity/ancestry/recovery, SKRRT Full Frame/Zone provenance, ShShSHa multi-time provenance, FLOWs transition-only behavior, strict auxiliary validation, historical/alternate Layer plans and last-writer semantics, duplicate/unknown rejection, representative protected intervals and mode-local recovery, one main encode/one safe transcode, default pipe/forced PNG/eligible fallback classification, codec/Zone no-fallback failures, H.264/yuv420p/AAC identity, source immutability, and temporary cleanup.
- Fixture/data boundary: all frames and tiny media are generated at runtime with NumPy/OpenCV/Pillow and ffmpeg inside task-owned `TemporaryDirectory` roots; offscreen GUI state patches only startup checks. The suite uses no network, private media, real user settings, committed media/evidence, package artifacts, or release assets, and writes no repository output.
- Command: from repository root, run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_*.py'`. Run it twice when its tests, fixtures, or oracle definition change.
- High-risk notes: the accepted serialized Material oracle SHA-256 is `441f9150b0f8c2d79fadb5a653a4b930d777959c37e458099a3b28eee3baa80a`; canonical spILL! Low/Medium/High changed/recursive/max-depth counts are `10/0/0`, `42/16/4`, and `60/60/7`. Do not regenerate or weaken accepted behavior to accommodate a production change. Expensive auxiliary stress, long-form/performance, frozen/package, DMG, subjective/real-media, and quarantine validation remain qualification-only.

### Render Engine

- Owning files/directories: `renderer.py`, `datamosh.py`, `presets.py`.
- Purpose: Builds a virtual media timeline from videos/photos, samples frames, prepares cached still/HEIC proxies, applies framing/effects/bypass/ANSI/chunky rendering, writes frames, and coordinates final video output. The optional desktop `Style begins at` gate uses absolute rendered-output time: earlier frames receive clean source framing only, while the first eligible frame and all later frames use the existing full WZRD treatment. Preview windows carry their absolute output offset into the renderer, and random clip assembly remains gated by assembled output time rather than source timestamps. Inside the styled portion, the shared post-pipeline artifact stage can process ANSI/text-art, chunky/WZRD Blocks, PUBLIC ACCESS, and normal/bypass frames. Its five v0.3.0 frame-domain effects run after the existing transition in fixed order—Pixel Sorting, Databending, Circuit Bending, Hex Editing, then Random Noise B/W—before the unchanged ending/loop stage; each retains an independent fixed numeric salt with the Weirdness seed and absolute output frame index. Each of those five effects may independently use Full Frame or one of up to three schema-6 static named Zones in normalized final-output coordinates. Full Frame stays on the literal pre-Zones path. A Zone floors its normalized x/y start, ceils x+w/y+h, clips the half-open rectangle to the output, computes material analysis and bounded luma/RGB history only for that ROI, runs the existing effect against a Zone-local candidate, validates its shape/dtype/writeability, and replaces only that ROI. The five effects keep their fixed order, so a later effect wins where assigned Zones overlap. SKRRT may also use one existing Zone assignment, but it does so later at the authentic codec stage; ShShSHa, the other codec modes, and all other Style effects remain Zone-ineligible. Their render-local choreographer evolves one bounded deterministic instability signal from enabled-effect material scores, transitions, intensity, seeded slow drift, and prior state, then applies effect-specific wandering response, irregular event duration/cooldown, transition aftershock, and incomplete baseline recovery without synchronizing the five grammars. Luminance, directional Sobel edges, magnitude, texture, motion, brightness, channel spread, and spatial focus are computed only when an enabled effect requests them. Full Frame analysis retains at most the prior luminance frame, while Circuit Bending may also retain only the immediately previous pre-effect styled frame; Zone histories are bounded to the active normalized rectangles. Those histories plus instability, ambient dwell, active events, and cooldowns reset for every render/preview/fallback attempt and at both edges of every Style FX-clean interval. ASCII ANSI presets use per-render glyph masks to avoid repeated `ImageDraw.text` glyph rasterization while preserving text-art pixels; chunky/Unicode glyph rendering stays on the direct text path. The direct raw RGB ffmpeg frame pipe is the default video transport before the same audio/finalization stages. Legacy PNG frame staging remains available through the local desktop developer opt-out or `WZRDVID_FORCE_PNG_STAGING=1`, and is still used automatically if pipe/encode transport fails before audio muxing. Source media access/decode errors and Zone/render-contract errors, including HEIC/HEIF macOS privacy denials, are not retried through PNG staging.
- Inbound dependencies: `app.py` render settings, timeline items, user selected output path, source media files, Effect Intensity, Weirdness seed, the persisted five-mode codec Layer sequence, absolute output/preview position, and the same final anonymous transition tuple and fitted-material activity used by the codec modes.
- Outbound dependencies: OpenCV, Pillow, numpy, ffmpeg helpers, optional `datamosh.py` codec stage, temporary frame directories, output MP4 files.
- High-risk notes: Rendering touches timing, frame counts, max-length caps, random clip segment planning, still proxy cache behavior, temp cleanup, EXIF photo orientation, bypass intervals, text glyph-mask caching, transitions/endings, material-event scheduling, Zone rasterization/containment/overlap, lazy analysis, bounded prior-frame state, optimization, long-media warning logs, stage timing logs, experimental pipe fallback, and audio duration expectations. Validate the byte-exact Full Frame frame-effect and SKRRT paths; Zone containment and outside-material isolation for all six eligible effects; same/different/overlapping frame-effect Zone order; bounded frame-effect Zone analysis/history; SKRRT exact prepared provenance plus decoded leakage/recovery; invalid candidate failure; disabled no-op behavior; Low/High and seed differences; material/transition responsiveness; exact binary B/W output; Style/preview/random/still boundaries; state/temp cleanup; event/visual evidence; longer performance; final codec/audio; and a fresh frozen packaged render after edits.

### Desktop Style FX Coverage

- Owning files/directories: `app.py`/`app_i18n.py` for controls, persistence, preview-map shifting, and user-facing copy; `renderer.py` for interval construction, source-stage frame gating, and temporal resets; `datamosh.py` for codec protection.
- Purpose: Independently marks output-timeline intervals where every optional desktop Style checkbox is off. Full effects is the backward-compatible default; random clean sections, manual clean time blocks, and their union use a dedicated persisted seed/percent/map that does not change ANSI Coverage, Weirdness, Layer order, transitions, endings, framing, Loop, source selection, or audio. Preview computes the full-output map first and shifts only its overlap into preview-local time, while Random assembly builds the map against the assembled output duration and `Style begins at` remains the outer gate.
- Boundary contract: frame-domain effects receive an empty effect map at their existing source stage; stutter holds, material-event choreography, prior luma/RGB, and codec activity history reset on both sides of every clean interval. The same half-open intervals become integer frame ranges on the rendered clock. Each enabled `DatamoshOperation` carries those ephemeral protected ranges; their edges are forced clean I anchors in the one existing controlled MPEG-4 encode, and General, spILL!/Overflow, SKRRT, ShShSHa/Scatter, and FLOWs/Bleed planning rejects protected sources, targets, persistence, and prepared windows. The shared one-safe-transcode/audio-finalization architecture is unchanged, and a fully protected eligible window skips the codec stage entirely.
- State/compatibility: current schema is 6. The optional `style_fx_coverage_mode`, `style_fx_manual_blocks`, `style_fx_random_percent`, and `style_fx_random_seed` fields retain their schema-5 behavior. Missing or malformed mode/blocks fail safe to Full effects/empty blocks. The visible transition label `None` maps to the stable internal/persisted `Hard Cut`; legacy state therefore loads as `None` without changing renderer identity.
- Required validation: A-H Full/manual/random/combined/ANSI-independence/Style-begin/absolute-preview/Loop matrix; seed isolation and reroll determinism; source-stage equality of clean frame regions to disabled-effect rendering; hard temporal reset checks; all-five codec protected source/target/window/recovery evidence; exactly one main controlled encode and one safe transcode when codec events apply, zero codec passes for 100% clean; default Full byte compatibility; save/load/reset plus malformed schema-3/4/5/6 migration; direct-cut/Random transition semantics; GUI accessibility/one-checkbox branding; H.264/yuv420p/AAC source and frozen-package renders.

### Authentic Datamosh Modes Codec Stage

- Owning files/directories: `datamosh.py`, with a narrow call site in `renderer.py`; five separate default-off activation flags plus one canonical five-identifier Layer order live in `app.py`/`app_i18n.py`.
- Purpose: When any codec mode is enabled, the completed silent visual intermediate is encoded once as a controlled video-only MPEG-4 Part 2 elementary `.m4v` stream, linearly parsed as `00 00 01 B6` VOP units, planned without dependence on the user's execution permutation, processed by explicit deterministic operations in the saved Layer order, and transcoded once to a validated silent H.264/yuv420p MP4 before any existing audio path runs. General DATAMOSHING retains its transition plus background reset/persistence grammar. Overflow selects shot-local motion peaks from anonymous rendered-material activity and uses restrained fixed-source accumulation at Low. At Medium/High, deterministic selected episodes may instead form bounded decaying recursive cascades: each rewritten whole P-VOP becomes the legitimate source available to the next target at Overflow's Layer position, fresh native P payloads periodically restart ancestry, and an untouched mode-local I-VOP is reserved for reacquisition. This remains prediction mutation, not alpha compositing, decoded-frame duplication, Motion Melt, optical-flow warping, ghosting, or frame blending. SKRRT selects sparse motion-led shot-local episodes and remuxes the controlled stream once for keyframe-indexed bounded access. Full Frame losslessly extracts only short source windows and encodes them in reverse order exactly as before. With a Zone assignment, SKRRT instead decodes bounded current and source windows from that same controlled stream, starts every full-size writable RGB auxiliary frame from the exact current frame, replaces only the rasterized half-open Zone with the exact reverse-chronological source frame, proves inside/outside equality and source immutability, and auxiliary-encodes the resulting full-size sequence. Both paths inject only auxiliary P-VOP material at SKRRT's saved Layer position before the same mode-local recovery anchor. Scatter selects materially active shot-local episodes, uses anonymous normalized material-led regions and at least two distinct non-current nearby offsets to assemble coherent multi-time composite frames from bounded decoded neighborhoods, normalizes every trimmed branch to the exact integer output-frame clock before timestamp-synchronized overlays, auxiliary-encodes each exact-count prepared episode as one I followed by P prediction, and injects only those P-VOPs at Scatter's Layer position before a mode-local recovery anchor. Both auxiliary modes use the controlled stream, never a preceding Layer mutation; they retain the native MPEG-4 encoder policy with B frames disabled, GOP `N+1`, maximum positive scene-change threshold, strict GOP, and one thread, then share the unchanged fail-closed parser contract requiring exactly `I=1`, `P=N-1`, `B=0`, `S=0`, with I only at index zero. Bleed only acts on the final anonymous source-transition map and consumes the then-current outgoing P payload at its Layer position when available.
- Operation contract: one normalized tuple contains each known mode exactly once. The historical default is `datamoshing`, `overflow`, `skrrt`, `scatter`, `bleed`; disabled modes retain their tuple position but are omitted from execution. Every enabled `DatamoshOperation` explicitly carries mode identity, intensity, seed, independent salt, Layer-derived order, local temporal start/end, absolute frame offset, transition inputs, optional anonymous activity samples, optional ephemeral Style FX protected intervals, mode parameters, frozen planned events/source identities, and optional render-local prepared SKRRT/Scatter windows. Planning replays the established historical composition only in memory to keep each mode's validated event targets and temporal identities fixed across permutations; ordered application still writes whole VOPs sequentially, and the last writer wins. General, fixed-source Overflow, and Bleed normally read their planned source P from the then-current Layer stream. A recursive Overflow event first consumes an already-written preceding Overflow replacement when that target is its planned source, otherwise it consumes the then-current native/captured P available at that Layer position; it never reads a later Layer result. If moving General later leaves a historically selected source frame as I at an earlier operation's Layer position, a narrow render-local captured historical P payload preserves that already-validated source/target plan instead of silently dropping or retargeting the event. No planning bytes or protected intervals persist to project state or contain a source path. Compatible operations still share one controlled encode and one safe transcode, and final VOP count/type invariants are revalidated. Any duplicate, unknown mode, auxiliary count/type violation, protected-window violation, or ordered-handler failure raises `DatamoshError` before a final output is accepted.
- Inbound dependencies: `renderer.py` silent H.264 intermediate, normalized saved codec Layer order, output fps/frame count and dimensions, Effect Intensity, Weirdness seed, absolute preview/output offset, `Style begins at`, Loop Friendly, existing CRF/target-bitrate planning, and an ephemeral anonymous transition tuple containing only local/absolute output frame, source kinds, and visual transition name. Overflow receives local/absolute frame plus sanitized scalar motion activity from the same fitted-material analysis family used by the Style choreographer. SKRRT receives the same activity plus optional normalized global phase-shift x/y/confidence scalars computed only while SKRRT is enabled; it does not retain optical flow. Scatter receives lazy scalar texture/edge/motion measures plus a bounded tuple of normalized coarse material-led regions computed only while Scatter is enabled. No path, full-resolution image sequence, or persistent identifier crosses that boundary; Layer order is persisted, while transition/activity/planning metadata remains render-time-only.
- Outbound dependencies: existing `ffmpeg_utils.py` binary discovery/command runner, system ffmpeg native `mpeg4` and lossless `ffv1` encoders and ffprobe, a nested `datamosh/controlled_prediction.m4v`, `datamosh/manipulated_prediction.m4v`, optional shared `datamosh/temporal_preparation/indexed_prediction_source.mp4`, bounded `temporal_preparation/skrrt/` forward-window/reverse-prediction files, bounded `temporal_preparation/scatter/` neighborhood/composite/prediction files, and `datamoshed_silent.mp4` inside the app-owned `wzrd_vid_render_*` temporary directory. Scatter provenance decodes only the representative prepared frame and its selected source frames to transient raw RGB files, removes them immediately after hashing/comparison, and records no path. No persistent cache or user source is written.
- Error boundary: `DatamoshError` identifies intermediate encode, invalid/truncated/no-VOP structure, unknown operation, SKRRT indexing/window extraction/auxiliary encode/transform, Scatter bounded extraction/fragment construction/auxiliary encode/transform, manipulated-stream decode/transcode, or safe-output validation failures. A Scatter construction count failure includes sanitized operation/window, neighborhood and trim ranges, fps, and exact frame-clock policy without a user path. These errors propagate after frame rendering; they must not trigger PNG fallback, silently disable a codec mode, substitute a frame-domain effect, or claim success. The outer render temporary directory cleans success and failure artifacts.
- Boundary/loop behavior: the pre-style prefix is protected, the first styled frame is forced to a clean I anchor, deterministic events are eligible only after it, preview decisions preserve absolute output transition frames, every Style FX clean interval forces clean I anchors at its half-open edges and excludes codec source/target/window planning, and Loop Friendly forces a clean tail anchor at the start of the renderer's actual loop-blend window instead of protecting an unnecessarily large arbitrary final GOP. Very short or fully Style-FX-protected eligible suffixes can skip/log no codec event and keep the already-rendered silent intermediate.
- Required validation: normalized persistence/migration/reset and malformed duplicate/unknown handling; exact six-row Zone allowlist with only SKRRT added among codec modes; parse rejection; exact I/P-only controlled maps; hundreds of repeated auxiliary encodes spanning current window sizes and varied static/motion/cut/texture/noise/compression material with exact one-I-at-zero/P-only structure and deterministic bytes; exact one-main-encode/saved-order operations/one-safe-transcode counts; byte-exact historical-default/Low Overflow and Full Frame SKRRT output; meaningful overlapping Layer permutations with invariant per-mode event/parameter/auxiliary plans, distinct writer chronology/final attribution/elementary and decoded hashes, no controlled-byte restoration, and same-order repeat determinism; legacy DATAMOSHING byte compatibility; Overflow static/slow/fast/expanding/contracting material response plus fixed/chained/decaying/burst comparison, recursive source ancestry, evolving payload identities, decoded sequence review, bounded chain depth, clean I recovery, and Low/Medium/High coverage differences; SKRRT static calmness, opposite-direction response, explicit reverse source order/hash/main targets/recovery, bounded decode/auxiliary encode/structural-validation/temp footprint, exact Zone prepared provenance, measured decoded leakage/recovery across representative geometry, and Low/Medium/High depth/persistence/spacing/coverage differences; Scatter exact per-branch integer frame clocks and composite counts across millisecond and exact-CFR inputs, objective multi-time per-region provenance, material-led spatial response, static calmness, coherent attack/fragmentation/partial-resolution/recovery, bounded neighborhoods/auxiliary preparation/structural-validation/temp footprint, and Low/Medium/High fragment/area/depth/persistence/spacing differences; Bleed first/middle/last transition-only behavior and then-current source evidence; reset suppression plus P persistence; exact decoded frame count and duration within one frame; Style/preview/random/loop boundaries; source hashes and temp cleanup; intermediate ordered-handler plus mode-specific/malformed-auxiliary failure injection with no PNG fallback; Phase 2 independence; default/forced/fallback transports; H.264/yuv420p and AAC/PCM timing; longer 960x540/1280x720 performance; long-form scheduler/flow stress; and fresh PyInstaller frozen-module renders in historical and substantially different orders.
- Layer recovery note: recovery anchors remain mode-local untouched positions. Overflow reserves its own selected recursive-flow I anchors against later Overflow episodes, but neither it nor another mode writes controlled bytes there as a global lock; another Layer may still target the same frame under the existing last-writer contract. Style and Loop protection remain the only global boundary constraints.

### Still Image Cache

- Owning files/directories: `still_cache.py`.
- Purpose: Loads still images, handles EXIF transpose/RGB conversion, decodes HEIC/HEIF sources through ffmpeg, writes app-managed proxy PNGs under `StillCache`, and enumerates managed still-cache cleanup targets.
- Inbound dependencies: `app.py` photo validation/preview/cache cleanup, `renderer.py` still timeline frame loading, source still files, optional `WZRDVID_STILL_CACHE_DIR`.
- Outbound dependencies: Pillow, `ffmpeg_utils.extract_still_frame()`, platform user config/application-support paths, generated proxy PNGs under `StillCache`.
- High-risk notes: Cache keys include resolved source path, size, mtime, and proxy size. Mistakes can cause stale proxies, repeated slow HEIC decodes, excessive cache growth, or unsafe cleanup target selection. Run syntax checks plus focused HEIC/still import, render, and cache cleanup smokes after edits.

### ffmpeg and Media Utilities

- Owning files/directories: `ffmpeg_utils.py`.
- Purpose: ffmpeg/ffprobe discovery, duration/stream probing, timecode parsing, video encoding, audio trim/mux/mix, source timeline audio construction, H.264/AAC optimization, and file-size targeting.
- Inbound dependencies: `app.py`, `renderer.py`, user-selected video/audio files, render duration and output-size settings.
- Outbound dependencies: system `ffmpeg`/`ffprobe`, subprocess calls, temp files, MP4/AAC outputs.
- High-risk notes: Path quoting, spaces, video-container audio, audio offsets, source audio mixing, probe cache correctness, and two-pass optimization depend on this file. `probe_media()` caches ffprobe metadata in-process by resolved path, mtime, and size; preserve helper signatures and avoid mutating returned probe dictionaries in place. Avoid `shell=True` unless absolutely necessary.

### Launchers and Source-Run Support

- Owning files/directories: `run.py`, `run.sh`, `run_windows.bat`, `requirements.txt`, `docs/CROSS_PLATFORM.md`.
- Purpose: Launch from source on macOS/Linux/Windows and document best-effort cross-platform behavior.
- Inbound dependencies: user shell/Python environment.
- Outbound dependencies: project virtualenv, Python executable, Python dependencies, ffmpeg installed on PATH or common macOS Homebrew paths.
- High-risk notes: Keep shell assumptions isolated to platform-specific helper scripts. `run.py` should stay shell-neutral.

### macOS Build and Release Packaging

- Owning files/directories: `build_app.sh`, `scripts/package_dmg.sh`, `scripts/package_release.sh`, `scripts/generate_icon.py`, `scripts/generate_logo.py`, `scripts/generate_branding.py`, `scripts/generate_ui_textures.py`, `assets/wzrd_vid.*`, `VERSION`, `WZRD.VID.spec` when generated locally.
- Purpose: Build `dist/WZRD.VID.app`, prune PyInstaller/Qt payload, generate icons/branding/textures, ad-hoc sign the macOS app, create the conventional `WZRD.VID.app` plus `Applications -> /Applications` read-only DMG, and retain `WZRD.VID-macOS.zip` as a fallback release artifact.
- Inbound dependencies: local macOS shell, Python virtualenv, requirements, `VERSION`, source assets.
- Outbound dependencies: `build/`, `dist/`, `.venv/`, `.pyinstaller-cache/`, generated icon/texture/branding files, `WZRD.VID-macOS.dmg`, and the fallback release ZIP.
- High-risk notes: macOS packaging is primary distribution. Do not change app name, icon paths, PyInstaller excludes, pruning rules, bundle metadata, signing identity, or mount cleanup casually. Post-PyInstaller Qt pruning uses an explicit framework allowlist and removes only the corresponding top-level Frameworks/Resources companion links plus the deliberately pruned translations companion before final signing. The build rejects any remaining dangling symlink and then runs strict codesign verification. The DMG packager repeats those link/signature/identity gates on source, staged, and mounted copies, allowlists top-level image contents, mounts only below its unique temporary tree, and detaches only its own captured device. Preserve these gates and do not restore unused Qt payload, globally delete unrelated links, strip quarantine, or make the DMG write into `/Applications`.

### GitHub Pages Landing Site

- Owning files/directories: `docs/index.html`, `docs/styles.css`, `docs/i18n.js`, `docs/CNAME`, `docs/assets/`, `docs/support/index.html`, `docs/privacy/index.html`, `docs/RELEASE_DOWNLOAD_HELP.md`, `docs/RELEASE_CHECKLIST.md`.
- Purpose: Static landing/download/support/privacy pages for `wzrdvid.com` and GitHub Pages, with release links, demo media, screenshots, Lite link, App Store support/privacy routes, and source/download guidance.
- Inbound dependencies: GitHub Pages configured to deploy branch `main` folder `/docs`, custom domain DNS, static assets copied under `docs/assets/` or referenced from repository paths that resolve on Pages.
- Outbound dependencies: browser rendering, GitHub Releases latest URL, GitHub repo URL, `docs/CNAME` custom domain.
- High-risk notes: `docs/CNAME`, root-relative paths, and release links can break the public site. Do not change Pages config or domain copy without deployment-related intent.

### WZRD.VID Lite Browser App

- Owning files/directories: `docs/lite/index.html`, `docs/lite/styles.css`, `docs/lite/app.js`, `docs/i18n.js`, `docs/lite/README.md`.
- Purpose: Browser-only, static WZRD.VID Lite prototype for local 15/30/60-second chaos cuts using drag/drop, Canvas, Web Audio, and MediaRecorder. Its single global `Include Source Audio` control defaults on and follows source-video sound through the assembled visual cuts. It does not upload user files.
- Inbound dependencies: browser file inputs/drop events, local media selected by user.
- Outbound dependencies: object URLs, Canvas, Web Audio, MediaRecorder, downloaded blob output, local Reset/Clear Project state release, and Apple Lite native Photos save handoff when running inside the iOS wrapper.
- High-risk notes: Privacy copy and no-upload behavior are product boundaries. Source audio must use the exact final visual segment/source-time map; still/image and silent-video segments are source-bus silence. Source plus explicit Add Audio must remain one mixed MediaRecorder audio track. The page reuses one AudioContext, retains safe cached MediaElementSource ownership for persistent source videos, uses short anti-click gain ramps, and cleans per-render buses/playback on completion or reset. iOS mixed Add Audio uses a decoded Web Audio buffer so source-video playback cannot stop a competing media element. Lite accepts HEIC/HEIF by extension, but decode support is browser/WKWebView-dependent and does not use the desktop ffmpeg still-cache path. Lite clears selected media/audio/rendered blobs through the browser runtime and should revoke object URLs when resetting. Lite already avoids desktop-style PNG frame staging by drawing to Canvas and recording via MediaRecorder. Grep for network APIs after edits: `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`.

### Static Assets and Branding

- Owning files/directories: `assets/branding/`, `assets/logo/`, `assets/ui/`, `assets/demos/`, `assets/screenshots/`, `docs/assets/`, generator scripts.
- Purpose: Official branding, app icon, README/site graphics, demo media, screenshots, and reusable UI texture assets.
- Inbound dependencies: generator scripts and manually approved media.
- Outbound dependencies: desktop app stylesheet/icons, README, GitHub Pages site, release/social assets.
- High-risk notes: Branding is reserved by `LICENSE` and `NOTICE.md`. Do not delete intentional official logo/banner assets. Do not commit large or copyrighted sample media.

### Documentation, Legal, and Contribution Surface

- Owning files/directories: `README.md`, `LICENSE`, `NOTICE.md`, `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `docs/*.md`, `examples/README.md`.
- Purpose: Public product explanation, source-available license terms, brand reservation, release instructions, cross-platform notes, and contribution/security guidance.
- Inbound dependencies: product direction and current repo behavior.
- Outbound dependencies: GitHub readers, contributors, users downloading releases/source.
- High-risk notes: Keep source-available language consistent. Do not reintroduce AGPL/open-source claims or stale fantasy/old-name branding.

## 2. Application Flows

### Desktop App Launch

- Entry point: `python run.py`, `python app.py`, `./run.sh`, `run_windows.bat`, or macOS `dist/WZRD.VID.app`.
- UI/component path: `app.py` creates the PySide6 application and main window; `theme.py` supplies stylesheet/assets.
- Data/state path: `app.py` loads settings from `_user_data_dir()` (`WZRD.VID/settings.json` under the platform user config/application-support location), passes raw persisted dictionaries through `state_contract.py`, then applies canonical values to widgets.
- Localization path: `app_i18n.py` resolves the UI language and falls back to English for missing keys; selected `ui_language` persists in local settings.
- Asset/media path: app icon and UI/branding assets under `assets/` when running from source or bundled by PyInstaller.
- Success behavior: Main window opens with Source, Style, and Output tabs.
- Failure/empty behavior: Missing ffmpeg/ffprobe is surfaced in the GUI/log with platform-specific install guidance.
- Files likely involved in changes: `app.py`, `theme.py`, launchers, `ffmpeg_utils.py`, `build_app.sh`.

### Desktop Source Import and Timeline

- Entry point: Add Video(s), Add Photo(s), drag/drop onto timeline, recipe import or legacy project preset load.
- UI/component path: `app.py` timeline widgets, `MediaDropTableWidget`, timeline item table columns, preview controls.
- Data/state path: `TimelineItem` records path, kind, duration, trim, photo hold, `has_audio`, and `include_audio`; project JSON preserves timeline order and item settings. Protected HEIC/HEIF imports may store an app-cache path plus a `display_name` that preserves the user's original filename.
- Asset/media path: user selected videos/photos, including desktop `.3gp` and `.3g2` video containers; readable HEIC/HEIF files from likely protected Messages/Photos containers are copied into app-owned `ImportedMedia`; photos are corrected for EXIF orientation through Pillow handling in the render/preview path.
- Success behavior: Items append to timeline, durations are shown, video audio is detected, Include Audio defaults appropriately, preview updates. `.3gp` and `.3g2` follow the same desktop visual-video path as other supported video containers across picker, drop, recipe restore, preview, and render. Normal HEIC/HEIF stills can be selected from the normal media picker and defer full decode until preview/render, where cached app-managed still proxies are reused. HEIC/HEIF stills from likely macOS protected Messages/Photos paths are internalized into `ImportedMedia` when WZRD.VID can read/copy them, while the timeline continues to show the original filename. Protected HEIC/HEIF internalization uses staged app-cache copies and can fall back from metadata-preserving copy to content-only or Qt file copy before rejecting the import.
- Failure/empty behavior: Unsupported media or probe/load failures are logged and shown as clear GUI errors. If protected HEIC/HEIF internalization cannot copy the selected file, import rejects that item with copy/export guidance and continues with other selected files. Render preflight remains fallback safety for recipes and older timelines that already reference protected paths.
- Files likely involved in changes: `app.py`, `renderer.py`, `ffmpeg_utils.py`.

### Desktop Audio Import, Source Audio, and Mixing

- Entry point: Select Music/Audio, drag/drop audio/video-with-audio, Audio Mix mode, Include Audio checkboxes.
- UI/component path: `app.py` audio controls, timeline Include Audio column, volume sliders, music trim/offset fields.
- Data/state path: settings/project JSON preserve external audio path, trims, offset fields, audio mix mode, volumes, and per-item include-audio flags.
- Asset/media path: external audio files or video containers with audio tracks, including `.3gp` and `.3g2`; source timeline video audio; silence for photos or disabled/no-audio video rows.
- Success behavior: Final MP4 can be silent, external-only, source-only, or external plus selected source audio, encoded as AAC when audio exists. Music trim start/end select the requested range inside the external audio file; Music start/end in video place the external read window inside the rendered output timeline without treating placement as a source trim offset. In External + selected source audio mode, selected source audio can still play from the timeline start while external music is delayed to its placement point. Worky music mode must preserve that placement delay before its mono/downsample texture processing.
- Failure/empty behavior: Selecting a file with no audio stream reports `Selected music file has no audio track.`; match-to-music disables unsafe source-audio mixing according to current app behavior.
- Files likely involved in changes: `app.py`, `ffmpeg_utils.py`, `renderer.py`, README/docs.

### Desktop Render, Preview, Batch, and Export

- Entry point: Preview 5 Seconds, MAKE VIDEO, MAKE BATCH.
- UI/component path: `app.py` collects render settings and starts `RenderThread` or `BatchRenderThread`; progress/log signals update GUI.
- Data/state path: `RenderSettings`, `PlaybackPlan`, optional `style_begin_time`, preview-only `output_time_offset`, optional `max_video_length`, optional `random_clip_assembly`, bypass intervals, random seeds, style/output/optimization/framing/effect settings, up to three normalized static `zones`, six optional `effect_zone_assignments`, the canonical five-identifier `codec_layer_order`, plus a non-persistent anonymous transition map derived after final sequential/random playback planning and non-persistent lazy frame analysis/event state derived during the styled render. The generic schema-version-6 `effects` dictionary remains the sole activation truth for the five DATAMOSH MODES plus the five v0.3.0 frame-effect flags. Assignments affect only Pixel Sorting, Databending, Circuit Bending, Hex Editing, Random Noise B/W, and SKRRT and default to Full Frame. SKRRT assignment remains independent of activation and Layer position; ShShSHa and all other codec modes ignore Zone keys. The separate optional `codec_layer_order` list controls codec order only; schema-3/4/5 state loads no Zones/Full Frame, while missing or malformed schema-6 Zones/references are normalized once. No material metric, temporal preparation, spatial fragment, event plan, Zone analysis/history, or auxiliary byte is saved. Blank or `auto` max video length means no cap/full selected timeline; random clip assembly uses that selected timeline duration unless an explicit max length is provided.
- Asset/media path: source media, temp frame directories and optional nested DATAMOSH MODES controlled/manipulated/temporal-preparation material, preview folder under app settings parent, user-selected output path, optional optimized output path.
- Success behavior: Normal MP4 visually renders ANSI/text-art/glitch output, optional `Style begins at` keeps output frames before its non-negative timestamp clean and starts a fresh material-event system at/after the boundary, optional max-length caps output duration, optional random clip assembly builds deterministic seeded source segments before rendering, optional audio is muxed/mixed independently of the visual gate, optional optimization targets max MB, output/open-folder controls become available. Enabled Pixel Sorting, Databending, Circuit Bending, Hex Editing, and Random Noise B/W retain subtle effect-specific baselines but develop deterministic material/transition-driven episodes with different timing and spatial behavior; their order, controls, independent salts, and schema-5 persistence remain unchanged and are not part of codec Layer. Enabled DATAMOSH MODES execute in the exact normalized saved Layer order on the completed silent visual output after all frame-domain effects/transitions/endings and before unchanged audio handling; disabled modes keep their saved position and do not execute, while all-off adds no codec round trip. The default remains DATAMOSHING -> Overflow -> SKRRT -> Scatter -> Bleed. Existing visual presets and Weird rerolls inherit/preserve explicit user order rather than resetting or randomizing it. Full Frame SKRRT retains the prior direct reverse-window path byte-for-byte. Zone SKRRT and Scatter preparation continue from the controlled stream and remain limited to selected local source windows; the former composes full-size current-frame auxiliaries with only the assigned Zone replaced by reverse source pixels, while the latter remains nonspatial. Layer adds no second WZRD render, main controlled encode, or safe transcode. Preview rendering compares the gate and transition events against the preview window's absolute output time while preserving the saved Layer sequence. `0:00` preserves all-styled behavior; a gate at/after the output end keeps all rendered frames clean. Blank/auto Max Video Length stays blank in saved settings and support/render reports unless the user explicitly types a cap; old no-op saved values that match or exceed the selected timeline normalize back to auto. By default the silent MP4 streams rendered RGB frames directly to ffmpeg through the frame-pipe transport. Legacy PNG frame staging can be forced by local desktop developer setting or `WZRDVID_FORCE_PNG_STAGING=1`, and the renderer falls back to PNG staging only on pre-audio pipe/encode transport failure. Preview MP4s and still/HEIC proxies under app-owned cache folders can be cleared manually, and old app-managed preview/cache/temp files are cleaned best-effort at launch.
- Failure/empty behavior: Random clip assembly with match-to-music should reject before render; blank/auto max length uses the selected timeline duration. HEIC/HEIF stills that need ffmpeg decode are preflighted before frame rendering so inaccessible protected-path sources fail before frame 1 with the filename/path and copy/export guidance. DATAMOSHING failures stop at their own post-render/pre-audio boundary and never invoke frame-pipe PNG fallback. Exceptions are logged and surfaced without freezing the GUI; temp directories should clean themselves up. Preview/cache cleanup failures should log and continue without deleting user-selected final exports, source media, or recipes.
- Files likely involved in changes: `app.py`, `renderer.py`, `ffmpeg_utils.py`, `presets.py`, `theme.py`.

### Export/Import Recipes

- Entry point: Export Recipe, Import Recipe.
- UI/component path: `app.py` project controls.
- Data/state path: user-selected recipe JSON files; app settings store recent/default values. `state_contract.py` owns the pure migration/default/repair/canonicalization boundary before MainWindow widget application and after UI state collection. Schema version 6 adds optional `zones` and `effect_zone_assignments`; missing fields and schema-3/4/5 state restore no Zones/Full Frame. Schema version 5 added optional `codec_layer_order`; exact valid order restores, missing/wrong-type values use the historical order, duplicates/unknowns are removed, and missing known modes are appended historically. Schema version 5 also added `style_begin_time` as entered text; recipes/settings without the field load it as `0:00`. Schema version 4 added `max_video_length` as entered text and `random_clip_assembly` as a boolean; those missing fields still load as blank/false.
- Asset/media path: recipe JSON references user media paths but does not copy media.
- Success behavior: Timeline, audio, Style begins at, max-length/random assembly controls, style/effects, exact codec Layer order, framing, bypass, output, batch, seeds, and optimization controls restore. Existing presets do not own or randomize codec Layer order.
- Failure/empty behavior: Missing referenced media, invalid recipe JSON, or older project preset JSON should be reported through GUI/log.
- Files likely involved in changes: `app.py`, docs.

### GitHub Pages Landing/Homepage And Static Support/Privacy Pages

- Entry point: `docs/index.html` at GitHub Pages root or `wzrdvid.com`; `docs/support/index.html` at `/support/`; `docs/privacy/index.html` at `/privacy/`.
- UI/component path: static HTML/CSS in `docs/index.html` and `docs/styles.css`.
- Data/state path: none; all static.
- Localization path: `docs/i18n.js` applies `data-i18n` text and stores only the UI language preference in localStorage.
- Asset/media path: `docs/assets/` and release/repo links.
- Success behavior: Users see hero, demo, screenshots, download links, Lite link, rights/source notes, footer, and App Store-prep support/privacy pages for WZRD.VID Lite.
- Failure/empty behavior: Missing relative assets show broken images/video; bad release links send users to wrong downloads.
- Files likely involved in changes: `docs/index.html`, `docs/styles.css`, `docs/i18n.js`, `docs/support/index.html`, `docs/privacy/index.html`, `docs/assets/`, `docs/CNAME`.

### WZRD.VID Lite Import, Render, and Download

- Entry point: `docs/lite/index.html`, Add Media, Add Audio, drag/drop, MAKE CLIP.
- UI/component path: `docs/lite/index.html`, `docs/lite/styles.css`, `docs/lite/app.js`.
- Data/state path: in-memory arrays of local File objects/object URLs, generated timeline segments, optional random clip assembly state, ANSI intervals, Canvas state, page-local default-on Include Source Audio state, explicit Add Audio bus state, one reusable AudioContext, MediaRecorder blobs, latest export diagnostics, and the latest rendered Blob for native Apple Lite export handoff. MAKE CLIP snapshots the source-audio checkbox before asynchronous preparation. Reset/Clear Project releases selected media/audio/rendered object URLs and active render/audio connections while keeping equivalent render-option controls, including Include Source Audio, unchanged. UI language preference may be stored in localStorage only.
- Asset/media path: local user files only; browser object URLs; no upload/server path.
- Success behavior: Browser renders a max 15/30/60-second local chaos cut with a 30 fps Fast 480p target or 24 fps Better 720p target, optionally assembling random local sections up to the selected duration by shuffling through loaded media before reuse, applies Lite motion/texture effects (live Lite-style tunnel zoom, punch/wobble, tape/RGB treatment, hard ANSI overlays, short ending fade, optional added-audio bump), and exposes a download button. Source OFF/no Add stays silent; source ON/no Add follows the visual video cuts; source OFF/Add preserves the captureStream-first/Web Audio fallback; source ON/Add mixes decoded Add Audio with timeline source nodes. Audio-enabled output has one Web Audio/MediaRecorder track. HEIC/HEIF import logs browser decode timing when decode succeeds.
- Failure/empty behavior: Browser API incompatibility or unsupported file types should log/fail in the Lite UI without network fallback. If source Web Audio is unavailable, Lite states that source audio was omitted while preserving any valid Add Audio path. HEIC/HEIF files may be selectable but still fail decode if the browser cannot decode them. Do not add persistent browser media caches without updating privacy/storage docs.
- Files likely involved in changes: `docs/lite/app.js`, `docs/lite/index.html`, `docs/lite/styles.css`, `docs/i18n.js`, `docs/lite/README.md`.

### WZRD.VID Lite Apple Wrapper Groundwork

- Entry point: `apple-lite/WZRDVIDLite.xcodeproj` iOS app target using SwiftUI sources under `apple-lite/WZRDVIDLite/App/`.
- UI/component path: `ContentView.swift` embeds `LiteWebView.swift`, which loads bundled local Lite web files into `WKWebView`.
- Data/state path: same Lite browser runtime model: local file picker/object URLs/Canvas/Web Audio/MediaRecorder, plus local UI language preference from the existing Lite JavaScript.
- Asset/media path: `apple-lite/scripts/prepare_lite_web_bundle.py` copies `docs/lite/`, `docs/i18n.js`, and referenced `docs/assets/{branding,logo,ui}/` into ignored `apple-lite/WZRDVIDLite/Resources/LiteWeb/`.
- Success behavior: The native shell loads bundled Lite files locally and cancels non-local navigation. Source and Add Audio are fully mixed in the bundled browser runtime before rendered Lite blobs reach Swift. The downstream `WKScriptMessageHandler` writes the browser output to a temporary local file, validates its tracks, and saves it directly to Photos with add-only permission. Debug simulator builds run all four audio modes, normal/random segment mapping, repeated render/reset cleanup, Fast/Better and 15/30 control paths, native validation, and exported-file PCM/FFT checks through `apple-lite/scripts/run_simulator_smoke.py`.
- Failure/empty behavior: Missing generated `LiteWeb/` shows a native-shell HTML error. Real-device testing found WKWebView blob downloads opened the clip for playback and the generic share-sheet Save Video path failed to add the output to Photos, so export now uses direct native Photos save. The native Blob handoff must slice Data URLs at `;base64,` because MP4 codec strings can contain commas. iOS WKWebView lacks `HTMLAudioElement.captureStream()`, so source/mixed modes use Web Audio; the Swift bridge must not recreate the source timeline or become a native mixer. Final physical-device source-audio monitoring and saved-Photos playback need a hand retest.
- Files likely involved in changes: `apple-lite/WZRDVIDLite.xcodeproj`, `apple-lite/README.md`, `apple-lite/WZRDVIDLite/App/*.swift`, `apple-lite/WZRDVIDLite/App/Info.plist`, `apple-lite/scripts/prepare_lite_web_bundle.py`, `apple-lite/scripts/run_simulator_smoke.py`, `docs/lite/*`.

### GitHub Pages Deployment

- Entry point: push to `main` with GitHub Pages configured to deploy `/docs`.
- UI/component path: GitHub Pages, `docs/CNAME` for `wzrdvid.com`.
- Data/state path: static files in `docs/`.
- Asset/media path: committed `docs/assets/` files and linked external GitHub URLs.
- Success behavior: `https://wzrdgang.github.io/wzrdVID/` and `https://wzrdvid.com` serve the landing page; `/lite/` serves Lite.
- Failure/empty behavior: Wrong Pages folder/domain/CNAME/pathing can break the site; no local `.github` workflow exists in the current checkout.
- Files likely involved in changes: `docs/index.html`, `docs/styles.css`, `docs/CNAME`, `docs/lite/*`, `docs/assets/*`.

## 3. Build/Deploy Flow

- Desktop source install: create a Python virtualenv, install `requirements.txt`, install ffmpeg/ffprobe separately.
- Desktop source run: `python run.py`; macOS/Linux convenience script: `./run.sh`; Windows helper: `run_windows.bat`.
- Desktop macOS app build: `./build_app.sh` creates `dist/WZRD.VID.app`, using `VERSION`, PyInstaller, and generated branding/icon/UI assets; after explicit Qt pruning it removes the matching PyInstaller companion links, rejects any dangling symlink, re-signs ad hoc, and requires strict codesign verification.
- Desktop drag-install DMG: `scripts/package_dmg.sh` consumes the existing built app, validates it, stages it with `ditto`, adds `Applications -> /Applications`, creates and verifies a compressed read-only image, mounts it at a unique temporary path, validates its exact top-level contents and strict app identity/signature, then emits ignored `WZRD.VID-macOS.dmg`. Replacement means Finder replaces only `/Applications/WZRD.VID.app`; macOS `settings.json`, `ImportedMedia`, `StillCache`, `Previews`, and user-selected recipes remain outside that bundle. The DMG is ad-hoc/unnotarized release preparation, not an automatic updater.
- Desktop release zip: `scripts/package_release.sh` creates `WZRD.VID-macOS.zip` with `ditto`.
- GitHub Pages local preview: serve `docs/` with a simple static server such as `python3 -m http.server` from the `docs` directory.
- GitHub Pages deployment: GitHub repo settings should deploy branch `main`, folder `/docs`, custom domain `wzrdvid.com` via `docs/CNAME`.
- Apple Lite local bundle prep: `python3 apple-lite/scripts/prepare_lite_web_bundle.py` generates ignored `apple-lite/WZRDVIDLite/Resources/LiteWeb/` for Xcode folder-reference inclusion.
- Apple Lite simulator smoke: `python3 apple-lite/scripts/run_simulator_smoke.py` builds `apple-lite/WZRDVIDLite.xcodeproj`, installs the app on an available iPhone simulator, and runs the debug-only WKWebView smoke harness, including native export bridge surface checks.
- GitHub Actions workflow: Not present in repo.
- Output directories: `dist/`, `build/`, `.pyinstaller-cache/`, `.venv/`, caches, temp folders, and release zip are generated/local outputs unless explicitly being packaged outside source control.
- Files that can break deployment: `docs/CNAME`, relative paths in `docs/index.html`, `docs/lite/*`, `docs/support/index.html`, `docs/privacy/index.html`, `docs/assets/*`, GitHub Release URLs/copy, `VERSION`, `build_app.sh`, `requirements.txt`, icon/asset generation scripts.

## 4. High-Risk Files

| File/path | Why high-risk | What depends on it | Safe edit guidance | Required checks after editing |
| --- | --- | --- | --- | --- |
| `app.py` | Central desktop UI, settings, six-row Zone assignment/codec Layer persistence, threading, timeline/audio bindings | Desktop app workflows, save/load/migration/reset, preview, render/batch | Keep edits scoped; keep activation checkboxes separate from Zone assignment and Layer position; allowlist only the five frame effects plus SKRRT; verify Zone identity/geometry/assignments, keyboard/drag editing, codec reorder, and project JSON | `python3 -m py_compile app.py ...`; targeted GUI save/reload/reset/malformed-state and source render smoke if behavior changed |
| `state_contract.py` | Canonical schema/migration/default/Reset/serialization and persisted Zone/Layer/Style/effect rules | Desktop settings, recipes, MainWindow state, renderer Zone/Layer identifiers | Keep stdlib-only; preserve schema 6 and current malformed/unknown policy; never add probing, paths, widgets, runtime planning, or codec execution | `py_compile`; direct pure schema-3/4/5/6, malformed/default/Reset/idempotence tests; isolated offscreen MainWindow settings/recipe integration; full tracked suite twice plus reverse order when tests/contracts change |
| `app_i18n.py` | Desktop UI localization resources and fallback helpers | Visible desktop labels, language selector, local settings preference | Keep stable keys and English fallback; mark draft translations | `py_compile`; source GUI smoke if practical |
| `renderer.py` | Core media timeline/render/effect engine, Zone-local frame effects, SKRRT Zone dispatch, and codec Layer dispatch | Preview/full render/batch outputs, spatial containment, and exact enabled operation chronology | Preserve literal Full Frame frame-effect/SKRRT paths; normalize Zones once; keep frame-effect Zone history bounded and ROI replacement half-open; pass only SKRRT's resolved box into codec operations; normalize one codec order and keep salts/parameters mode-owned | `py_compile`; Full Frame oracles; six-row allowlist; frame-effect containment/isolation/overlap/failure; SKRRT prepared/decoded Zone matrices; codec order permutations; tiny preview/full render; affected media tests |
| `datamosh.py` | Planned and saved-order MPEG-4 Part 2 DATAMOSHING/Overflow/SKRRT/Scatter/Bleed composition, bounded Full Frame/Zone reverse preparation, exact frame-clocked fragment preparation, strict shared auxiliary structure validation, and safe pre-audio transcode | Codec-mode preview/full/batch outputs, target/writer semantics, spatial provenance/leakage, timing, temp cleanup, final codec validity | Keep per-mode planning order-independent, whole-VOP last-writer execution explicit, temporal windows/provenance/recovery anchors bounded, and auxiliaries controlled-stream-based; Zone SKRRT must start from exact current full frames and replace only the rasterized box with exact reverse source; preserve one main controlled encode/safe transcode; never mutate sources or silently drop/retarget events | `py_compile`; migration/duplicate rejection; Full Frame byte oracle; VOP/authenticity/order/attribution/provenance/determinism/failure, Zone geometry/leakage/recovery, fragment-construction, and auxiliary stress tests; ffprobe frame/duration/H.264/AAC checks; frozen historical/reverse/Zone package renders |
| `still_cache.py` | Still-image loading, HEIC/HEIF proxy caching, and managed still-cache cleanup targets | Photo preview/import, desktop render still frames, preview/cache cleanup | Preserve cache-key inputs and managed-directory boundaries; do not broaden cleanup outside app-owned `StillCache` | `python3 -m py_compile still_cache.py`; focused HEIC/still import/render/cache cleanup smoke |
| `ffmpeg_utils.py` | ffmpeg discovery, probing, audio mix/mux, optimization | Audio output, final MP4 compatibility, file-size targets | Preserve subprocess list args and path safety | `py_compile`; ffprobe/ffmpeg smoke; AAC/H.264 verification if output changed |
| `presets.py` | Style preset definitions consumed by UI/renderer | Preset dropdown and visual output | Additive changes are safer than renames/removals | `py_compile`; preview/tiny render with changed preset |
| `theme.py` | Desktop visual identity and asset paths | Entire PySide6 UI styling | Keep controls readable; do not scatter one-off styles | `py_compile`; GUI screenshot/launch check for styling edits |
| `build_app.sh` | macOS packaging, PyInstaller excludes, pruning/link integrity, signing | Release app bundle | Do not edit casually; preserve app name/icon/bundle path and explicit pruning allowlist | `bash -n build_app.sh`; `./build_app.sh`; zero-output dangling-link scan; strict codesign verification; normal app launch |
| `scripts/package_dmg.sh` | DMG staging, mount cleanup, app/link/signature validation, and generated artifact replacement | Primary future macOS drag-install artifact | Keep staging under its validated temporary root; preserve strict source/staged/mounted checks and never install, strip quarantine, sign for production, notarize, or publish | `bash -n`; fresh app build; two package passes; failure cleanup; mounted content/link/codesign/identity checks; isolated replacement, launch, user-data hash, and frozen render smoke |
| `scripts/package_release.sh` | Release zip creation | GitHub Release fallback asset | Preserve `ditto` app bundle packaging | `bash -n`; run script after app build if changed |
| `requirements.txt` | Runtime/build dependency set | Source runs and PyInstaller app size/reliability | Add dependencies only with clear need | install/build checks; app smoke |
| `VERSION` | Single app/release version source | Desktop app visible version and `build_app.sh` Info.plist metadata | Keep in sync with changelog/release tag | `py_compile`; `./build_app.sh`; Info.plist version check |
| `docs/CNAME` | Custom domain binding | `wzrdvid.com` GitHub Pages | Do not change outside domain task | Pages preview/live check after push |
| `docs/index.html` | Public landing/download page | Website, download guidance, Lite link | Preserve relative paths and brand/license copy | local static preview; link/path checks |
| `docs/i18n.js` | Static landing/Lite localization resources | Public site and Lite visible copy, language preference, RTL document direction | Keep static/no-network behavior; use stable keys and English fallback | `node --check docs/i18n.js`; local static preview; grep Lite network APIs |
| `docs/lite/app.js` | Browser-only Lite logic/privacy/timing | Lite render/download behavior | Keep no-upload rule; avoid network APIs | `node --check`; local browser smoke; grep network APIs |
| `apple-lite/` | Future WZRD.VID Lite Apple wrapper | iOS/iPadOS local bundled Lite shell | Keep desktop renderer/ffmpeg/backend out; use bundled local assets; block remote navigation; keep export bridge limited to local rendered blobs and direct Photos save/share needs | bundle prep script; plist lint; Swift parse/build with iPhone Simulator SDK if available; simulator smoke |
| `assets/` and `docs/assets/` | Branding/demo/UI assets | Desktop app, README, Pages | Avoid deleting intentional assets; check file size/licensing | `git status`; asset path checks; preview/readme/site checks |
| `LICENSE`, `NOTICE.md`, `README.md` | Public rights, brand, and user instructions | GitHub readers, release users, contributors | Keep source-available wording consistent | targeted `rg` for stale license/branding terms |

## 5. Data and Assets Map

- Desktop persistent settings: platform user config/application-support directory from `app.py` `_user_data_dir()`; includes `settings.json`.
- Desktop previews: preview outputs are placed under a `Previews` folder next to the user-data/settings area.
- Desktop still cache: HEIC/HEIF proxies are stored under a `StillCache` folder in the same WZRD.VID app-support/config area, keyed by source path, size, mtime, and proxy size. Manual Clear Preview Cache removes them; automatic cleanup removes old app-managed still cache files by age.
- Desktop imported media cache: protected HEIC/HEIF imports that WZRD.VID can read are copied under `ImportedMedia` in the same app-support/config area using original stem plus a short source identity hash. Recipes may reference these cached paths. Current preview/cache cleanup does not delete `ImportedMedia`; do not add deletion without a separate safety design.
- User recipes/project presets: user-selected JSON files; media paths are referenced, not embedded.
- Desktop render temp files: `tempfile.TemporaryDirectory(prefix="wzrd_vid_render_")` and ffmpeg temp directories for optimization/audio work. The default renderer uses the frame-pipe transport and does not create a `frames/` PNG sequence. Legacy PNG staging can be forced with the local desktop developer setting or `WZRDVID_FORCE_PNG_STAGING=1`, and the renderer creates `frames/` if the default pipe path falls back before audio muxing. Any enabled datamosh codec mode adds only nested app-owned `datamosh/controlled_prediction.m4v`, `datamosh/manipulated_prediction.m4v`, and `datamoshed_silent.mp4` artifacts inside that same auto-cleaned render root.
- Browser Lite data: local browser File objects, object URLs, Canvas, Web Audio, MediaRecorder blobs; no server storage and no upload path.
- Apple Lite generated web bundle: ignored `apple-lite/WZRDVIDLite/Resources/LiteWeb/`, regenerated from `docs/lite/` and selected `docs/assets/` by `apple-lite/scripts/prepare_lite_web_bundle.py` or the Xcode build phase.
- Static assets safe to edit with care: `assets/branding/`, `assets/logo/`, `assets/ui/`, `assets/demos/`, `assets/screenshots/`, `docs/assets/`.
- Generated/build outputs: `dist/`, `build/`, `.venv/`, `.pip-cache/`, `.pyinstaller-cache/`, `__pycache__/`, `WZRD.VID.spec`, `tmp/`, `temp/`, local release DMGs and zips.
- Media handling rules: Do not commit random copyrighted media or large local renders. Release-safe demo/screenshot assets under `assets/` and `docs/assets/` are intentionally allowed by `.gitignore` negation rules.
- Performance/release planning notes: `docs/PERFORMANCE_NOTES.md` records long-media audit/stress findings; `docs/APPLE_LITE_APP_RESEARCH.md` records Apple Lite app groundwork research only.

## 6. Dependency Map

| Dependency/tool | Used for | Primary files | Risk notes |
| --- | --- | --- | --- |
| PySide6 / Qt | Desktop GUI widgets/styles/threading | `app.py`, `theme.py`, `build_app.sh` | PyInstaller bundle size and Qt plugin pruning are sensitive |
| OpenCV (`opencv-python-headless`) | Video frame reads/resizing | `renderer.py` | Codec/platform support can vary by OS/source file |
| Pillow | Text/art rendering, images, EXIF handling, asset generation | `renderer.py`, generator scripts | Font and image-format availability can vary |
| numpy | Frame/image array processing | `renderer.py`, texture generation | Keep array operations memory-aware |
| ffmpeg / ffprobe | Media probing, encode/mux/mix/optimize and controlled MPEG-4 Part 2 datamosh-modes round trip | `ffmpeg_utils.py`, `datamosh.py`, README/docs | External install required; native `mpeg4`, `libx264`, I/P/VOP structure, frame count, and path detection must be validated |
| PyInstaller | macOS app bundle | `build_app.sh`, generated spec | Excludes/pruning can break Finder app launch |
| Browser Canvas/Web Audio/MediaRecorder | WZRD.VID Lite local render | `docs/lite/app.js` | Browser codec support varies; must remain no-upload |
| SwiftUI / WKWebView | WZRD.VID Lite Apple wrapper shell | `apple-lite/WZRDVIDLite/App/*.swift` | Keep bundled/local-only; test file input and blob export on real devices |
| GitHub Pages | Static site hosting | `docs/`, `docs/CNAME` | Relative paths/custom domain settings can break public site |

## 7. Agent-Safe Edit Protocol

### UI/content changes

- Inspect: `README.md`, affected `docs/*.html`, `docs/*.css`, `app.py`, `theme.py`.
- Preserve public brand terms, source-available license language, and current layout unless explicitly changing them.
- Run `git diff --check` and local/static preview or GUI screenshot when visible UI changed.

### Component logic changes

- Inspect `state_contract.py`, affected UI wiring, and downstream render/settings consumers.
- Keep changes narrow; update save/load project JSON only when necessary and backward-compatible.
- Run `py_compile` and targeted workflow smoke tests. Run the tracked desktop regression suite when Material effects, Zones, schema/project state, Preview/playback/transition/tail planning, codec execution/Layer persistence, render transport/failure classification, or final audio/media handling are affected.

### Routing/navigation changes

- For Pages/Lite, inspect `docs/index.html`, `docs/lite/index.html`, relative links, and `docs/CNAME`.
- Preserve GitHub Pages compatibility; avoid root-only paths unless verified.
- Run local static preview and link/path checks.

### Asset/media changes

- Inspect `assets/README.md`, `.gitignore`, `docs/assets/`, and asset consumers.
- Keep assets lightweight and rights-safe; do not delete official branding assets.
- Verify referenced paths and file sizes before committing.

### Dependency changes

- Inspect `requirements.txt`, import usage, `build_app.sh`, README install docs, and cross-platform docs.
- Add dependencies only when existing code cannot reasonably do the job.
- Run install/build checks appropriate to the dependency impact.

### GitHub Pages/deployment changes

- Inspect `docs/CNAME`, `docs/index.html`, `docs/styles.css`, `docs/lite/*`, release links, and Pages docs.
- Do not alter domain/Pages source casually.
- Preview locally and check live URLs after push if deployment was intended.

### Broad refactors

- Require explicit user permission.
- Read `docs/agent-change-playbook.md`, this map, and latest log entries first.
- Stage incrementally and expand verification to include app, Lite, packaging, and docs as applicable.

## 8. Verification Matrix

| Change type | Minimum checks |
| --- | --- |
| Docs-only | `git status --short --branch`; `git diff --check`; targeted `rg` for required section names/stale terms |
| Copy/style-only desktop | Docs-only checks; `python3 -m py_compile app.py app_i18n.py renderer.py datamosh.py ffmpeg_utils.py still_cache.py presets.py theme.py run.py`; GUI launch/screenshot if practical |
| Copy/style-only Pages/Lite | Docs-only checks; local static preview; `node --check docs/i18n.js`; `node --check docs/lite/app.js` if Lite JS touched |
| Component UI | `py_compile`; targeted GUI smoke; save/load smoke if settings/project controls touched |
| App logic/state | `python3 -m py_compile app.py state_contract.py app_i18n.py renderer.py datamosh.py ffmpeg_utils.py still_cache.py presets.py theme.py run.py`; direct pure state-module tests plus isolated MainWindow integration; tracked desktop regression suite when schema, Zones, Material state, Preview/playback/transition/tail planning, codec execution/Layer persistence, render transport/failure classification, or final audio/media handling are affected; focused render/preview/project smoke; check settings backward compatibility |
| Video/media handling | `python3 -m py_compile app.py state_contract.py app_i18n.py renderer.py datamosh.py ffmpeg_utils.py still_cache.py presets.py theme.py run.py`; tracked desktop regression suite for affected Preview/playback/transition/tail, frame, Zone, codec, Layer, transport/failure, or final-media contracts; tiny render or still/HEIC cache smoke with relevant media; `node --check docs/i18n.js docs/lite/app.js` if Lite/media UI changed; ffprobe final codec/audio where output changed |
| Tracked desktop regression tests | Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_*.py'`; require exact Material oracle and canonical spILL! contracts, labeled CURRENT-versus-ACCEPTED Preview planning characterization, rights-safe deterministic generated fixtures/media, isolated settings/temp cleanup, source immutability, no repository artifacts, repeat execution, and reverse-module-order execution when the suite or its fixtures/oracles change |
| Routing/navigation | local static preview from `docs/`; check relative links and `docs/CNAME` only if domain-related |
| Asset/media | file-size check; path/reference check; README/site/app preview if asset is visible |
| Dependency/package | install check in venv; `py_compile`; build/source-run smoke; packaging smoke if PyInstaller impact |
| Build/deploy config | syntax check scripts; `./build_app.sh` or relevant package script; `find -L dist/WZRD.VID.app -type l -print` must be empty; `codesign --verify --deep --strict --verbose=4 dist/WZRD.VID.app` must pass; normal app launch if macOS bundle changed. For DMGs, additionally validate image checksum, allowlisted root contents, `/Applications` symlink, mounted and replacement-installed app integrity/identity, cleanup on failure, structural repeatability, isolated user-data hashes, and a frozen packaged render. |
| GitHub Pages/deployment | local static preview; after push, verify GitHub Pages/custom domain as task requires |
| Broad refactor | Full relevant matrix: desktop source run, render smoke, Lite smoke, docs checks, build/release checks as applicable |

## 9. Known unknowns

No unresolved evidence gaps remain from the current static repo inspection.

Explicitly not present in the current checkout:

- `.github` GitHub Actions workflows.
- Tracked frozen-package/DMG/real-media regression coverage beyond the current source/integration `unittest` foundation.
- A configured markdown lint tool.
- Backend/server runtime for the Pages site or Lite app.
- Official packaged Windows/Linux builds.

Items that cannot be proven from the repo alone:

- Current GitHub Pages dashboard settings and HTTPS enforcement. Verify in GitHub Settings -> Pages or with live HTTP checks.
- Current GitHub Release assets. Verify with `gh release view` or the GitHub Releases UI.
- Cross-platform runtime behavior on Windows/Linux. Verify on those operating systems with the documented source-run commands.
