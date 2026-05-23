# wzrdVID Agent Documentation System Audit

Date: 2026-05-23

Scope: audit the current GitNexus-style agent documentation substitute using repository evidence, git history, the current agent docs, selected source inspections, release metadata, and live HTTP/header checks for the public Pages routes. No app behavior was changed.

## 1. Executive Assessment

The agent-docs system effectively mapped the wzrdVID repository. It created a durable operating model around `AGENTS.md`, `docs/agent-log.md`, `docs/agent-impact-map.md`, and `docs/agent-change-playbook.md`, and later work generally followed that model: tasks started from repo state, entries recorded intent and no-touch boundaries, and high-risk surfaces such as the desktop renderer, Lite runtime, Apple Lite signing, GitHub Pages, generated assets, and release ZIPs were repeatedly handled with explicit scope control.

It is still useful. The current docs are strong enough for a future agent to orient quickly, avoid broad refactors, find the relevant validation commands, and distinguish repo evidence from live release/Pages evidence.

It has helped future agents work more safely, based on repo evidence. The log repeatedly records required doc reads, targeted checks, failed/recovered checks, generated-output avoidance, and explicit boundaries around signing IDs, Bundle IDs, release assets, `docs/CNAME`, Lite privacy behavior, and desktop renderer changes. Causation cannot be proven from git history alone, but the pattern after the docs were introduced is materially safer and more traceable than a plain README-only workflow.

It is likely to continue helping if kept fresh. The biggest risk is drift in the check commands and module map, especially around `still_cache.py`, Apple Lite asset catalogs, and release/App Store operational docs that evolved after the initial system.

Overall grade: A.

Confidence level: high for static repo and git-history findings; medium for claims that the docs caused safer behavior. The evidence shows compliance and useful outcomes, but git history cannot prove agent intent.

## 2. Source Docs Inventory

