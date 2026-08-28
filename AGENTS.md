# AGENTS.md

Repo-specific operating guide for coding agents working on //wzrdVID.

## 1. Project Summary

//wzrdVID is a local-first creative video tool. The desktop app turns videos and photos into ANSI/text-art, chunky block, glitch, VHS, and compression-art MP4s with optional audio mixing and size optimization. The public site markets and documents the app, hosts demo assets, and includes WZRD.VID Lite, a static browser-only 15/30/60 second chaos-cut prototype.

Current hosting/deployment model:

- Desktop app: Python/PySide6 source run, plus macOS `.app` built locally with PyInstaller via `./build_app.sh`; `scripts/package_dmg.sh` creates the primary drag-install DMG candidate and `scripts/package_release.sh` retains the ZIP fallback for GitHub Releases.
- Website: static GitHub Pages site from `main` branch, `/docs` folder, custom domain `wzrdvid.com` from `docs/CNAME`.
- GitHub Actions: not present in this checkout.

Product boundaries:

- Desktop app remains the full local renderer and primary macOS packaged app.
- Windows/Linux source runs are best-effort only; packaged Windows/Linux builds are not currently official.
- WZRD.VID Lite is browser-only, local-file/no-upload, and not the full desktop renderer.
- The project is source-available for personal noncommercial use; branding is reserved.

## 2. Tech Stack

- Desktop GUI: Python 3, PySide6 QWidget UI.
- Desktop localization: lightweight dictionary-based UI strings in `app_i18n.py`, with fallback to English.
- Rendering: OpenCV, Pillow, numpy, ffmpeg/ffprobe helpers.
- Packaging: PyInstaller, macOS `.app`, ad-hoc codesign in `build_app.sh`.
- Public site: static HTML/CSS/JS under `docs/`.
- Lite prototype: vanilla browser JavaScript, Canvas, MediaRecorder, object URLs; no backend and no uploads.
- Apple Lite groundwork: SwiftUI/WKWebView shell and Xcode project under `apple-lite/`; bundled web resources are generated locally from `docs/lite/`.
- Package manager: `pip` with `requirements.txt`; shell launchers create/use `.venv`.
- Hosting target: GitHub Pages from `docs/`.
- Test/lint tools: the standard-library `unittest` suite under `tests/` preserves the tracked desktop frame/state, Preview planning, and codec/Layer/transport contracts; no formatter is configured. Use that suite plus the syntax/static checks listed below.

## 3. Repo Structure

