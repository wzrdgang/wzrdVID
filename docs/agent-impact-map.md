# wzrdVID Agent Impact Map

This map describes the current repository so future agents can edit with context. It is descriptive, not aspirational. It does not change app behavior.

## 1. Major Modules

### Desktop GUI Shell

- Owning files/directories: `app.py`, `app_i18n.py`, `theme.py`, `assets/ui/`, `assets/branding/`, `assets/logo/`.
- Purpose: PySide6 desktop interface for timeline sources, audio controls, style/effects settings, output controls, preview rendering, recipe import/export, batch render, and logs.
- Inbound dependencies: `run.py`, `run.sh`, `run_windows.bat`, user file selections, drag/drop events, saved settings JSON, recipe/project preset JSON.
- Outbound dependencies: `renderer.py`, `ffmpeg_utils.py`, `presets.py`, Qt widgets/styles/assets, local filesystem, temp preview/output folders.
- High-risk notes: UI controls feed render settings and audio behavior. Small copy/style changes are usually safe; widget wiring, settings keys, thread behavior, table columns, and localization keys can break render, save/load, or audio mix flows.

### Render Engine

- Owning files/directories: `renderer.py`, `presets.py`.
- Purpose: Builds a virtual media timeline from videos/photos, samples frames, applies framing/effects/bypass/ANSI/chunky rendering, writes frames, and coordinates final video output.
- Inbound dependencies: `app.py` render settings, timeline items, user selected output path, source media files.
- Outbound dependencies: OpenCV, Pillow, numpy, ffmpeg helpers, temporary frame directories, output MP4 files.
- High-risk notes: Rendering touches timing, frame counts, max-length caps, random clip segment planning, temp cleanup, EXIF photo orientation, bypass intervals, transitions/endings, optimization, and audio duration expectations. Run focused smoke tests after edits.

### ffmpeg and Media Utilities

- Owning files/directories: `ffmpeg_utils.py`.
- Purpose: ffmpeg/ffprobe discovery, duration/stream probing, timecode parsing, video encoding, audio trim/mux/mix, source timeline audio construction, H.264/AAC optimization, and file-size targeting.
- Inbound dependencies: `app.py`, `renderer.py`, user-selected video/audio files, render duration and output-size settings.
- Outbound dependencies: system `ffmpeg`/`ffprobe`, subprocess calls, temp files, MP4/AAC outputs.
- High-risk notes: Path quoting, spaces, video-container audio, audio offsets, source audio mixing, and two-pass optimization depend on this file. Avoid `shell=True` unless absolutely necessary.

### Launchers and Source-Run Support

- Owning files/directories: `run.py`, `run.sh`, `run_windows.bat`, `requirements.txt`, `docs/CROSS_PLATFORM.md`.
- Purpose: Launch from source on macOS/Linux/Windows and document best-effort cross-platform behavior.
- Inbound dependencies: user shell/Python environment.
- Outbound dependencies: project virtualenv, Python executable, Python dependencies, ffmpeg installed on PATH or common macOS Homebrew paths.
- High-risk notes: Keep shell assumptions isolated to platform-specific helper scripts. `run.py` should stay shell-neutral.

### macOS Build and Release Packaging

- Owning files/directories: `build_app.sh`, `scripts/package_release.sh`, `scripts/generate_icon.py`, `scripts/generate_logo.py`, `scripts/generate_branding.py`, `scripts/generate_ui_textures.py`, `assets/wzrd_vid.*`, `VERSION`, `WZRD.VID.spec` when generated locally.
- Purpose: Build `dist/WZRD.VID.app`, prune PyInstaller/Qt payload, generate icons/branding/textures, ad-hoc sign the macOS app, and create `WZRD.VID-macOS.zip` for GitHub Releases.
- Inbound dependencies: local macOS shell, Python virtualenv, requirements, `VERSION`, source assets.
- Outbound dependencies: `build/`, `dist/`, `.venv/`, `.pyinstaller-cache/`, generated icon/texture/branding files, release zip.
- High-risk notes: macOS packaging is primary distribution. Do not change app name, icon paths, PyInstaller excludes, pruning rules, or bundle metadata casually.

### GitHub Pages Landing Site