| File path | Purpose | Last meaningful update | Instructed to read? | Overlap | Stale? | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | Root operating guide, repo structure, safety rules, commands, validation matrix, task-ending format. | `8911687` / 2026-05-10 / Apple Lite Xcode project and smoke. | Yes, before every task. | Overlaps impact map, playbook, release docs. | Mostly current, but misses `still_cache.py` in repo structure/checks and does not name support/privacy routes or Apple Lite app-icon assets in high-risk areas. | Keep and update. |
| `docs/agent-log.md` | Reverse-chronological working memory for tasks, checks, known gaps, next prompt. | `ba63b59` / 2026-05-22 / AMPYX signing setup. | Yes, before every task and append after meaningful file changes unless task scope forbids it. | Overlaps changelog, performance notes, Apple Lite logs. | Current but large. One post-system commit (`6c403c3`) changed docs without a log update. One entry is missing a `Files changed` line. | Keep. Add a short audit entry in a later allowed pass. |
| `docs/agent-impact-map.md` | Architecture/data-flow map, high-risk file table, verification matrix. | `c86db3d` / 2026-05-22 / support/privacy Pages drafts. | Yes before architecture, flow, rendering, deployment, or asset work. | Overlaps AGENTS and playbook. | Mostly accurate, but `still_cache.py` is only implicit in the data map and absent from high-risk/check tables; Apple Lite `Assets.xcassets/AppIcon.appiconset` is not called out specifically. | Keep and update. |
| `docs/agent-change-playbook.md` | Change-type checklists for docs, copy, localization, UI, app logic, media, Apple Lite, assets, deps, build, Pages, refactors. | `8911687` / 2026-05-10 / Apple Lite Xcode project and smoke. | Yes before code changes. | Overlaps AGENTS validation matrix and impact map. | Useful but check commands omit `still_cache.py` in app/media logic and some sections still use shorter compile commands. | Keep and update. |
| `docs/RELEASE_CHECKLIST.md` | Release preparation checklist for legal/docs, hygiene, build, ZIP, GitHub metadata. | `7578447` / 2026-05-09 / v0.1.8 maintenance. | Conditional, for release/package work. | Overlaps README, install/download help, AGENTS commands. | Stale in examples (`v0.1.1`) and compile command omissions (`app_i18n.py`, `still_cache.py`, Apple Lite scripts). | Keep and update before the next release. |
| `docs/RELEASE_DOWNLOAD_HELP.md` | Normal-user release asset vs source ZIP guidance and build/package instructions. | `6c403c3` / 2026-05-10 / update status README wording. | Conditional, for release/download docs. | Overlaps README and install guide. | Mostly current; points to latest release asset and says updater is notifier-only. | Keep. |
| `docs/INSTALL_MAC.md` | Mac install/update support doc for the current packaged ZIP. | `6c403c3` / 2026-05-10 / update status README wording. | Conditional, for install/download work. | Overlaps README and release download help. | Mostly current; still says unsigned/unnotarized and Apple Silicon-focused, matching repo docs. | Keep. |
| `docs/CROSS_PLATFORM.md` | Cross-platform source-run boundaries and best-effort Windows/Linux status. | `7578447` / 2026-05-09 / v0.1.8 maintenance. | Conditional, for platform/release work. | Overlaps README and AGENTS. | Current unless packaged platform support changes. | Keep. |
| `docs/PERFORMANCE_NOTES.md` | Evidence log for long-media, HEIC, frame-pipe, and Lite/Apple portability performance decisions. | `ef5b75d` / 2026-05-13 / Lite Apple portability audit. | Conditional, for performance/media work. | Overlaps agent log and impact map. | Dated sections are accurate historically but can confuse because older frame-pipe notes were superseded by later default-frame-pipe behavior. | Keep, add supersession note. |
| `docs/APPLE_LITE_APP_RESEARCH.md` | Apple Lite app path, requirements, Bundle ID/team evidence, native shell boundaries. | `ba63b59` / 2026-05-22 / AMPYX signing setup. | Conditional, for Apple Lite/signing/App Store work. | Overlaps App Store prep, device log, Apple Lite README. | Current; correctly labels current IDs as repo evidence only. | Keep. |
| `docs/APPLE_LITE_DEVICE_TEST_LOG.md` | Physical/simulator Apple Lite test history, blockers, manual matrix, boundaries. | `ba63b59` / 2026-05-22 / AMPYX signing setup. | Conditional, for Apple Lite/device work. | Overlaps agent log and App Store prep. | Current but long. | Keep. |
| `docs/APPLE_LITE_APP_STORE_PREP.md` | App Store Connect, privacy, metadata, support/privacy URL, screenshot and signing prep. | `ba63b59` / 2026-05-22 / AMPYX signing setup. | Conditional, for App Store work. | Overlaps Apple research, asset plan, public support/privacy pages. | Current; explicitly marks unresolved AMPYX/signing/privacy-manifest gaps. | Keep. |
| `docs/APPLE_LITE_APP_ASSET_PLAN.md` | Apple Lite app icon and screenshot asset plan, simulator capture workflow, approved dry-run baseline. | `e25206e` / 2026-05-22 / screenshot baseline approval. | Conditional, for Apple Lite asset/screenshot work. | Overlaps App Store prep and device log. | Current; screenshots remain dry-run only. | Keep. |
| `apple-lite/README.md` | Apple Lite wrapper setup, bundle prep, Xcode project, simulator smoke, manual smokes. | `fcfb150` / 2026-05-12 / Lite render coverage and smoothness. | Conditional through Apple Lite playbook. | Overlaps Apple research/device/prep docs. | Mostly current but predates the AppIcon catalog and later AMPYX checklist. | Update. |
| `docs/support/index.html` | Public support route for App Store prep and Lite user help. | `c86db3d` / 2026-05-22 / support/privacy drafts. | Conditional, for Pages/App Store support work. | Overlaps App Store prep. | Current draft; AMPYX contact details still placeholders. | Keep and update before App Store submission. |
| `docs/privacy/index.html` | Public privacy policy route for App Store prep. | `c86db3d` / 2026-05-22 / support/privacy drafts. | Conditional, for Pages/App Store privacy work. | Overlaps App Store prep. | Current draft; legal/contact review still pending. | Keep and update before App Store submission. |

## 3. Mapping Quality Audit

