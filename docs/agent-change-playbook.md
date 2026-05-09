# wzrdVID Agent Change Playbook

Read this before code changes. It complements `AGENTS.md`, `docs/agent-log.md`, and `docs/agent-impact-map.md`. Keep changes small, verified, and faithful to current product behavior unless the user explicitly asks for a broader shift.

## 1. Docs-Only

- Inspect first: `README.md`, relevant `docs/*.md`, `LICENSE`, `NOTICE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/agent-log.md`.
- Searches to run: stale product names/licensing terms; required headings; broken referenced file paths.
- Common mistakes to avoid: changing app behavior docs without repo evidence; reintroducing AGPL/open-source claims; editing generated outputs.
- High-risk files: `LICENSE`, `NOTICE.md`, `README.md`, release/download docs.
- Required checks: `git status --short --branch`; `git diff --check`; targeted `rg` checks.
- Update `AGENTS.md` when: commands, rules, validation expectations, or repo boundaries change.
- Update `docs/agent-impact-map.md` when: docs reveal new architecture/deployment/high-risk surfaces.
- Update `docs/agent-log.md` when: files changed or an important decision was made.

## 2. Copy/Text/Content

- Inspect first: `README.md`, `docs/index.html`, `docs/lite/index.html`, `app.py`, `theme.py`, legal docs if rights copy is nearby.
- Searches to run: exact old copy, brand strings, stale names, licensing terms, `sam.mode`/`worky.mode` style identity references when relevant.
- Common mistakes to avoid: broad rewrites, accidental legal changes, changing layout to fit copy without instruction.
- High-risk files: `README.md`, `docs/index.html`, `docs/lite/index.html`, `app.py` header/status copy.
- Required checks: docs-only checks; local visual preview if text length/wrapping changed; `py_compile` if Python string changes are inside code.
- Update `AGENTS.md` when: public terminology rules change.
- Update `docs/agent-impact-map.md` when: content changes affect flows/download/deployment behavior.
- Update `docs/agent-log.md` after the task.

## 3. Styling/Layout

- Inspect first: `theme.py`, `app.py` layout code, `docs/styles.css`, `docs/lite/styles.css`, visible assets in `assets/ui/` and `docs/assets/`.
- Searches to run: existing style constants/classes, hardcoded colors, image asset references.
- Common mistakes to avoid: text overlap, noisy controls, inaccessible contrast, redesigning structure when only polish was requested.
- High-risk files: `theme.py`, `app.py`, `docs/styles.css`, `docs/lite/styles.css`.
- Required checks: syntax checks; GUI/site screenshots or local browser preview; `git diff --check`.
- Update `AGENTS.md` when: visual identity rules or screenshot QA expectations change.
- Update `docs/agent-impact-map.md` when: new style asset systems or layout architecture are introduced.
- Update `docs/agent-log.md` after the task.

## 4. Shared Component

- Inspect first: component/widget definitions in `app.py`, shared stylesheet in `theme.py`, shared Lite/site components if any.
- Searches to run: class/function names, signal connections, settings keys, usages in save/load/render code.
- Common mistakes to avoid: breaking project preset restore, drag/drop events, table columns, or render-thread signal behavior.
- High-risk files: `app.py`, `theme.py`, `docs/lite/app.js` if browser UI component logic is affected.
- Required checks: `py_compile`; targeted GUI workflow; save/load smoke when controls persist state.
- Update `AGENTS.md` when: new required validation or operating procedure is introduced.
- Update `docs/agent-impact-map.md` when: shared component ownership or data flow changes.
- Update `docs/agent-log.md` after the task.

## 5. Page/Route

- Inspect first: `docs/index.html`, `docs/lite/index.html`, `docs/CNAME`, relative assets/links, `docs/RELEASE_DOWNLOAD_HELP.md`.
- Searches to run: href/src paths, `/lite/`, release URLs, CNAME/domain strings.
- Common mistakes to avoid: root-relative paths that fail under GitHub Pages, breaking custom domain, hiding release download guidance.
- High-risk files: `docs/CNAME`, `docs/index.html`, `docs/lite/index.html`.
- Required checks: local static server from `docs/`; link/path spot checks; browser/mobile-ish preview if layout changed.
- Update `AGENTS.md` when: deployment/routing rules change.
- Update `docs/agent-impact-map.md` when: routes/pages or hosting model changes.
- Update `docs/agent-log.md` after the task.

## 6. App Logic/State

- Inspect first: `app.py`, `renderer.py`, `ffmpeg_utils.py`, project save/load code, settings defaults and migration behavior.
- Searches to run: affected setting key, dataclass field, UI control name, project JSON serializer/deserializer.
- Common mistakes to avoid: changing settings schema without backward handling, blocking the UI thread, losing paths with spaces, breaking audio/render sync.
- High-risk files: `app.py`, `renderer.py`, `ffmpeg_utils.py`.
- Required checks: `python3 -m py_compile app.py renderer.py ffmpeg_utils.py presets.py theme.py run.py`; focused smoke test for affected flow.
- Update `AGENTS.md` when: new command/check is required for future agents.
- Update `docs/agent-impact-map.md` when: state/data flow changes.
- Update `docs/agent-log.md` after the task.

## 7. Video/Media Handling