- Owning files/directories: `docs/index.html`, `docs/styles.css`, `docs/i18n.js`, `docs/CNAME`, `docs/assets/`, `docs/RELEASE_DOWNLOAD_HELP.md`, `docs/RELEASE_CHECKLIST.md`.
- Purpose: Static landing/download page for `wzrdvid.com` and GitHub Pages, with release links, demo media, screenshots, Lite link, and source/download guidance.
- Inbound dependencies: GitHub Pages configured to deploy branch `main` folder `/docs`, custom domain DNS, static assets copied under `docs/assets/` or referenced from repository paths that resolve on Pages.
- Outbound dependencies: browser rendering, GitHub Releases latest URL, GitHub repo URL, `docs/CNAME` custom domain.
- High-risk notes: `docs/CNAME`, root-relative paths, and release links can break the public site. Do not change Pages config or domain copy without deployment-related intent.

### WZRD.VID Lite Browser App

- Owning files/directories: `docs/lite/index.html`, `docs/lite/styles.css`, `docs/lite/app.js`, `docs/i18n.js`, `docs/lite/README.md`.
- Purpose: Browser-only, static WZRD.VID Lite prototype for local 15/30/60-second chaos cuts using drag/drop, Canvas, Web Audio, and MediaRecorder. It does not upload user files.
- Inbound dependencies: browser file inputs/drop events, local media selected by user.
- Outbound dependencies: object URLs, Canvas, Web Audio, MediaRecorder, downloaded blob output.
- High-risk notes: Privacy copy and no-upload behavior are product boundaries. Grep for network APIs after edits: `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`.

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
- Data/state path: `app.py` loads settings from `_user_data_dir()` (`WZRD.VID/settings.json` under the platform user config/application-support location).
- Localization path: `app_i18n.py` resolves the UI language and falls back to English for missing keys; selected `ui_language` persists in local settings.
- Asset/media path: app icon and UI/branding assets under `assets/` when running from source or bundled by PyInstaller.
- Success behavior: Main window opens with Source, Style, and Output tabs.
- Failure/empty behavior: Missing ffmpeg/ffprobe is surfaced in the GUI/log with platform-specific install guidance.
- Files likely involved in changes: `app.py`, `theme.py`, launchers, `ffmpeg_utils.py`, `build_app.sh`.

### Desktop Source Import and Timeline

- Entry point: Add Video(s), Add Photo(s), drag/drop onto timeline, recipe import or legacy project preset load.
- UI/component path: `app.py` timeline widgets, `MediaDropTableWidget`, timeline item table columns, preview controls.
- Data/state path: `TimelineItem` records path, kind, duration, trim, photo hold, `has_audio`, and `include_audio`; project JSON preserves timeline order and item settings.
- Asset/media path: user selected videos/photos; photos are corrected for EXIF orientation through Pillow handling in the render/preview path.
- Success behavior: Items append to timeline, durations are shown, video audio is detected, Include Audio defaults appropriately, preview updates.
- Failure/empty behavior: Unsupported media or probe/load failures are logged and shown as clear GUI errors.
- Files likely involved in changes: `app.py`, `renderer.py`, `ffmpeg_utils.py`.

### Desktop Audio Import, Source Audio, and Mixing

- Entry point: Select Music/Audio, drag/drop audio/video-with-audio, Audio Mix mode, Include Audio checkboxes.
- UI/component path: `app.py` audio controls, timeline Include Audio column, volume sliders, music trim/offset fields.
- Data/state path: settings/project JSON preserve external audio path, trims, offset fields, audio mix mode, volumes, and per-item include-audio flags.
- Asset/media path: external audio files or video containers with audio tracks; source timeline video audio; silence for photos or disabled/no-audio video rows.
- Success behavior: Final MP4 can be silent, external-only, source-only, or external plus selected source audio, encoded as AAC when audio exists.
- Failure/empty behavior: Selecting a file with no audio stream reports `Selected music file has no audio track.`; match-to-music disables unsafe source-audio mixing according to current app behavior.
- Files likely involved in changes: `app.py`, `ffmpeg_utils.py`, `renderer.py`, README/docs.

### Desktop Render, Preview, Batch, and Export