| Area checked | Classification | Evidence and notes |
| --- | --- | --- |
| Desktop Python/PySide6 app entry points | Mostly accurate but needs update | `app.py`, `run.py`, `run.sh`, and `run_windows.bat` match the docs. `app_i18n.py` is described, but default check commands should include it consistently. `still_cache.py` is imported by `app.py` and `renderer.py` but is not first-class in AGENTS or the high-risk table. |
| Renderer/media pipeline | Mostly accurate but needs update | `renderer.py` matches the impact map: timeline expansion, frame pipe default, PNG fallback, HEIC handling, bypass, transitions/endings, optimization handoff. Missing first-class map entry for `still_cache.py`. |
| ffmpeg/ffprobe utilities | Accurate | `ffmpeg_utils.py` covers discovery, probing, raw RGB pipe encoding, PNG sequence encoding, audio trim/mux/mix, source timeline audio, and optimization. It uses subprocess argument lists rather than `shell=True` for normal paths. |
| Settings/project JSON handling | Accurate | `app.py` owns settings path, recipe import/export, schema restoration, max-length normalization, and local persistent settings. |
| Preview/render/batch/export flows | Accurate | `RenderThread`, `BatchRenderThread`, preview path creation, batch variants, output/open-folder behavior, and cache cleanup are in `app.py`; rendering is delegated to `renderer.py`. |
| Audio/source-audio/mixing behavior | Accurate | Impact map descriptions match `renderer.py` and `ffmpeg_utils.py`: external/source/mix modes, source-audio extraction, worky audio delay ordering, and match-to-music restrictions. |
| WZRD.VID Lite browser app | Accurate | `docs/lite/app.js` uses Canvas, Web Audio/MediaRecorder, local object URLs, reset cleanup, HEIC browser-limited import, no network APIs from grep evidence, and no upload path. |
| Static GitHub Pages site under `docs/` | Mostly accurate but needs update | `docs/index.html`, `docs/styles.css`, `docs/CNAME`, `docs/lite/`, `docs/support/`, and `docs/privacy/` match the map. `AGENTS.md` should name support/privacy routes as Pages-impacting files. Live `https://wzrdvid.com/`, `/lite/`, `/support/`, and `/privacy/` returned HTTP 200 during this audit. |
| Apple Lite/App Store/signing setup docs | Mostly accurate but needs update | Current Xcode project evidence matches docs: `com.samhowell.wzrdvid.lite`, team `JKSWZ8682X`, version/build `0.2.0`/`1`, AppIcon catalog, local `LiteWeb`, Photos usage strings. The impact map should call out `Assets.xcassets/AppIcon.appiconset` and the privacy-manifest gap directly. |
| macOS packaging/release scripts | Mostly accurate but needs update | `build_app.sh` uses PyInstaller, asset generation, Info.plist versioning from `VERSION`, bundle ID `com.samhowell.wzrdvid`, and ad-hoc codesign. `scripts/package_release.sh` creates `WZRD.VID-macOS.zip` with `ditto`. Release checklist is the stale part. |
| Generated assets and branding | Mostly accurate but needs update | Generated desktop branding/icon/UI assets and Pages copies are documented. Apple Lite app-icon PNG slots are generated/committed but not specifically named in main impact-map asset guidance. |
| Public release/update-check behavior | Accurate from repo, live release verified | `app.py` uses GitHub Releases API with release-page fallback and notifier-only UI. `gh release view` reported latest `v0.2.1`, asset `WZRD.VID-macOS.zip`, SHA256 `d1535c08ed71791afb3351d25c164711d8d9cb406b545bc8e93488176db7a61a`, published 2026-05-14. |
| GitHub Releases/download guidance | Accurate | README/install/help docs point users to `WZRD.VID-macOS.zip` under Releases and distinguish Source ZIP. Live release asset exists and matches the documented current version. |
| GitHub Pages/custom domain behavior | Mostly accurate but needs update | Repo evidence: `docs/CNAME` contains `wzrdvid.com`; no `.github` workflows exist; Pages is documented as `/docs` on `main`. Live route headers returned 200. GitHub dashboard settings cannot be proven from repo alone. |
| Tests/check commands | Mostly accurate but needs update | Docs-only checks are good. Syntax commands should include `app_i18n.py`, `still_cache.py`, `docs/i18n.js`, and Apple Lite scripts where relevant. `docs/RELEASE_CHECKLIST.md` is behind current practice. |
| Ignored/generated outputs | Accurate | `.gitignore` and `apple-lite/.gitignore` ignore `.venv/`, caches, `build/`, `dist/`, `WZRD.VID-macOS.zip`, `demo/`, `DerivedData/`, and generated `LiteWeb/`. `git status --short --ignored` shows those ignored outputs present but untracked. |
| High-risk files | Mostly accurate but needs update | Core high-risk files are identified. Add `still_cache.py`, `docs/support/index.html`, `docs/privacy/index.html`, Apple Lite `Assets.xcassets`, and release checklist/download docs to the explicit high-risk set. |
| Verification matrix | Mostly accurate but needs update | The matrix matches repo practice but should be refreshed for `still_cache.py`, `app_i18n.py`, `docs/i18n.js`, Apple Lite asset catalog checks, release digest checks, and live Pages checks when a Pages deployment is in scope. |