- Inspect first: `renderer.py`, `ffmpeg_utils.py`, `app.py` media import/preview code, relevant README docs.
- Searches to run: `TimelineItem`, `RenderSettings`, `parse_timecode`, `has_audio_stream`, `mux_audio`, `build_timeline_audio`, `MediaRecorder` for Lite.
- Common mistakes to avoid: audio desync, unsupported image orientation, temp file leaks, final codec regression, path quoting bugs.
- High-risk files: `renderer.py`, `ffmpeg_utils.py`, `app.py`, `docs/lite/app.js`.
- Required checks: `py_compile`; tiny render or Lite render smoke; `ffprobe` final output if codec/audio changed; grep network APIs for Lite privacy changes.
- Update `AGENTS.md` when: new media safety rules are discovered.
- Update `docs/agent-impact-map.md` when: media pipeline modules/flows change.
- Update `docs/agent-log.md` after the task.

## 8. Asset/Static File Changes

- Inspect first: `assets/README.md`, `.gitignore`, `assets/`, `docs/assets/`, generator scripts, README/site references.
- Searches to run: asset filename references, old names, ignored file status with `git check-ignore -v` if needed.
- Common mistakes to avoid: committing huge/copyrighted media, deleting official branding, updating generated outputs without source/generator clarity.
- High-risk files/directories: `assets/branding/`, `assets/logo/`, `assets/ui/`, `docs/assets/`, `.gitignore`.
- Required checks: file-size listing; path reference check; preview/readme/site check for visible assets.
- Update `AGENTS.md` when: asset policy changes.
- Update `docs/agent-impact-map.md` when: new asset ownership/generation paths are added.
- Update `docs/agent-log.md` after the task.

## 9. Dependency/Package Changes

- Inspect first: `requirements.txt`, imports/usages, `build_app.sh`, README install docs, `docs/CROSS_PLATFORM.md`.
- Searches to run: package import name, dependency-specific docs in repo, PyInstaller excludes/hooks if relevant.
- Common mistakes to avoid: bloating the app bundle, breaking cross-platform source runs, adding dependency for simple standard-library work.
- High-risk files: `requirements.txt`, `build_app.sh`, `ffmpeg_utils.py`, `renderer.py`, `app.py`.
- Required checks: venv install/update; `py_compile`; app launch/source run; build smoke if packaging affected.
- Update `AGENTS.md` when: install/test commands change.
- Update `docs/agent-impact-map.md` when: dependency responsibilities or risk map changes.
- Update `docs/agent-log.md` after the task.

## 10. Build Config

- Inspect first: `build_app.sh`, `scripts/package_release.sh`, `requirements.txt`, icon/branding generators, `.gitignore`.
- Searches to run: app name, bundle id, PyInstaller excludes, icon path, `dist/WZRD.VID.app`, release zip name.
- Common mistakes to avoid: breaking Finder launch, removing needed Qt plugins, changing app identity, committing generated build outputs.
- High-risk files: `build_app.sh`, `scripts/package_release.sh`, `requirements.txt`, generator scripts.
- Required checks: script syntax; `./build_app.sh` when packaging behavior changed; `scripts/package_release.sh` when release zip behavior changed; Finder launch if app bundle changed.
- Update `AGENTS.md` when: build commands or packaging rules change.
- Update `docs/agent-impact-map.md` when: build output/dependency flow changes.
- Update `docs/agent-log.md` after the task.

## 11. GitHub Pages/Deployment

- Inspect first: `docs/CNAME`, `docs/index.html`, `docs/styles.css`, `docs/lite/*`, release/download docs, GitHub Pages settings if using `gh`/browser.
- Searches to run: custom domain, release URL, `docs/assets`, `lite/`, root-relative paths.
- Common mistakes to avoid: changing Pages source/domain casually, assuming DNS/HTTPS state without live verification, confusing Source ZIP with Release ZIP.
- High-risk files: `docs/CNAME`, `docs/index.html`, `docs/lite/*`, release docs.
- Required checks: local static preview; link/path checks; live HTTP checks if deployment state is part of the task.
- Update `AGENTS.md` when: hosting/deploy procedure changes.
- Update `docs/agent-impact-map.md` when: deployment model changes.
- Update `docs/agent-log.md` after the task.

## 12. Broad Refactor

- Inspect first: `AGENTS.md`, `docs/agent-log.md`, `docs/agent-impact-map.md`, this playbook, all affected modules.
- Searches to run: dependency graph around affected files, settings/project keys, UI strings, media flow functions, docs references.
- Common mistakes to avoid: architecture rewrites without explicit permission, mixing unrelated cleanup, changing public identity or deployment as collateral.
- High-risk files: any central module (`app.py`, `renderer.py`, `ffmpeg_utils.py`, `theme.py`, `build_app.sh`, `docs/index.html`, `docs/lite/app.js`).
- Required checks: combine all relevant matrices; use staged incremental validation; summarize behavior changes explicitly.
- Update `AGENTS.md` when: procedures, commands, or safety rules change.
- Update `docs/agent-impact-map.md` when: architecture, flows, dependencies, or high-risk files change.
- Update `docs/agent-log.md` after the task.

## Standing Rules

- Do not touch deployment config casually.
- Do not edit generated build output unless the repo intentionally deploys generated output.
- Do not add dependencies without explaining why existing code cannot do the job.
- Do not rewrite layout or app structure unless explicitly requested.
- Preserve GitHub Pages compatibility.
- Preserve the no-upload privacy boundary for WZRD.VID Lite.
- Preserve source-available licensing and reserved branding language unless explicitly instructed by the user.