- Entry point: Preview 5 Seconds, MAKE VIDEO, MAKE BATCH.
- UI/component path: `app.py` collects render settings and starts `RenderThread` or `BatchRenderThread`; progress/log signals update GUI.
- Data/state path: `RenderSettings`, `PlaybackPlan`, optional `max_video_length`, optional `random_clip_assembly`, bypass intervals, random seeds, style/output/optimization/framing/effect settings.
- Asset/media path: source media, temp frame directories, preview folder under app settings parent, user-selected output path, optional optimized output path.
- Success behavior: Normal MP4 visually renders ANSI/text-art/glitch output, optional max-length caps output duration, optional random clip assembly builds deterministic seeded source segments before rendering, optional audio is muxed/mixed, optional optimization targets max MB, output/open-folder controls become available.
- Failure/empty behavior: Random clip assembly without max length or with match-to-music should reject before render; exceptions are logged and surfaced without freezing the GUI; temp directories should clean themselves up.
- Files likely involved in changes: `app.py`, `renderer.py`, `ffmpeg_utils.py`, `presets.py`, `theme.py`.

### Export/Import Recipes

- Entry point: Export Recipe, Import Recipe.
- UI/component path: `app.py` project controls.
- Data/state path: user-selected recipe JSON files; app settings store recent/default values. Schema version 4 adds `max_video_length` as entered text and `random_clip_assembly` as a boolean; missing fields must load as blank/false.
- Asset/media path: recipe JSON references user media paths but does not copy media.
- Success behavior: Timeline, audio, max-length/random assembly controls, style/effects, framing, bypass, output, batch, seeds, and optimization controls restore.
- Failure/empty behavior: Missing referenced media, invalid recipe JSON, or older project preset JSON should be reported through GUI/log.
- Files likely involved in changes: `app.py`, docs.

### GitHub Pages Landing/Homepage

- Entry point: `docs/index.html` at GitHub Pages root or `wzrdvid.com`.
- UI/component path: static HTML/CSS in `docs/index.html` and `docs/styles.css`.
- Data/state path: none; all static.
- Localization path: `docs/i18n.js` applies `data-i18n` text and stores only the UI language preference in localStorage.
- Asset/media path: `docs/assets/` and release/repo links.
- Success behavior: Users see hero, demo, screenshots, download links, Lite link, rights/source notes, and footer.
- Failure/empty behavior: Missing relative assets show broken images/video; bad release links send users to wrong downloads.
- Files likely involved in changes: `docs/index.html`, `docs/styles.css`, `docs/i18n.js`, `docs/assets/`, `docs/CNAME`.

### WZRD.VID Lite Import, Render, and Download

- Entry point: `docs/lite/index.html`, Add Media, Add Audio, drag/drop, MAKE CLIP.
- UI/component path: `docs/lite/index.html`, `docs/lite/styles.css`, `docs/lite/app.js`.
- Data/state path: in-memory arrays of local File objects/object URLs, generated timeline segments, optional random clip assembly state, ANSI intervals, Canvas state, MediaRecorder blobs. UI language preference may be stored in localStorage only.
- Asset/media path: local user files only; browser object URLs; no upload/server path.
- Success behavior: Browser renders a max 15/30/60-second local chaos cut, optionally assembling random local sections up to the selected duration, and exposes a download button.
- Failure/empty behavior: Browser API incompatibility or unsupported file types should log/fail in the Lite UI without network fallback.
- Files likely involved in changes: `docs/lite/app.js`, `docs/lite/index.html`, `docs/lite/styles.css`, `docs/i18n.js`, `docs/lite/README.md`.

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
- Desktop macOS app build: `./build_app.sh` creates `dist/WZRD.VID.app`, using `VERSION`, PyInstaller, and generated branding/icon/UI assets.
- Desktop release zip: `scripts/package_release.sh` creates `WZRD.VID-macOS.zip` with `ditto`.
- GitHub Pages local preview: serve `docs/` with a simple static server such as `python3 -m http.server` from the `docs` directory.
- GitHub Pages deployment: GitHub repo settings should deploy branch `main`, folder `/docs`, custom domain `wzrdvid.com` via `docs/CNAME`.
- GitHub Actions workflow: Not present in repo.
- Output directories: `dist/`, `build/`, `.pyinstaller-cache/`, `.venv/`, caches, temp folders, and release zip are generated/local outputs unless explicitly being packaged outside source control.
- Files that can break deployment: `docs/CNAME`, relative paths in `docs/index.html` and `docs/lite/*`, `docs/assets/*`, GitHub Release URLs/copy, `VERSION`, `build_app.sh`, `requirements.txt`, icon/asset generation scripts.