## 4. Agent Log Usefulness Audit

The log is doing its job. It has 85 task entries, reverse chronological order, and every entry has known gaps plus a next recommended prompt. 84 of 85 entries include file-change information and behavior-change information. The exception is `2026-05-12 - Apple Lite Bucket 1/2 deploy and final smoke`, which records pushed commits but does not include a literal `Files changed` line.

Entries after meaningful tasks are present. From `65b804a` onward, only one file-changing commit lacked a `docs/agent-log.md` change: `6c403c3 Fix update status README wording`, which changed `README.md`, `docs/INSTALL_MAC.md`, and `docs/RELEASE_DOWNLOAD_HELP.md`.

The entries accurately summarize changed files in most cases. They frequently preserve no-touch boundaries, especially around desktop renderer behavior, Lite runtime, Apple Lite runtime, signing IDs, Bundle IDs, App Store metadata, GitHub Releases, GitHub Pages config, generated media, and release assets.

The log records failed/recovered checks well. Examples include SSH public-key auth blocked then HTTPS/GitHub CLI fallback for release/push work, simulator/physical-device blockers, Playwright/Browser limitations with Brave/Computer Use fallback, system Python missing dependencies with `.venv` recovery, old packaged app launch constraints, and physical iPhone availability problems.

The log helps later agents resume. It records exact SHA256 values, release URLs, final prompts, screenshot directories under `/tmp`, live Pages verification, version states, smoke matrices, and unresolved App Store/AMPYX gaps.

Weak points:

- The log is long enough that future agents may skim only the newest entries.
- Some early entries are less complete than current entries.
- One post-system commit missed a log entry.
- The log records many operational facts that also live in Apple Lite docs and performance notes; this is useful for evidence, but duplication can drift.

## 5. Evidence of Usefulness

Evidence from git history and docs supports usefulness, but does not prove causation.

- The required task-ending format became common in log entries: intent, files changed, behavior changed, commands, checks, known gaps, and next prompt are usually present.
- Many entries explicitly state "required repo docs reads" before work.
- Architecture-affecting work often updated `docs/agent-impact-map.md`, including Apple Lite wrapper additions, frame-pipe changes, HEIC/still-cache work, Lite reset/HEIC import work, support/privacy Pages additions, and audio placement changes.
- Docs-only tasks stayed docs-only in several high-risk areas: Apple Lite App Store prep, screenshot planning, AMPYX signing setup, screenshot baseline approval, release publication logs, and performance findings.
- The no-touch boundaries became very explicit. Recent entries repeatedly preserved desktop renderer behavior, Lite runtime behavior, Apple Lite runtime behavior, signing IDs, Bundle IDs, App Store Connect records, App Store/DUNS metadata, GitHub Releases, GitHub Pages config, release assets, screenshots, generated outputs, and unrelated files.
- GitHub Release handling became evidence-based: log entries record asset size, SHA256, GitHub digest, fresh download checks, and unzipped plist/version checks.
- GitHub Pages and Lite privacy handling stayed cautious: entries record local/static checks, live hash/marker checks, and forbidden-network grep checks.
- Apple Lite work stayed scoped: the docs distinguish bundled local `LiteWeb` from a remote wrapper, dev Bundle ID from preferred production Bundle ID, and dry-run screenshot evidence from final App Store assets.

Counterevidence:

- `6c403c3` changed release/install docs without updating `docs/agent-log.md`.
- `still_cache.py` was introduced and used by desktop app/render flows but did not become first-class in AGENTS, the impact map high-risk table, or standard compile commands.
- Some release checklist commands lag behind actual practice.

## 6. Drift and Missed Coverage

Important drift or missed coverage:

- `still_cache.py` is the biggest current gap. It owns HEIC proxy caching, the `StillCache` path, cache target enumeration, and ffmpeg-backed still decode. It is referenced in `app.py` and `renderer.py`, but the agent docs do not consistently list it as a module, high-risk file, or compile target.
- `app_i18n.py` is documented but omitted from some canonical compile commands.
- `docs/i18n.js` should be included in the normal static/Lite syntax check whenever site or Lite text changes; some docs mention it, some do not.
- Apple Lite `Assets.xcassets/AppIcon.appiconset/` is now committed and operational. The Apple Lite docs know this, but the main impact map should call it out directly.
- `docs/support/index.html` and `docs/privacy/index.html` now matter for App Store support/privacy URLs and Pages. The impact map mentions them, but AGENTS high-risk/site rules should too.
- `docs/RELEASE_CHECKLIST.md` still uses old example tags (`v0.1.1`) and an older syntax command.
- `docs/PERFORMANCE_NOTES.md` has older dated sections saying the frame pipe was experimental or default PNG staging remained the default. Later sections supersede that, but a top note should prevent misreading.
- Ignored generated outputs are present locally (`WZRD.VID-macOS.zip`, `build/`, `dist/`, `.venv/`, caches, Apple Lite `DerivedData/`, generated `LiteWeb/`). The docs warn about these correctly.
- Current dev signing IDs (`com.samhowell.wzrdvid.lite`, `JKSWZ8682X`) are not stale because docs label them as repo evidence only. They remain a footgun if copied into production work without reading the Apple Lite docs.
- `worky.mode / wzrdgang` still appears in `app.py` UI copy. The playbook already says to search old identity/worky.mode references when relevant. Repo evidence does not prove these are stale; treat them as intentional UI/brand copy unless a product decision says otherwise.

No evidence was found of:

- New `.github` workflows.
- A formal Python test suite.
- A configured markdown linter.
- Backend/server runtime for Pages or Lite.
- Official packaged Windows/Linux builds.

## 7. Agent Compliance Audit

Recent agent work mostly follows the operating rules.

- Scoped changes: mostly yes. Commits and log entries stay focused and repeatedly state no-touch surfaces.
- Relevant checks: mostly yes. Logs show Python compile, JavaScript syntax, `git diff --check`, static server/curl, forbidden-network grep, simulator smoke, plist lint, Xcode builds, release ZIP checks, ffprobe output validation, and live release/download checks when relevant.
- Agent log updates: mostly yes. One known miss: `6c403c3`.
- Docs-only tasks avoiding app behavior changes: yes, based on changed files and log text for the recent Apple Lite/App Store prep and screenshot evidence tasks.
- Desktop renderer preservation when not requested: yes in recent Apple Lite, signing, screenshot, and release-publication tasks.
- No-touch surfaces preserved: mostly yes. Logs explicitly avoid Lite runtime, GitHub Pages config, release assets, signing IDs, Bundle IDs, App Store Connect records, App Store/DUNS metadata, screenshots, generated outputs, and desktop renderer behavior unless authorized.
- Local checks vs public evidence: mostly yes. Release entries distinguish local ZIPs, GitHub asset metadata, fresh downloads, live Pages hashes, and current repo state.
- Architecture invention: mostly avoided. Docs say "Not present in repo" or record explicit evidence gaps.

Compliance gaps:

- One docs commit missed the agent log.
- Some current check commands in docs lag behind actual source file set.
- The agent-log append rule conflicts with this audit's user instruction not to edit `docs/agent-log.md` yet; this audit intentionally leaves the log unchanged and records that as a known gap.

## 8. Risk Audit