- `app.py`: PySide6 desktop application entry point, UI construction, widget application/collection for settings and recipe JSON, render worker threads, drag/drop and file picker wiring.
- `state_contract.py`: stdlib-only desktop persisted-state boundary. Owns schema 6, schema-3/4/5 migration, canonical defaults/Reset/serialization, malformed state repair, persisted effect activation identifiers/defaults, Zone definitions/eligibility/normalization, codec Layer identifiers/order normalization, Style FX persisted normalization, max-length load repair, and legacy audio/transition identities. It must not import Qt, renderer/codec/media modules, probe paths/media, or perform runtime planning.
- `app_i18n.py`: lightweight desktop UI localization resources and language fallback helpers.
- `renderer.py`: desktop render pipeline, canonical full-output/Preview window planning, timeline expansion, frame rendering, ANSI/chunky conversion, effects, bypass intervals, transitions/endings, explicit saved codec Layer dispatch, and optimization handoff.
- `datamosh.py`: authentic desktop MPEG-4 Part 2 I/P-VOP parsing/manipulation, canonical/persisted-order DATAMOSHING/Overflow/SKRRT/Scatter/Bleed operations, order-independent frozen event plans, deterministic last-writer execution, shared bounded temporal indexing, controlled-stream SKRRT reverse-prediction (Full Frame or Zone-composed full-size auxiliaries) and Scatter fragment preparation, a shared one-I/P-only auxiliary encoding/validation contract, and one safe silent H.264 transcode when any codec mode is enabled.
- `still_cache.py`: still-image loading and HEIC/HEIF proxy caching under the app-managed `StillCache` directory.
- `ffmpeg_utils.py`: ffmpeg/ffprobe discovery, probing, encoding, muxing, source audio building, audio mixing, optimization/transcode helpers.
- `presets.py`: ANSI/chunky style presets and descriptions.
- `theme.py`: PySide6 stylesheet and UI asset references.
- `run.py`, `run.sh`, `run_windows.bat`: source launchers.
- `build_app.sh`: macOS PyInstaller build, asset regeneration, explicit Qt pruning/companion-link cleanup, Info.plist versioning, ad-hoc signing, dangling-link rejection, and strict codesign verification.
- `scripts/package_dmg.sh`: validates an existing `dist/WZRD.VID.app`, copies it bundle-safely into a temporary DMG staging tree with `Applications -> /Applications`, creates a compressed read-only image, mounts and strictly revalidates its app, and writes `WZRD.VID-macOS.dmg`.
- `scripts/package_release.sh`: creates `WZRD.VID-macOS.zip` from `dist/WZRD.VID.app` using `ditto`.
- `scripts/generate_branding.py`, `scripts/generate_icon.py`, `scripts/generate_logo.py`, `scripts/generate_ui_textures.py`: generated branding/icon/texture asset scripts.
- `assets/`: desktop app assets, generated branding/icon/UI textures, public demo screenshots and demo video.
- `docs/`: GitHub Pages static site and project documentation. `docs/index.html` is the landing page; `docs/lite/` is the Lite app.
- `docs/i18n.js`: static UI localization resources shared by the landing page and Lite.
- `docs/I18N.md`: UI localization notes, fallback behavior, and language-addition workflow.
- `docs/assets/`: Pages copies of selected public assets.
- `apple-lite/`: WZRD.VID Lite Apple wrapper groundwork. The simulator-ready Xcode project lives at `apple-lite/WZRDVIDLite.xcodeproj`; SwiftUI/WKWebView sources live under `apple-lite/WZRDVIDLite/App/`; generated local web resources live under ignored `apple-lite/WZRDVIDLite/Resources/LiteWeb/`.
- `tests/`: tracked, rights-safe, deterministic desktop regression contracts for the Full Frame Material oracle, Material seed behavior, frame-effect Zones, schema-6 migration/repair, isolated settings state, canonical full-output/Preview planning semantics, controlled MPEG-4 structure/modes, Layer ordering, frame transport/failure classification, final H.264/AAC identity, source immutability, and temporary cleanup. It generates all frame/media fixtures at runtime in temporary directories, uses the Python standard-library `unittest` runner plus existing runtime dependencies/tools, and must not contain private media or generated evidence.
- `examples/`: placeholder docs for safe example media.
- `dist/`, `build/`, `.venv/`, `.pip-cache/`, `.pyinstaller-cache/`, `__pycache__/`: generated/local outputs; do not edit or commit.
- `demo/`: ignored local staging for demo media; do not treat as release-safe source.

Generated/build outputs that should not be edited directly:

- `dist/`, `build/`, `.venv/`, `.pip-cache/`, `.pyinstaller-cache/`, `__pycache__/`.
- `WZRD.VID-macOS.dmg` and `WZRD.VID-macOS.zip`.
- Generated assets in `assets/branding/`, `assets/logo/`, `assets/ui/`, `assets/wzrd_vid.*`, and `assets/wzrd_vid.iconset/` should normally be changed through their scripts, not hand-edited.
- `docs/assets/` contains deployable copies for Pages; update intentionally when public site assets change.
- `apple-lite/WZRDVIDLite/Resources/LiteWeb/` is generated by `python3 apple-lite/scripts/prepare_lite_web_bundle.py`; do not edit or commit it.

## 4. Agent Operating Rules

- Read `AGENTS.md` before every task.
- Read `docs/agent-log.md` before every task.
- Read `docs/agent-impact-map.md` before architecture, flow, rendering, deployment, or asset work.
- Read `docs/agent-change-playbook.md` before code changes.
- Append `docs/agent-log.md` after every meaningful file-changing task or important decision.
- Start from current worktree state with `git status --short --branch`.
- Keep changes small, scoped, and directly tied to the request.
- Do not rewrite architecture, UI structure, render flow, or deploy model without explicit permission.
- Do not change deploy/hosting config unless the task is deployment-related.
- Preserve user-facing content, typography, spacing, Jazz-cup/broadcast styling, and app behavior unless explicitly changing them.
- Do not invent product behavior. If repo evidence does not show a feature, write `Not present in repo`.
- Prefer minimal verified changes over broad refactors.
- Do not commit generated media, large local renders, or private/personal media.

## 5. Safety Rules

High-risk files/directories:

- `renderer.py`: affects output timing, frame conversion, effects, audio planning, bypass logic, optimization path.
- `datamosh.py`: affects persisted codec Layer ordering and last-writer composition, order-independent operation plans, temporary MPEG-4 prediction structure, bounded temporal indexing/window extraction/SKRRT Zone frame composition/exact frame-clocked fragment assembly/auxiliary encoding, the shared maximum scene-change-threshold and strict one-I/P-only auxiliary validator, material/transition event maps, Style-boundary anchors, frame/duration preservation, loop-tail protection, and the safe pre-audio H.264 intermediate.
- `still_cache.py`: affects still-image loading, HEIC/HEIF proxy generation, `StillCache` paths, cache keys, and cache cleanup targets.
- `ffmpeg_utils.py`: affects ffmpeg command construction, audio muxing/mixing, file size optimization, path safety.
- `app.py`: affects desktop UI, project settings, source timeline handling, render settings, worker threads.
- `state_contract.py`: affects settings/recipe migration, defaults, Reset, canonical JSON, Zones/assignments, codec Layer persistence, Style FX persisted state, and legacy identity repair. Keep it stdlib-only and preserve schema 6 unless an explicitly authorized schema phase says otherwise.
- `build_app.sh`: affects packaged macOS app, asset generation, Qt pruning and companion links, signing, strict bundle integrity, bundle version, and bundle identifier.
- `docs/index.html`, `docs/styles.css`, `docs/CNAME`: affect public site and custom-domain Pages behavior.
- `docs/lite/app.js`: affects browser-only Lite rendering, file privacy, MediaRecorder behavior.
- `apple-lite/`: affects future WZRD.VID Lite Apple app packaging. Keep it a local bundled Lite shell; do not add desktop renderer parity, ffmpeg, backend calls, analytics, accounts, or remote config.
- `assets/` and `docs/assets/`: public branding/demo assets and bundled app UI assets.
- `requirements.txt`: affects every source run and PyInstaller bundle.

Deployment/routing rules:

- GitHub Pages is served from `docs/`; changing `docs/index.html`, `docs/lite/`, `docs/assets/`, `docs/styles.css`, or `docs/CNAME` changes the public site.
- `docs/lite/index.html` routes via relative link `lite/` from the landing page.
- No backend routes or server framework are present.

Persistent data rules:

- Desktop settings live outside the repo: macOS `~/Library/Application Support/WZRD.VID/settings.json`, Windows `%APPDATA%/WZRD.VID/settings.json`, Linux `$XDG_CONFIG_HOME/wzrdvid/settings.json` or `~/.config/wzrdvid/settings.json`.
- Project presets are user-selected JSON files.
- Lite uses in-memory browser state, object URLs, Canvas, Web Audio, and MediaRecorder. Do not add uploads or persistence without explicit permission.

Asset/media rules:

- General media files are ignored by `.gitignore`; only release-safe assets under `assets/demos/`, `assets/screenshots/`, `docs/assets/demos/`, and `docs/assets/screenshots/` are allowed by negation rules.
- Do not add copyrighted sample media or personal footage.
- Keep Pages asset paths relative.
- If generated branding/UI assets are changed, update the generator script where practical and copy required public assets into `docs/assets/` intentionally.

Secrets/API key rules:

- Do not add secrets, tokens, private keys, API keys, personal paths, or private media.
- This repo does not require API keys for normal app/site operation.

## 6. Commands

Install/source run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Convenience launchers:

```bash
./run.sh
run_windows.bat
```

Static Pages preview:

```bash
python3 -m http.server 8770 --bind 127.0.0.1 --directory docs
```

macOS app build:

```bash
./build_app.sh
```

macOS bundle integrity after a packaging change:

```bash
find -L dist/WZRD.VID.app -type l -print
codesign --verify --deep --strict --verbose=4 dist/WZRD.VID.app
```

The dangling-link scan must print nothing and strict codesign must exit successfully before the bundle is release-ready.

Release ZIP:

```bash
scripts/package_release.sh
```

macOS drag-install DMG:

```bash
scripts/package_dmg.sh
```

The DMG script consumes the already-built app, verifies the source/staged/mounted copies, and must leave no mounted image or temporary staging tree after success or failure. It does not install into `/Applications`, sign with a production identity, notarize, publish, or replace user data.

Apple Lite bundle prep:

```bash
python3 apple-lite/scripts/prepare_lite_web_bundle.py
```

Apple Lite simulator smoke:

```bash
python3 apple-lite/scripts/run_simulator_smoke.py
```

Syntax/static checks:

```bash
python3 -m py_compile app.py state_contract.py app_i18n.py renderer.py datamosh.py ffmpeg_utils.py still_cache.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py
node --check docs/i18n.js
node --check docs/lite/app.js
git diff --check
```