## 4. High-Risk Files

| File/path | Why high-risk | What depends on it | Safe edit guidance | Required checks after editing |
| --- | --- | --- | --- | --- |
| `app.py` | Central desktop UI, settings, threading, timeline/audio bindings | Desktop app workflows, save/load, preview, render/batch | Keep edits scoped; verify affected controls and project JSON | `python3 -m py_compile app.py ...`; targeted GUI/source render smoke if behavior changed |
| `app_i18n.py` | Desktop UI localization resources and fallback helpers | Visible desktop labels, language selector, local settings preference | Keep stable keys and English fallback; mark draft translations | `py_compile`; source GUI smoke if practical |
| `renderer.py` | Core media timeline/render/effect engine | Preview/full render/batch outputs | Avoid broad timing/render rewrites; test representative media | `py_compile`; tiny render smoke; affected media tests |
| `ffmpeg_utils.py` | ffmpeg discovery, probing, audio mix/mux, optimization | Audio output, final MP4 compatibility, file-size targets | Preserve subprocess list args and path safety | `py_compile`; ffprobe/ffmpeg smoke; AAC/H.264 verification if output changed |
| `presets.py` | Style preset definitions consumed by UI/renderer | Preset dropdown and visual output | Additive changes are safer than renames/removals | `py_compile`; preview/tiny render with changed preset |
| `theme.py` | Desktop visual identity and asset paths | Entire PySide6 UI styling | Keep controls readable; do not scatter one-off styles | `py_compile`; GUI screenshot/launch check for styling edits |
| `build_app.sh` | macOS packaging, PyInstaller excludes, pruning, signing | Release app bundle | Do not edit casually; preserve app name/icon/bundle path | `bash -n build_app.sh`; `./build_app.sh`; Finder launch if packaging changed |
| `scripts/package_release.sh` | Release zip creation | GitHub Release asset | Preserve `ditto` app bundle packaging | `bash -n`; run script after app build if changed |
| `requirements.txt` | Runtime/build dependency set | Source runs and PyInstaller app size/reliability | Add dependencies only with clear need | install/build checks; app smoke |
| `VERSION` | Single app/release version source | Desktop app visible version and `build_app.sh` Info.plist metadata | Keep in sync with changelog/release tag | `py_compile`; `./build_app.sh`; Info.plist version check |
| `docs/CNAME` | Custom domain binding | `wzrdvid.com` GitHub Pages | Do not change outside domain task | Pages preview/live check after push |
| `docs/index.html` | Public landing/download page | Website, download guidance, Lite link | Preserve relative paths and brand/license copy | local static preview; link/path checks |
| `docs/i18n.js` | Static landing/Lite localization resources | Public site and Lite visible copy, language preference, RTL document direction | Keep static/no-network behavior; use stable keys and English fallback | `node --check docs/i18n.js`; local static preview; grep Lite network APIs |
| `docs/lite/app.js` | Browser-only Lite logic/privacy/timing | Lite render/download behavior | Keep no-upload rule; avoid network APIs | `node --check`; local browser smoke; grep network APIs |
| `assets/` and `docs/assets/` | Branding/demo/UI assets | Desktop app, README, Pages | Avoid deleting intentional assets; check file size/licensing | `git status`; asset path checks; preview/readme/site checks |
| `LICENSE`, `NOTICE.md`, `README.md` | Public rights, brand, and user instructions | GitHub readers, release users, contributors | Keep source-available wording consistent | targeted `rg` for stale license/branding terms |

## 5. Data and Assets Map

- Desktop persistent settings: platform user config/application-support directory from `app.py` `_user_data_dir()`; includes `settings.json`.
- Desktop previews: preview outputs are placed under a `Previews` folder next to the user-data/settings area.
- User recipes/project presets: user-selected JSON files; media paths are referenced, not embedded.
- Desktop render temp files: `tempfile.TemporaryDirectory(prefix="wzrd_vid_render_")` and ffmpeg temp directories for optimization/audio work.
- Browser Lite data: local browser File objects, object URLs, Canvas, Web Audio, MediaRecorder blobs; no server storage and no upload path.
- Static assets safe to edit with care: `assets/branding/`, `assets/logo/`, `assets/ui/`, `assets/demos/`, `assets/screenshots/`, `docs/assets/`.
- Generated/build outputs: `dist/`, `build/`, `.venv/`, `.pip-cache/`, `.pyinstaller-cache/`, `__pycache__/`, `WZRD.VID.spec`, `tmp/`, `temp/`, local release zips.
- Media handling rules: Do not commit random copyrighted media or large local renders. Release-safe demo/screenshot assets under `assets/` and `docs/assets/` are intentionally allowed by `.gitignore` negation rules.