| Footgun | Why risky | Current doc warning | Add this wording/check |
| --- | --- | --- | --- |
| `still_cache.py` under-documented | It controls HEIC proxy decode/cache and cleanup targets; mistakes can break photo import or delete the wrong cache files. | Only implicit in impact map data map and log entries. | Add `still_cache.py` to AGENTS repo structure, high-risk files, impact map major modules, and compile commands. |
| Desktop renderer/media/audio pipeline | `renderer.py` and `ffmpeg_utils.py` affect timing, effects, source audio, mix placement, codec output, optimization, and temp cleanup. | Strong warnings in AGENTS, impact map, playbook. | Keep requiring focused render/audio/ffprobe smokes after changes. |
| ffmpeg path/probe/codec behavior | Path quoting, probe cache mutation, adelay/worky order, AAC/H.264 output, and size targeting are easy to regress. | Impact map and playbook warn. | Add a small "do not mutate probe dicts; preserve subprocess list args" note to AGENTS safety rules. |
| PyInstaller/macOS bundle/signing | App identity, Qt pruning, Info.plist versioning, ad-hoc signing, and release ZIP behavior can break installed app launches. | AGENTS, impact map, release docs. | Refresh release checklist with current compile files, `bash -n build_app.sh scripts/package_release.sh`, build/package/plist/launch checks. |
| Apple Lite dev IDs vs production IDs | Current `com.samhowell.wzrdvid.lite` and `JKSWZ8682X` are repo evidence, not final AMPYX production identity. | Apple Lite docs warn clearly. | Also add a short warning in AGENTS Apple Lite safety bullet. |
| Apple Lite docs vs runtime source | App Store prep/docs can overstate behavior if runtime changes; Lite source audio remains future work. | Apple docs and support page note limitations. | Require `rg` evidence for runtime claims and simulator smoke before changing App Store copy. |
| GitHub Releases assets | Source ZIP vs release ZIP confusion, stale checksums, or asset replacement can mislead users. | Release/download docs and log entries. | Require `gh release view --json tagName,assets,publishedAt,isDraft,isPrerelease` plus SHA/digest in release tasks. |
| GitHub Pages/custom domain | `docs/CNAME`, relative paths, support/privacy routes, and Lite links affect public site and App Store URLs. | AGENTS/impact/playbook warn. | Add support/privacy routes to AGENTS high-risk Pages bullet and require local curl before push plus live curl after deployment when in scope. |
| WZRD.VID Lite no-upload/privacy behavior | A network API, cache, service worker, analytics, or remote wrapper would violate the product boundary. | Strong AGENTS/playbook/impact warnings. | Standardize forbidden grep to include `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`, `indexedDB`, `caches`, `serviceWorker`, and external Swift navigation. |
| Generated branding/icon/texture assets | Hand edits can drift from generators; large media can be accidentally committed. | AGENTS and asset playbook warn. | Add Apple Lite AppIcon-specific note and require file-size/path-reference checks. |
| Public update-check behavior | It is notifier-only and relies on GitHub Releases; changing it can create false update or auto-install expectations. | README/install/help and app code. | Add update-check helper smoke to release/update docs and say no auto-download/install unless explicitly requested. |
| Accidental broad refactors | `app.py` is large and tightly wired; broad "cleanup" can break settings, recipes, UI state, render threads, or localization. | Strong AGENTS/playbook warnings. | Require user approval and a staged validation matrix for broad refactors. |

## 9. Recommended Updates

### P0 - Must Fix Now

| File to update | Why | Suggested wording or section | Scope | Verification command |
| --- | --- | --- | --- | --- |
| `AGENTS.md` | Standard checks omit current source files. | In "Syntax/static checks", include `app_i18n.py` and `still_cache.py`; include `node --check docs/i18n.js` beside `docs/lite/app.js`. | Docs-only. | `rg -n "still_cache.py|app_i18n.py|docs/i18n.js" AGENTS.md && git diff --check` |
| `docs/agent-impact-map.md` | `still_cache.py` is not first-class despite owning HEIC proxy/cache behavior. | Add a "Still Image Cache" module or expand Render Engine owning files to include `still_cache.py`; add it to high-risk files and verification matrix. | Docs-only. | `rg -n "still_cache.py|Still Image Cache|StillCache" docs/agent-impact-map.md && git diff --check` |
| `docs/agent-change-playbook.md` | App/media checklists omit `still_cache.py` and inconsistent check commands can under-validate. | Under App Logic/State and Video/Media Handling, add `still_cache.py` to inspect/check commands. | Docs-only. | `rg -n "still_cache.py" docs/agent-change-playbook.md && git diff --check` |
| `docs/agent-log.md` | This audit is a meaningful file-changing task, but the user asked not to edit the log yet. | Later entry: "Agent system audit created; behavior unchanged; known gap: current audit intentionally did not update log until allowed." | Docs-only. | `git diff --check` |

### P1 - Should Fix Soon