Tracked desktop regression foundation:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Run this from the repository root. It requires the normal development environment from `requirements.txt` plus ffmpeg/ffprobe, uses no network, private media, or user settings, and must leave no repository artifacts. Run it after changes to frame-domain Material behavior, Zone normalization/rendering, schema/project state, Preview/playback/transition/tail planning, codec execution or Layer persistence, frame-pipe/PNG fallback classification, audio/final-media handling, or the tracked tests themselves.

Docs/link checks:

```bash
rg -n "REQUIRED TEXT OR SECTION" AGENTS.md docs/*.md README.md
python3 -m http.server 8770 --bind 127.0.0.1 --directory docs
curl -fsS http://127.0.0.1:8770/ >/dev/null
curl -fsS http://127.0.0.1:8770/lite/ >/dev/null
```

Deploy/preview:

- GitHub Pages deploys from pushed `main` branch `/docs` folder.
- No local deploy command or GitHub Actions workflow is present in this checkout.

## 7. Validation Matrix

| Change type | Minimum checks |
| --- | --- |
| Docs-only | `git status --short --branch`, `git diff --check`, targeted `rg` for required sections/terms. |
| UI/content-only desktop | Docs-only checks plus `python3 -m py_compile app.py theme.py`; offscreen screenshot if layout/wrapping may change. |
| UI/content-only Pages | Docs-only checks plus `node --check docs/lite/app.js` if Lite JS changed; local static server and `curl` landing/Lite pages. |
| Component logic desktop | `python3 -m py_compile app.py state_contract.py renderer.py datamosh.py ffmpeg_utils.py presets.py theme.py run.py`; run the tracked desktop regression suite when Material effects, Zones, schema/project state, Preview/playback/transition/tail planning, codec execution/Layer persistence, render transport/failure classification, or final audio/media handling are in scope; focused smoke for changed flow where practical. Persisted-state changes additionally require direct pure `state_contract.py` schema-3/4/5/6, malformed/default/Reset/canonicalization/idempotence tests plus at least one isolated offscreen MainWindow save/load or recipe integration check. Codec Layer changes additionally require old/malformed state migration, duplicate/unknown rejection, same-order determinism, meaningful overlapping order permutations, unchanged per-mode plans/intensity/auxiliary provenance, and source/package render checks. |
| Tracked desktop regression tests | Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_*.py'`; preserve the exact 18-case Material oracle hash, exact canonical spILL! counts, direct A-X repaired full-output/Preview planning expectations, strict controlled/auxiliary VOP rules, deterministic generated fixtures/media, isolated temporary settings, zero network/private media, source immutability, and zero repository output. Run twice when changing the tests or their fixture/oracle definitions, and include a reverse-module-order run. |
| Lite/browser logic | `node --check docs/lite/app.js`; local static server; browser/headless smoke if practical; grep for forbidden upload APIs when privacy-relevant. Lite audio changes also require source-off/source-only/Add-only/mixed output checks, source-to-visual-cut sync including still silence, and repeated-render/reset graph cleanup. |
| Apple Lite wrapper groundwork | `python3 apple-lite/scripts/prepare_lite_web_bundle.py`; `plutil -lint apple-lite/WZRDVIDLite/App/Info.plist`; Swift parse/build with the iPhone Simulator SDK if Xcode is installed; `python3 apple-lite/scripts/run_simulator_smoke.py` when simulator UI behavior is in scope; for audio changes require exported-file track and PCM/frequency evidence rather than track count alone; keep generated `LiteWeb/` and `DerivedData/` out of git. |
| Routing/navigation | Local static server; `curl` changed pages; verify relative asset/link paths. |
| Build/deploy config | `git diff --check`; inspect affected build/package or Pages config; run `./build_app.sh` when packaging behavior changed; require a clean `find -L dist/WZRD.VID.app -type l -print`, successful `codesign --verify --deep --strict --verbose=4`, and normal app launch. DMG changes also require `bash -n scripts/package_dmg.sh`, two structural package passes when practical, mounted-image app/link/content validation, failure cleanup, and an isolated replacement/user-data preservation smoke. |
| Dependency/package changes | Explain why existing deps are insufficient; `pip install -r requirements.txt`; relevant py_compile/build checks. |
| Asset/media changes | Confirm file sizes and rights; verify `.gitignore` does not block intended release-safe assets; check consuming page/app path. |

## 8. Required Task Ending Format

Every future task must end with:

1. Concise summary
2. Files changed
3. Behavior changed: yes/no
4. Tests added
5. Commands run
6. Checks passed/failed
7. Known gaps
8. Agent log updated: yes/no
9. Exact next recommended prompt

If something is unclear, write `Unknown` and include the exact command or file inspection needed to verify it.