## 6. Dependency Map

| Dependency/tool | Used for | Primary files | Risk notes |
| --- | --- | --- | --- |
| PySide6 / Qt | Desktop GUI widgets/styles/threading | `app.py`, `theme.py`, `build_app.sh` | PyInstaller bundle size and Qt plugin pruning are sensitive |
| OpenCV (`opencv-python-headless`) | Video frame reads/resizing | `renderer.py` | Codec/platform support can vary by OS/source file |
| Pillow | Text/art rendering, images, EXIF handling, asset generation | `renderer.py`, generator scripts | Font and image-format availability can vary |
| numpy | Frame/image array processing | `renderer.py`, texture generation | Keep array operations memory-aware |
| ffmpeg / ffprobe | Media probing, encode/mux/mix/optimize | `ffmpeg_utils.py`, README/docs | External install required; path detection must stay cross-platform tolerant |
| PyInstaller | macOS app bundle | `build_app.sh`, generated spec | Excludes/pruning can break Finder app launch |
| Browser Canvas/Web Audio/MediaRecorder | WZRD.VID Lite local render | `docs/lite/app.js` | Browser codec support varies; must remain no-upload |
| GitHub Pages | Static site hosting | `docs/`, `docs/CNAME` | Relative paths/custom domain settings can break public site |

## 7. Agent-Safe Edit Protocol

### UI/content changes

- Inspect: `README.md`, affected `docs/*.html`, `docs/*.css`, `app.py`, `theme.py`.
- Preserve public brand terms, source-available license language, and current layout unless explicitly changing them.
- Run `git diff --check` and local/static preview or GUI screenshot when visible UI changed.

### Component logic changes

- Inspect affected UI wiring and downstream render/settings consumers.
- Keep changes narrow; update save/load project JSON only when necessary and backward-compatible.
- Run `py_compile` and targeted workflow smoke tests.

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
| Copy/style-only desktop | Docs-only checks; `python3 -m py_compile app.py renderer.py ffmpeg_utils.py presets.py theme.py run.py`; GUI launch/screenshot if practical |
| Copy/style-only Pages/Lite | Docs-only checks; local static preview; `node --check docs/lite/app.js` if Lite JS touched |
| Component UI | `py_compile`; targeted GUI smoke; save/load smoke if settings/project controls touched |
| App logic/state | `py_compile`; focused render/preview/project smoke; check settings backward compatibility |
| Video/media handling | `py_compile`; tiny render smoke with relevant media; ffprobe final codec/audio where output changed |
| Routing/navigation | local static preview from `docs/`; check relative links and `docs/CNAME` only if domain-related |
| Asset/media | file-size check; path/reference check; README/site/app preview if asset is visible |
| Dependency/package | install check in venv; `py_compile`; build/source-run smoke; packaging smoke if PyInstaller impact |
| Build/deploy config | syntax check scripts; `./build_app.sh` or relevant package script; Finder/app launch if macOS bundle changed |
| GitHub Pages/deployment | local static preview; after push, verify GitHub Pages/custom domain as task requires |
| Broad refactor | Full relevant matrix: desktop source run, render smoke, Lite smoke, docs checks, build/release checks as applicable |

## 9. Known unknowns

No unresolved evidence gaps remain from the current static repo inspection.

Explicitly not present in the current checkout:

- `.github` GitHub Actions workflows.
- A formal Python test suite or configured test runner.
- A configured markdown lint tool.
- Backend/server runtime for the Pages site or Lite app.
- Official packaged Windows/Linux builds.

Items that cannot be proven from the repo alone:

- Current GitHub Pages dashboard settings and HTTPS enforcement. Verify in GitHub Settings -> Pages or with live HTTP checks.
- Current GitHub Release assets. Verify with `gh release view` or the GitHub Releases UI.
- Cross-platform runtime behavior on Windows/Linux. Verify on those operating systems with the documented source-run commands.