| File to update | Why | Suggested wording or section | Scope | Verification command |
| --- | --- | --- | --- | --- |
| `docs/RELEASE_CHECKLIST.md` | Release checklist is stale versus current practice. | Update compile command to include `app_i18n.py`, `still_cache.py`, Apple Lite scripts when relevant, and replace `v0.1.1` examples with "current `VERSION`". Add `gh release view` digest check. | Docs-only. | `rg -n "still_cache.py|app_i18n.py|gh release view|VERSION" docs/RELEASE_CHECKLIST.md && git diff --check` |
| `AGENTS.md` | Pages/App Store support routes and Apple Lite app icons are now operational surfaces. | Add `docs/support/index.html`, `docs/privacy/index.html`, and `apple-lite/WZRDVIDLite/App/Assets.xcassets/AppIcon.appiconset/` to high-risk/safety notes. | Docs-only. | `rg -n "docs/support|docs/privacy|AppIcon.appiconset" AGENTS.md && git diff --check` |
| `docs/agent-impact-map.md` | Apple Lite AppIcon and support/privacy are only partially represented. | In Apple Lite wrapper and static assets sections, name `Assets.xcassets/AppIcon.appiconset`, support/privacy routes, and privacy-manifest gap. | Docs-only. | `rg -n "AppIcon.appiconset|PrivacyInfo|docs/support|docs/privacy" docs/agent-impact-map.md && git diff --check` |
| `apple-lite/README.md` | Predates later AppIcon and AMPYX setup docs. | Add "For signing/App Store identity, defer to `docs/APPLE_LITE_APP_STORE_PREP.md`; AppIcon catalog now exists." | Docs-only. | `rg -n "APPLE_LITE_APP_STORE_PREP|AppIcon" apple-lite/README.md && git diff --check` |

### P2 - Useful Cleanup

| File to update | Why | Suggested wording or section | Scope | Verification command |
| --- | --- | --- | --- | --- |
| `docs/PERFORMANCE_NOTES.md` | Older frame-pipe sections can be misread as current. | Add top note: "Later dated sections supersede earlier transport notes; current default is raw RGB frame pipe with legacy PNG fallback/force option." | Docs-only. | `rg -n "supersede|current default" docs/PERFORMANCE_NOTES.md && git diff --check` |
| `docs/agent-log.md` | Long log is useful but hard to scan. | Add a short latest-state index at the top only if the user wants one; do not rewrite history. | Docs-only. | `git diff --check` |
| `docs/APPLE_LITE_APP_STORE_PREP.md` | Final contact/legal details remain placeholders. | Add an explicit "do not submit before AMPYX contact/legal review" checklist item if not already obvious enough. | Docs-only. | `rg -n "contact|legal review|do not submit" docs/APPLE_LITE_APP_STORE_PREP.md && git diff --check` |

### P3 - Optional

| File to update | Why | Suggested wording or section | Scope | Verification command |
| --- | --- | --- | --- | --- |
| New or existing docs index | Operational docs are numerous. | A small "Operational docs map" could route agents to release, Apple Lite, performance, localization, license, and Pages docs. | Docs-only. | `git diff --check` |
| Markdown tooling | No formal markdown linter exists. | Optional future `markdownlint` or simple heading/link script if docs churn increases. | Docs/tooling only. | `git diff --check` plus chosen tooling smoke |

## P0 remediation applied

Applied on 2026-05-23 as docs-only remediation: `AGENTS.md`, `docs/agent-impact-map.md`, and `docs/agent-change-playbook.md` now treat `still_cache.py` as a first-class still/HEIC proxy cache surface and include `still_cache.py`, `app_i18n.py`, and `docs/i18n.js` in the relevant check guidance. `docs/agent-log.md` records the remediation. An unrelated dirty `renderer.py` performance diff was reviewed, identified as intentional-looking WIP with companion docs, and left untouched.

## 10. Audit Conclusion

Was the work effective? Yes. The agent-docs system gave wzrdVID a practical repo map, change playbook, running log, and strict task-ending protocol. It materially improved traceability and scope control.

Will it continue to be effective? Yes, if refreshed. The system is robust enough, but its check commands and high-risk map need a small drift update.

Did we miss anything important? Yes: `still_cache.py` is the most important missed coverage. The release checklist and some compile commands also lag current repo structure. Apple Lite AppIcon/support/privacy surfaces should be more explicit in the main agent docs.

What is the next smallest safe improvement? Do a docs-only drift refresh that adds `still_cache.py`, `app_i18n.py`, `docs/i18n.js`, Apple Lite AppIcon assets, and support/privacy routes to the current agent docs and release checklist, then add a concise `docs/agent-log.md` entry for this audit if the user permits editing the log.
