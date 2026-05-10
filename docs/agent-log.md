# wzrdVID Agent Log

This file is the running memory for agent work on wzrdVID. It is intentionally practical and concise: future agents should use it to understand recent decisions, verification, and unresolved risks before touching the repo.

## Required Agent Behavior

Future agents must:

- Read `AGENTS.md` before every task.
- Read `docs/agent-log.md` before every task.
- Check the latest entries before making changes.
- Append a new entry after each task that changes files or makes an important decision.
- Never delete prior log entries unless explicitly instructed.
- Keep entries factual and concise.
- Include commands/checks run.
- Include unresolved risks or follow-ups.

Entries are reverse chronological: newest entry near the top.

## 2026-05-10 - Source-available use terms clarification

- Agent/task: Codex / narrow licensing and redistribution language pass before v0.2.0 Apple/Lite rollout work.
- Intent: Clarify public-facing rights language so the repo consistently says WZRD.VID is source-available, currently free for personal/noncommercial use, not permissive open source, and does not permit redistribution, app-store copies, hosted services, competing products, commercial use, or brand use without permission.
- Files changed this pass: `LICENSE`, `NOTICE.md`, `README.md`, `docs/LICENSE_FAQ.md`, `CONTRIBUTING.md`, `docs/lite/README.md`, `docs/agent-log.md`.
- Behavior changed: No. Documentation/legal-language only; app behavior, renderer behavior, Lite behavior, versioning, packaging, publishing, pushing, and tagging were not changed.
- Commands run: `git status --short --branch`; required repo docs reads; rights-language grep across README, license, notice, contributing docs, public docs, homepage, and Lite docs; `git diff --check`; final `git status --short --branch`.
- Checks passed: Targeted grep confirms source-available/noncommercial/commercial/redistribution/repackaging/hosted-service/branding/output/app-store language is present in the relevant public docs. Diff whitespace check passed.
- Checks failed: None.
- Decisions made: Kept the homepage rights note short to avoid turning the landing page into a legal wall; strengthened the canonical license/notice/README/FAQ/contributing/Lite docs instead.
- Known gaps: This was a practical clarity pass, not external legal review. Future App Store or commercial-license work should get proper legal review before submission or negotiation.
- Next recommended prompt: Run a v0.2.0 beta media pass with real long phone footage, then decide whether more desktop performance fixes are needed before Apple Lite app packaging.

## 2026-05-10 - v0.2.0 performance hardening and Apple Lite groundwork

- Agent/task: Codex / v0.2.0 performance audit, conservative optimization pass, long-media stress smoke, and Apple Lite app groundwork research.
- Intent: Treat v0.2.0 as performance hardening plus Apple/Lite rollout preparation by auditing long-media risks first, then making only low-risk measured changes and documenting Apple app options without publishing, pushing, tagging, packaging, or adding UI/effects features.
- Files changed this pass: `ffmpeg_utils.py`, `renderer.py`, `CHANGELOG.md`, `docs/PERFORMANCE_NOTES.md`, `docs/APPLE_LITE_APP_RESEARCH.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes, performance/logging only. ffprobe metadata is cached in-process by resolved path, mtime, and size; render logs now include stage timing; 30+ minute source video/audio inputs emit long-media warnings. Visual output, recipe schema, Lite behavior, deployment config, packaging, publishing, pushing, and tagging were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; performance audit greps/reads across `app.py`, `renderer.py`, `ffmpeg_utils.py`, README, changelog, and prior logs; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; synthetic media generation and render stress smokes with ffmpeg/ffprobe using the repo `.venv`; probe-cache smoke; official Apple Developer docs research for enrollment, App Review, privacy, App Store Connect, SDK submission requirements, and WKWebView local-file loading; `git diff --check`.
- Checks passed: Python and JavaScript syntax checks passed before stress. Probe cache smoke showed repeated duration/audio/video helper calls for the same file issued 1 ffprobe call total. Synthetic stress smokes passed for baseline short render, long source to 10s, long source to 90s, long source plus random/photo, source-audio only, long external audio only, long external audio with worky mode, external plus selected source audio, random plus source audio, random plus match-to-music rejection, and 5s/10s preview-like renders. Outputs were verified with ffprobe for duration/audio presence where applicable.
- Checks failed: The first stress attempt used system Python and failed because `cv2` was not installed there; reran with the repo `.venv` and passed.
- Decisions made: Added conservative runtime probe caching and observability instead of rewriting frame seeking, changing ffmpeg command structure, changing the worky profile, changing recipe schema, or touching Lite. Apple app work remains research-only until Developer/D-U-N-S setup is complete.
- Known gaps: Real 4K/60fps, variable-frame-rate, long-GOP, and difficult phone footage still need beta testing. OpenCV timestamp seeking remains the likely long-video/random-mode bottleneck. PNG frame staging can still grow with long/high-FPS outputs. Source-audio random assembly can still get expensive with many short segments. Apple Lite app implementation is intentionally not scaffolded yet.
- Next recommended prompt: Run a v0.2.0 beta media pass with real long phone footage, then start WZRD.VID Lite Apple app packaging only after no desktop performance blockers remain.

## 2026-05-10 - Final v0.1.9 rebuild and package validation

- Agent/task: Codex / final v0.1.9 rebuild/package after full desktop/site/Lite localization coverage.
- Intent: Re-run final validation, rebuild the packaged macOS app, package the release ZIP, verify version/size/checksum, and hand off for manual review without publishing, pushing, tagging, or creating a GitHub Release.
- Files changed this pass: `docs/agent-log.md`.
- Behavior changed: No. Validation and packaging only; no source UI, layout, copy, renderer/media, Lite render behavior, deployment config, version metadata, or release publication changes were made.
- Commands run: `git status --short --branch`; `git log --oneline -15`; required repo docs reads; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; Lite forbidden-network grep; `git diff --check`; local Pages server with `curl` checks for `/`, `/lite/`, and `/i18n.js`; source/offscreen desktop smoke for header placement and Spanish/Russian/Japanese/Arabic localization; `./build_app.sh`; `scripts/package_release.sh`; Info.plist version check; ZIP size check; SHA256 check; final `git status --short --branch`.
- Checks passed: Current HEAD includes the v0.1.9 release-prep commit, Phase A/B commits, README wording fix, header placement fix, desktop localization coverage commit, and site/Lite localization coverage commit. Python and JavaScript syntax checks passed. Lite forbidden-network grep returned no forbidden APIs. Static Pages root, Lite, and `i18n.js` loaded. Source/offscreen desktop smoke confirmed the header utility row is below the mint bus strip, language selector and update controls exist there, Download Update remains hidden/disabled initially, Spanish/Russian/Japanese/Arabic primary UI strings update, and max video length/random clip assembly controls exist. `dist/WZRD.VID.app` rebuilt and `WZRD.VID-macOS.zip` was packaged. Bundle plist reports `CFBundleShortVersionString` and `CFBundleVersion` as `0.1.9`.
- Checks failed: Initial offscreen smoke attempted to compare coordinates for the hidden Download Update button and failed because hidden Qt widgets report unreliable geometry; rerun validated its header parentage plus hidden/disabled state and passed. System Python lacks PySide6, so the desktop smoke used the repo `.venv`.
- Release artifact: `WZRD.VID-macOS.zip`, 76M, SHA256 `3e11371e25abe8620b698605b95ced490483ac2c558e70d9dee0c9857e4bde54`.
- Decisions made: Generated build outputs under `build/` and `dist/` and the release ZIP were kept as local release artifacts and were not committed.
- Known gaps: Manual review of the final packaged app and Lite remains before publication. Non-English translations remain draft/non-native-reviewed, and Arabic RTL support remains structural only.
- Next recommended prompt: Manually review the final packaged v0.1.9 app and Lite, then publish v0.1.9 on GitHub Releases with the final rebuilt ZIP and SHA256.

## 2026-05-10 - Full site and Lite localization key coverage

- Agent/task: Codex / normalize public site and WZRD.VID Lite localization coverage across all supported languages before v0.1.9 publication.
- Intent: Bring `docs/i18n.js` up to the same key coverage standard as the desktop app by filling the current English homepage/Lite/runtime key set for every supported site/Lite language while keeping translations draft.
- Files changed this pass: `docs/i18n.js`, `docs/I18N.md`, `docs/agent-log.md`.
- Behavior changed: No. Static UI localization resources and localization notes only; desktop behavior, renderer/media behavior, Lite render behavior, no-upload/no-network behavior, deployment config, versioning, packaging, pushing, tagging, and release publication were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; site/Lite i18n audits; site/Lite key coverage audit; placeholder consistency audit; `rg -n "\\{[a-zA-Z0-9_]+\\}|%s|%d" docs/i18n.js`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; full Python compile command; Lite forbidden-network grep; local Pages server with `curl` checks for `/`, `/lite/`, and `/i18n.js`; Arabic `dir=rtl` runtime smoke; Brave/Computer Use visual smoke for Spanish, Russian, Japanese, and Arabic site/Lite localization; `git diff --check`.
- Checks passed: Coverage audit reports `missing=0 extra=0` for English, Spanish, Brazilian Portuguese, French, German, Russian, Ukrainian, Japanese, Korean, Simplified Chinese, Traditional Chinese, Filipino/Tagalog, Hindi, and Arabic in `docs/i18n.js`. Placeholder audit passed. JavaScript and Python syntax checks passed. Lite forbidden-network grep returned no forbidden APIs. Local Pages root, Lite, and `i18n.js` loaded. Brave smoke confirmed homepage hero/download/Lite links localized in Spanish/Russian/Japanese, Lite controls and Random clip assembly localized in Japanese/Arabic, duration controls remained usable, and Arabic switched the document direction to RTL structurally.
- Checks failed: Playwright CLI browser smoke was not available because its default Chrome target was not installed at `/Applications/Google Chrome.app`; visual smoke used Brave through Computer Use instead.
- Decisions made: Added a static site/Lite coverage overlay in `docs/i18n.js` instead of changing the runtime fallback API, Lite rendering, localStorage behavior, or page markup. Brand and technical terms such as WZRD.VID, WZRD.VID Lite, worky.mode, wzrdgang, ANSI, MP4, FFmpeg, codec names, and creative preset names remain stable where appropriate.
- Known gaps: Non-English site/Lite strings now have complete key coverage but remain draft and need fluent/native review. Arabic RTL support remains structural only, not full RTL visual QA. Lite runtime rendering behavior was not changed or re-smoked beyond static/browser UI checks.
- Next recommended prompt: Rebuild/package v0.1.9 after full desktop/site/Lite localization coverage, then manually review the app and Lite before publishing.

## 2026-05-10 - Full desktop localization key coverage

- Agent/task: Codex / normalize desktop localization coverage across all supported desktop languages before v0.1.9 publication.
- Intent: Extend the prior Russian-only coverage pass so every supported desktop language has values for the current English `app_i18n.py` key set while keeping translations draft and preserving English fallback.
- Files changed this pass: `app_i18n.py`, `docs/I18N.md`, `docs/agent-log.md`.
- Behavior changed: No. Desktop UI resource strings and localization docs only; layout, renderer/media behavior, max-length/random behavior, Lite behavior, website behavior, versioning, packaging, pushing, tagging, and release publication were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -10`; required repo docs reads; desktop key coverage audit; per-language coverage audits; `python3 -m py_compile app_i18n.py`; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; offscreen source GUI localization smoke for Spanish, Russian, Japanese, and Arabic; `git diff --check`; `git status --short --branch`.
- Checks passed: Coverage audit reports `missing=0 extra=0` for English, Spanish, Brazilian Portuguese, French, German, Russian, Ukrainian, Japanese, Korean, Simplified Chinese, Traditional Chinese, Filipino/Tagalog, Hindi, and Arabic. Source GUI smoke confirmed Spanish/Russian/Japanese/Arabic table headers, source controls, preview empty state, timeline help/status, update controls/status, max-length/random controls, language switching, and header utility row placement.
- Checks failed: None.
- Decisions made: Added draft desktop key coverage in `app_i18n.py` instead of changing widget extraction, layout, render code, Lite, or site behavior. Brand and technical terms such as WZRD.VID, worky, worky.mode, ANSI, MP4, H.264, AAC, CRF, and Seed remain stable where appropriate.
- Known gaps: All supported desktop languages now have complete key coverage, but translations remain draft and need fluent/native review. Site/Lite non-English strings remain separately managed in `docs/i18n.js` and were not expanded in this pass.
- Next recommended prompt: Rebuild/package v0.1.9 after the full desktop localization coverage pass, then manually review the app and Lite before publishing.

## 2026-05-10 - Russian desktop localization coverage pass

- Agent/task: Codex / focused desktop localization coverage pass from manual Russian review before v0.1.9 publication.
- Intent: Reduce high-visibility English fallback in the desktop app after switching to Russian, especially table headers, timeline/source buttons, preview empty states, timeline help text, status labels, update controls, and common dialogs/tooltips.
- Files changed this pass: `app_i18n.py`, `docs/agent-log.md`.
- Behavior changed: No. UI strings only; renderer/media behavior, random/max-length behavior, Lite, website, versioning, packaging, pushing, tagging, and release publication were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; desktop i18n/widget audit greps; Russian missing-key audit; `python3 -m py_compile app_i18n.py`; offscreen source GUI Russian language smoke; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`; `git status --short --branch`.
- Checks passed: Russian now has desktop translations for all current `app_i18n.py` English keys, the offscreen GUI smoke confirmed Russian table headers, source controls, timeline help, preview empty state, timeline status, and update controls update without restart, Python and JavaScript syntax checks passed, and diff whitespace check passed.
- Checks failed: None.
- Decisions made: Added a focused Russian high-visibility draft pack in `app_i18n.py` instead of changing widget extraction or render code. Existing stable English internals such as preset/effect option names, raw technical errors, and media filenames remain outside this pass unless already represented by UI keys.
- Known gaps: Russian strings remain draft and need fluent review. Other non-English languages still have partial desktop coverage and English fallback for many less-reviewed strings.
- Next recommended prompt: Review the v0.1.9 desktop app manually in Russian, then rebuild/package if this localization coverage pass is accepted.

## 2026-05-10 - Header utility row placement correction

- Agent/task: Codex / small desktop header layout correction before v0.1.9 publication.
- Intent: Move the existing update/language utility row so it sits directly below the mint-green `worky.mode / wzrdgang` bus strip instead of competing with the strip higher in the header.
- Files changed this pass: `app.py`, `docs/agent-log.md`.
- Behavior changed: No. Layout only; update behavior, language persistence, localization, renderer/media/random/max-length behavior, Lite, website, versioning, and packaging were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; header audit grep; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`; offscreen source GUI smoke; normal source GUI visual smoke with Computer Use.
- Checks passed: Python and JavaScript syntax checks passed, diff whitespace check passed, offscreen source GUI confirmed the visible language/update controls are below the bus strip, the hidden download update button stayed parented in the header and hidden/disabled at initial state, Spanish language switching still updated primary UI, no duplicate update/language controls were found in the Output panel, max length/random controls remained present, and normal GUI visual smoke showed the row under the mint bus strip.
- Checks failed: Initial offscreen geometry check could not position the hidden `download_update_button` because it starts hidden by design; rerun validated its parentage and preserved hidden/disabled state instead.
- Decisions made: Moved the existing row in `_build_header` without new styling or `theme.py` changes.
- Known gaps: Packaged app was not rebuilt after this source layout correction; rebuild/package remains a manual-review decision before publication.
- Next recommended prompt: Review the v0.1.9 app and Lite manually, then rebuild/package if this header correction changed the packaged app.

## 2026-05-10 - Max length and random clip assembly

- Agent/task: Codex / Phase B desktop max video length plus desktop and Lite random clip assembly before v0.1.9 publication.
- Intent: Add release-safe duration capping and random clip assembly while preserving existing desktop/Lite behavior when new controls are off, avoiding advanced per-clip include-section editing, and keeping Lite browser-only/no-upload.
- Files changed this pass: `app.py`, `app_i18n.py`, `renderer.py`, `docs/lite/index.html`, `docs/lite/app.js`, `docs/lite/styles.css`, `docs/i18n.js`, `README.md`, `CHANGELOG.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Desktop can cap final render duration, can build deterministic random source segments when max length is set, saves/loads schema version 4 recipe fields, and rejects random+match-to-music before render. Lite now exposes a localized random clip assembly checkbox using its existing 15/30/60-second duration choices.
- Commands run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; Phase B audit grep; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; Lite forbidden-network grep; offscreen source GUI/recipe smoke; synthetic ffmpeg render smokes with ffprobe; local Pages server with `curl` checks for `/`, `/lite/`, and `i18n.js`; Lite checkbox static check; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; plist, ZIP size, and SHA256 verification.
- Checks passed: Python and JavaScript syntax checks passed, Lite network grep returned no forbidden APIs, source GUI opened with Phase A header controls intact, max/random controls existed, Spanish language switching still updated primary UI, old recipe JSON loaded blank/false for new fields, schema 4 recipe JSON saved/reloaded both fields, default render worked, max-only render capped output, random video+photo render produced a valid capped MP4, random source-audio render produced a valid MP4 with audio, random+match-to-music rejected before render, local Pages root/Lite/i18n loaded, the release ZIP rebuilt, and bundle plist reports 0.1.9.
- Checks failed: Browser automation for a live Lite render was not run; validation used JS syntax, static local serving, checkbox presence, and source render smokes.
- Decisions made: Lite's random checkbox defaults on so the existing random browser timeline behavior remains the default. Desktop source audio is attempted through the existing source-audio builder for randomized segments and falls back with a clear log if that path fails.
- Known gaps: Advanced per-clip include-section selection remains future work. Lite random mode is non-deterministic and remains browser/MediaRecorder dependent. Non-English strings are still draft and need fluent review.
- Release artifact: `WZRD.VID-macOS.zip`, 76M, SHA256 `1bd1799544bbcb6c686bae45caf6a3080ead540e1d4f028c74096eaaf2ba16d0`.
- Next recommended prompt: Review the v0.1.9 app and Lite manually, then publish the updated v0.1.9 release with the rebuilt ZIP and SHA256.

## 2026-05-10 - Header update/language relocation

- Agent/task: Codex / Phase A desktop header UI relocation before v0.1.9 publication.
- Intent: Move the existing update status/check/download controls and UI language selector into one compact header utility row without changing update behavior, language persistence, renderer/media behavior, website/Lite behavior, or release publication state.
- Files changed this pass: `app.py`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes, desktop UI placement only. The update cluster and language selector now live in the top header, and the old Output-tab rows were removed to avoid duplicate controls.
- Commands run: `git status --short --branch`; `git log --oneline -5`; required repo docs reads; header/update/language audit grep; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; offscreen source GUI smoke; `git diff --check`.
- Checks passed: Python and JavaScript syntax checks passed, diff whitespace check passed, offscreen source GUI opened, the update status/check/download controls and language selector are parented under the header, the old Output panel no longer contains those widgets, Spanish language switching still updated primary UI, and `download_update_button` remained hidden/disabled at initial state.
- Checks failed: None.
- Decisions made: Reused the existing widgets/signals/state rules instead of creating duplicate controls. No `theme.py` or localization resource change was needed for this relocation.
- Known gaps: Visual crowding should still get a normal manual GUI glance before release publication.
- Next recommended prompt: Implement desktop max length plus desktop and Lite random clip assembly as the next scoped v0.1.9 feature pass.

## 2026-05-10 - v0.1.9 localization release prep

- Agent/task: Codex / version, commit, package, and prepare the localization-focused v0.1.9 release.
- Intent: Verify the homepage notice removal and second-pass localization polish, bump app metadata to v0.1.9, build the macOS app, package the release ZIP, and prepare the local commit without changing renderer/media behavior or deployment config.
- Files changed this pass: `VERSION`, `app.py`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes, UI/site/localization only. Version metadata now reports v0.1.9, and the release notes document the localization polish and homepage notice removal. Renderer, ffmpeg, media processing, `docs/CNAME`, release scripts, and generated build outputs were not changed.
- Commands run: `git status --short --branch`; required repo docs reads; release docs/version inspection; homepage notice stale-phrase grep; Lite forbidden-network grep; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; local Pages server with `curl` checks for `/`, `/lite/`, and `i18n.js`; desktop offscreen Spanish language smoke; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; plist/version checks; package size and SHA256 checks; packaged app GUI launch smoke.
- Checks passed: Homepage stale notice grep is clean, Python and JavaScript syntax checks passed, no forbidden Lite network APIs were found, local Pages root/Lite/i18n loaded, desktop language switching updated primary Spanish UI without restart, `dist/WZRD.VID.app` built, `WZRD.VID-macOS.zip` packaged, bundle version reads 0.1.9, SHA256 is `01808a7dc06ee8963e90a254bbab676a6b6434320c9c0ce78aafa5c26a16deae`, and normal packaged GUI launch showed `WZRD.VID v0.1.9`.
- Checks failed: Packaged offscreen launch smoke failed because the bundled Qt app exposes the Cocoa platform plugin only; normal GUI packaged launch passed after that.
- Decisions made: Kept the release as a UI/localization/site release. Did not rebuild translation architecture, edit renderer/media code, touch `docs/CNAME`, or publish the GitHub Release.
- Known gaps: Non-English strings remain draft/partial and need fluent review. Arabic RTL support remains structural only. Intel/universal packaged builds remain a future packaging task. GitHub release publication remains deferred.
- Next recommended prompt: Publish v0.1.9 on GitHub Releases with the prepared ZIP and SHA256 after reviewing the release notes.

## 2026-05-10 - Homepage notice removal and localization polish

- Agent/task: Codex / scoped homepage notice removal plus second-pass UI localization support.
- Intent: Remove the top homepage Mac install notice block and tighten high-visibility desktop/site/Lite localization without changing renderer, media handling, uploads, deployment config, versioning, packaging, or release state.
- Files changed this pass: `README.md`, `app.py`, `app_i18n.py`, `docs/index.html`, `docs/styles.css`, `docs/i18n.js`, `docs/lite/index.html`, `docs/I18N.md`, `docs/agent-log.md`.
- Behavior changed: Yes, UI-only. The homepage top notice block is gone. Desktop localization now covers more common tooltips, table type labels, user-facing warning/dialog copy, the session log label, and header signal text. Site/Lite ARIA labels and remaining download-note translations were tightened.
- Commands run: `git status --short --branch`; required repo docs reads; homepage notice grep before/after; required desktop and site/Lite visible-string audits; localization key audit; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; Lite forbidden-network grep; local Pages server with `curl` checks for `/`, `/lite/`, and `i18n.js`; desktop offscreen Spanish language smoke; Brave/Computer Use visual smoke for local site and Lite; `git diff --check`.
- Checks passed: Homepage notice/stale-phrase grep is clean, Python and JavaScript syntax checks passed, no forbidden Lite network APIs were found, local Pages root and Lite loaded, desktop Spanish language switching updated primary controls/dialog strings without restart, and local site/Lite rendered in Spanish with no obvious first-viewport regression.
- Checks failed: Browser plugin runtime tools were not exposed in this session; rendered smoke used Brave through Computer Use instead.
- Decisions made: Preset/effect names, codec names, preset descriptions, raw ffmpeg/probe/render errors, and low-level render logs remain stable English internals. The README sentence was reworded only to remove the stale phrase caught by the required grep.
- Known gaps: Non-English strings remain draft/partial and need fluent review. Arabic RTL support remains structural only. Some combo option labels and preset descriptions still require restart-safe, schema-safe localization work before they should be translated.
- Next recommended prompt: Version, commit, package, and prepare the next wzrdVID release after verifying the homepage notice removal and second-pass localization polish.

## 2026-05-10 - UI localization groundwork

- Agent/task: Codex / desktop, WZRD.VID Lite, and public-site UI localization/readability pass.
- Intent: Make the desktop app, Lite, and wzrdvid.com usable worldwide at the UI/readability layer only while preserving local-first/no-upload behavior, static GitHub Pages deployment, and renderer/ffmpeg behavior.
- Files changed: `app.py`, `app_i18n.py`, `theme.py`, `docs/index.html`, `docs/styles.css`, `docs/i18n.js`, `docs/I18N.md`, `docs/lite/index.html`, `docs/lite/app.js`, `docs/lite/styles.css`, `AGENTS.md`, `docs/agent-impact-map.md`, `docs/agent-change-playbook.md`, `docs/agent-log.md`.
- Behavior changed: Yes, UI-only. Desktop, Lite, and the public site now expose language selectors, persist the selected UI language locally, fall back to English, and update major visible interface strings without changing media processing, project JSON beyond the safe app setting, deployment config, or `docs/CNAME`.
- Commands run: `git status --short --branch`; required repo docs reads; targeted `rg`/`sed`; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; desktop offscreen Qt language smoke; local static server with `curl` checks for `/` and `/lite/`; Lite forbidden network API grep; visible-string audit grep; Brave/Computer Use visual smoke for site and Lite language switching; `git diff --check`.
- Checks passed: Python syntax, site/Lite JavaScript syntax, desktop language switching smoke, local Pages root and Lite loads, no forbidden Lite `fetch`/`XMLHttpRequest`/`sendBeacon`/`WebSocket` matches, visual smoke with Spanish selected, and diff whitespace check passed.
- Checks failed: Browser plugin Node REPL control surface was not available in this session, so the rendered-page smoke used Brave through Computer Use instead.
- Decisions made: Used lightweight Python/JavaScript dictionary resources with stable keys instead of Qt `.ts/.qm` files or a static-site build step. Translations are marked draft and centralized for later review. Arabic gets structural `dir` support, not a claim of complete RTL QA.
- Known gaps: Non-English translations are draft/partial and need native review. Some desktop lower-level engine option names, detailed tooltips, raw ffmpeg/probe/render errors, branding strings, and support/log internals remain English. No content/media/subtitle translation was added.
- Next recommended prompt: Review the draft translation resources for the target languages and tighten the remaining high-visibility desktop strings without touching renderer behavior.

## 2026-05-09 - Website download wording cleanup

- Agent/task: Codex / front-page v0.1.8 website copy cleanup.
- Intent: Remove defensive Source ZIP warning language from the wzrdvid.com primary CTA area while keeping detailed download warnings in README/install/help docs.
- Files changed: `docs/index.html`, `docs/agent-log.md`.
- Behavior changed: No. Website copy only; app code, version metadata, and release ZIP were not changed.
- Commands run: `git status --short --branch`; targeted `rg`/`sed`; local Pages server and `curl`; `git diff --check`.
- Checks passed: Front page no longer contains the removed Source ZIP warning, README/install/help docs still retain Source ZIP vs packaged app guidance, local `/` and `/lite/` Pages checks passed, and diff check passed.
- Checks failed: None.
- Decisions made: Homepage used softer normal-user wording for packaged Mac app guidance and Intel Mac source-run guidance.
- Known gaps: v0.1.8 GitHub release remains unpublished. App ZIP was not rebuilt because the change is website copy only.
- Next recommended prompt: Publish v0.1.8 with the existing packaged app ZIP and unchanged SHA256 after reviewing the release command.

## 2026-05-09 - v0.1.8 maintenance prep

- Agent/task: Codex / tightly scoped v0.1.8 maintenance release prep.
- Intent: Clarify current packaged Mac ZIP support boundaries for Apple Silicon vs Intel Macs, improve install/update troubleshooting, verify PUBLIC ACCESS stability after v0.1.7, bump/package v0.1.8, and prepare but not publish the release.
- Files changed: `VERSION`, `app.py`, `README.md`, `docs/index.html`, `docs/INSTALL_MAC.md`, `docs/RELEASE_DOWNLOAD_HELP.md`, `docs/CROSS_PLATFORM.md`, `docs/RELEASE_CHECKLIST.md`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: No renderer/workflow behavior changed. App-visible version metadata changed to v0.1.8, and public install/update documentation now states that the packaged Mac ZIP is Apple Silicon-focused while Intel Mac users should run from source for now.
- Commands run: `git status --short --branch`; targeted `rg`/`sed`; `node --check docs/lite/app.js`; forbidden Lite network API grep; `python3 -m py_compile`; synthetic ffmpeg media generation; desktop render smokes for PUBLIC ACCESS 0%/50%/100% ANSI and 5s/10s paths with worky music mode; local Pages server and `curl`; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; plist/version/size/checksum checks; packaged app launch smoke with Output tab/update checker inspection.
- Checks passed: Python and Lite syntax checks, no forbidden Lite network APIs, static Pages checks, desktop PUBLIC ACCESS render smokes, H.264/yuv420p output verification, worky music mode AAC output verification, diff check, macOS app build, release ZIP package, plist version 0.1.8, packaged app launch, and non-blocking update checker smoke passed.
- Checks failed: System Python render smoke failed before using the project virtualenv because `cv2` was not installed globally; rerunning through `.venv/bin/python` passed.
- Decisions made: No PUBLIC ACCESS code changes were needed. The maintenance release keeps universal/Intel packaging as a future packaging task and directs Intel users to source runs for now.
- Known gaps: GitHub release publication remains intentionally deferred. Intel/universal packaged builds are not created yet.
- Next recommended prompt: Publish v0.1.8 with the generated `WZRD.VID-macOS.zip` and SHA256 after reviewing the final release command.

## 2026-05-09 - v0.1.7 PUBLIC ACCESS renderer prep

- Agent/task: Codex / v0.1.7 real PUBLIC ACCESS renderer and Lite parity release prep.
- Intent: Turn PUBLIC ACCESS from preset groundwork into a visible renderer treatment, keep ANSI coverage semantics intact, add Lite PUBLIC ACCESS parity and browser-dependent format copy, bump/package v0.1.7, and prepare but not publish the release.
- Files changed: `VERSION`, `app.py`, `renderer.py`, `presets.py`, `README.md`, `docs/index.html`, `docs/lite/index.html`, `docs/lite/app.js`, `docs/lite/README.md`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes. PUBLIC ACCESS now applies camcorder-dub/VHS source treatment before ANSI coverage decisions, so 0%, mixed, and 100% ANSI outputs all share the analog broadcast source texture. Lite now includes a matching PUBLIC ACCESS preset and broader extension acceptance with browser-limited decode messaging.
- Commands run: `git status --short --branch`; targeted `sed`/`rg`; `python3 -m py_compile`; `node --check docs/lite/app.js`; forbidden Lite network API grep; local Pages server and `curl`; Brave/Computer Use Lite load smoke; synthetic ffmpeg media generation; desktop render smokes for PUBLIC ACCESS 0%/50%/100% ANSI, 5s/10s paths, worky music mode, and HEIC; offscreen recipe/reset smoke; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; plist/version/size/checksum checks; packaged app launch smoke.
- Checks passed: Python and Lite syntax checks, no forbidden Lite network APIs, static Pages checks, desktop PUBLIC ACCESS render smokes, H.264/yuv420p output verification, AAC worky audio output verification, HEIC render smoke on this machine, recipe/reset smoke, macOS app build, release ZIP package, plist version 0.1.7, and packaged app launch smoke passed.
- Checks failed: Playwright CLI browser smoke could not run because Google Chrome is not installed at the expected path; Brave/Computer Use was used for the Lite page load smoke instead.
- Decisions made: PUBLIC ACCESS uses the existing preset/effect-intensity surface instead of adding a new panel. The treatment is a pre-ANSI source layer, not an ANSI-off mode.
- Known gaps: GitHub release publication remains intentionally deferred. Lite HEIC/HEIF remains browser-limited even though desktop can use ffmpeg-backed decoding.
- Next recommended prompt: Publish v0.1.7 with the generated `WZRD.VID-macOS.zip` and SHA256 after reviewing the final release command.

## 2026-05-09 - v0.1.6 media expansion prep

- Agent/task: Codex / focused v0.1.6 media expansion and broadcast artifact release prep.
- Intent: Add 10-second preview support, expand accepted media formats, add HEIC/HEIF motion-loop handling, add worky's music mode, add PUBLIC ACCESS preset groundwork, bump/package v0.1.6, and prepare but not publish the release.
- Files changed: `VERSION`, `app.py`, `renderer.py`, `ffmpeg_utils.py`, `presets.py`, `README.md`, `docs/index.html`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Desktop preview duration can be 5s or 10s, more media extensions are accepted, HEIC/HEIF stills can decode through ffmpeg fallback with restrained automatic motion, external audio can use the worky music profile, and PUBLIC ACCESS appears as a style preset while preserving ANSI coverage controls.
- Commands run: `git status --short --branch`; targeted `sed`/`rg`; `python3 -m py_compile`; `node --check docs/lite/app.js`; local Pages `curl` checks; offscreen Qt helper smoke for preview options/extensions/recipe defaults; tiny render smokes for 5s/10s preview settings, HEIC motion, and worky music mode; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; plist/version/size/checksum checks; packaged app launch smoke.
- Checks passed: Python and Lite syntax checks, static Pages checks, recipe compatibility smoke, HEIC render smoke, direct ffprobe worky music mode output check, macOS app build, release ZIP package, plist version 0.1.6, and packaged app launch smoke passed.
- Checks failed: None.
- Decisions made: PUBLIC ACCESS was added as stable preset groundwork, not a separate renderer rewrite. Worky's music mode processes external audio only and leaves source-video audio routing intact.
- Known gaps: GitHub release publication remains intentionally deferred. HEIC support depends on available ffmpeg decoding on the user's machine.
- Next recommended prompt: Publish v0.1.6 with the generated `WZRD.VID-macOS.zip` and SHA256 after reviewing the final release command.

## 2026-05-09 - v0.1.5 packaged update checker fix

- Agent/task: Codex / release-critical desktop update checker hardening before v0.1.5.
- Intent: Fix packaged-app update-check dead ends, add GitHub release-page fallback/manual check behavior, bump/package v0.1.5, and prepare but not publish the release.
- Files changed: `VERSION`, `app.py`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Update checks now use explicit GitHub headers, short timeouts, API plus release-page fallback, clearer diagnostics, and a manual release-page button when automatic checking fails.
- Commands run: `git status --short --branch`; targeted `sed`/`rg`; direct source update fetch test; helper semver/latest-release assertions; `python3 -m py_compile`; packaged app launch/smoke checks; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; bundle version/size/checksum checks.
- Checks passed: Source latest-release fetch, semver helper checks, Python/Lite syntax checks, packaged v0.1.5 update-check smoke, packaged v0.1.2 release-app update check showing v0.1.4 available, diff check, macOS app build, release ZIP package, plist version 0.1.5, and checksum checks passed.
- Checks failed: Exact old packaged exception was not captured because the v0.1.2 package did not reproduce the unavailable state during final smoke.
- Decisions made: No Sparkle, auto-download, dependencies, UI redesign, or release publication were added; failures now leave users with a manual GitHub Releases path.
- Known gaps: v0.1.5 GitHub Release publication remains intentionally deferred.
- Next recommended prompt: Publish v0.1.5 with the generated `WZRD.VID-macOS.zip` after reviewing the final checksum.

## 2026-05-09 - v0.1.4 workflow polish prep

- Agent/task: Codex / Phase 3B Desktop Workflow Tightening - Endings, Transitions, Drag/Drop Reliability.
- Intent: Keep Fade Out as the ending default, set a less abrupt default transition, improve drag/drop rejection logging, bump/package v0.1.4, and prepare but not publish the release.
- Files changed: `VERSION`, `app.py`, `renderer.py`, `README.md`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes. New projects/default reset now use CRT Flash transitions with Fade Out endings, invalid local drops are accepted into handlers so they can be logged/warned, and v0.1.4 metadata is packaged.
- Commands run: `git status --short --branch`; targeted `rg`; `python3 -m py_compile app.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; helper smoke with media paths containing spaces/apostrophes; tiny render smoke; source GUI launch/Output tab inspection; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; bundle version/size/checksum checks.
- Checks passed: Py compile, diff check, helper drag/drop/audio/recipe/reset/COPY REPORT smoke, tiny H.264/yuv420p render with CRT Flash/Fade Out logs, source GUI launch, macOS app build, release ZIP package, and plist version 0.1.4 passed.
- Checks failed: None.
- Decisions made: VHS Collapse was not made default; Fade Out was already stable and kept. Existing saved recipes keep their saved transition/ending values.
- Known gaps: GitHub release publication was intentionally deferred.
- Next recommended prompt: Publish v0.1.4 using the generated `WZRD.VID-macOS.zip` and SHA256, then have a normal user smoke-test the packaged app.

## 2026-05-09 - Recipe workflow and reset polish

- Agent/task: Codex / Phase 3A Desktop Workflow Tightening - Recipes + Reset Polish.
- Intent: Rename visible project preset controls to recipe import/export, preserve JSON compatibility, and make reset confirmation/state cleanup clearer.
- Files changed: `app.py`, `README.md`, `docs/agent-impact-map.md`, `docs/agent-change-playbook.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Desktop copy now uses recipe language, reset no longer treats log text alone as resettable project state, reset clears the last render error, and recipe import/export keeps legacy project preset JSON compatibility.
- Commands run: `git status --short --branch`; targeted `rg`; programmatic Qt offscreen recipe/import/reset/COPY REPORT smoke; `python3 -m py_compile app.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py`; `git diff --check`.
- Checks passed: Py compile, diff whitespace check, recipe JSON round-trip, old `video_path`-only project JSON import, reset non-deletion check, and COPY REPORT after reset passed.
- Checks failed: None.
- Decisions made: Internal function names and JSON shape were left intact to reduce compatibility risk.
- Known gaps: No full render smoke was run because the changed path is recipe/reset UI state, not rendering.
- Next recommended prompt: Run a short manual GUI pass: export a real recipe, import it, reset project, then decide whether to package a v0.1.4 maintenance release.

## 2026-05-09 - Download/install docs polish

- Agent/task: Codex / focused Download / Install / Update flow polish after v0.1.3.
- Intent: Make the packaged Mac app release asset path obvious, move source-run instructions secondary, add a short Mac install guide, and smoke-test the published v0.1.3 ZIP from GitHub.
- Files changed: `README.md`, `docs/index.html`, `docs/styles.css`, `docs/RELEASE_DOWNLOAD_HELP.md`, `docs/INSTALL_MAC.md`, `docs/agent-log.md`.
- Behavior changed: No app behavior changed. Public docs/site copy changed.
- Commands run: v0.1.3 release download/unzip/version checks; latest-release update-check smoke; `git diff --check`; targeted `rg`; local static server with `curl` checks for `/`, `/lite/`, `/INSTALL_MAC.md`, and `/RELEASE_DOWNLOAD_HELP.md`.
- Checks passed: Release ZIP exists and unzips from GitHub; bundled app version is 0.1.3; docs/site static checks passed.
- Checks failed: None.
- Decisions made: No desktop feature work, licensing changes, UI redesign, or release publication was included.
- Known gaps: Normal GUI launch from the downloaded app was not run because this pass focused on docs and prior clean-install GUI testing was constrained by an active local WZRD.VID session.
- Next recommended prompt: Let one normal Mac user follow the updated download/install instructions from wzrdvid.com and report any remaining friction.

## 2026-05-09 - v0.1.3 bugfix prep

- Agent/task: Codex / Phase 2 v0.1.3 bugfix-only polish implementation.
- Intent: Validate the published v0.1.2 ZIP, add a sanitized copy-report helper, bump version metadata, rebuild/package v0.1.3, and prepare but not publish the release.
- Files changed: `VERSION`, `app.py`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes. The desktop app can copy a sanitized support report from the Output log area.
- Commands run: v0.1.2 release download/unzip checks; bundle metadata checks; ffmpeg/ffprobe checks; copy-report offscreen smoke; tiny render smoke; update checker worker smoke; `python3 -m py_compile`; `node --check`; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; checksum/version/size checks.
- Checks passed: v0.1.3 compile/static checks, copy-report sanitization smoke, tiny H.264/yuv420p + AAC render smoke, update checker worker smoke, build, package, plist version, and checksum checks passed.
- Checks failed: Direct isolated-HOME launch of the v0.1.2 bundle exited with macOS pasteboard service errors; normal GUI inspection raised an existing running WZRD.VID session instead of a clean first-run instance.
- Decisions made: No creative features, UI redesign, Sparkle, signing, or notarization work was included.
- Known gaps: Clean install GUI smoke is partially constrained by an existing active WZRD.VID render/session on the machine; the v0.1.2 release ZIP downloaded/unzipped and bundle metadata verified, but add-media/preview/render was covered through source-level smoke instead of the downloaded GUI.
- Next recommended prompt: Publish the prepared v0.1.3 GitHub Release with the generated ZIP and SHA256.

## 2026-05-09 - v0.1.2 stabilization prep

- Agent/task: Codex / Phase 1 v0.1.2 stabilization implementation.
- Intent: Verify Lite duration/ANSI behavior, add desktop GitHub Releases update checker, bump version metadata, package release ZIP, and prepare but not publish v0.1.2.
- Files changed: `VERSION`, `app.py`, `build_app.sh`, `CHANGELOG.md`, `docs/index.html`, `docs/agent-change-playbook.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Desktop app now checks GitHub Releases for updates without blocking or auto-downloading.
- Commands run: `rg` stale-copy/no-upload checks; `node --check`; `python3 -m py_compile`; local Pages `curl` checks; `git diff --check`; `./build_app.sh`; `scripts/package_release.sh`; Info.plist/version/size/checksum checks.
- Checks passed: v0.1.2 verification/package checks passed during implementation.
- Checks failed: None.
- Decisions made: Lite implementation was already correct and left unchanged; release ZIP was created locally but not committed; GitHub release publication was intentionally deferred.
- Known gaps: No Sparkle, signing, notarization, or Apple pipeline work was included in this phase.
- Next recommended prompt: Publish the prepared v0.1.2 GitHub Release with the generated ZIP and SHA256.

## 2026-05-09 - Change playbook created

- Agent/task: Codex / Prompt 5 in the agent documentation system plan.
- Intent: Create a practical change-type checklist so future agents do not fly blind.
- Files changed: `AGENTS.md`, `docs/agent-change-playbook.md`, `docs/agent-log.md`.
- Behavior changed: No.
- Commands run: `git status --short --branch`; repository inspection commands; `git diff --check`; targeted `rg` section checks.
- Checks passed: Docs-only checks passed for the committed documentation set.
- Checks failed: None.
- Decisions made: The playbook is mandatory before code changes; broad refactors require explicit user direction and map/log updates.
- Known gaps: No formal markdown linter is configured in the repo.
- Next recommended prompt: Use the Future task starter prompt from the user-provided plan for the next wzrdVID task.

## 2026-05-09 - Impact map items tightened

- Agent/task: Codex / Prompt 4 in the agent documentation system plan.
- Intent: Resolve map ambiguity by searching for uppercase `Unknown` entries and replacing them with repo evidence or absent-feature statements.
- Files changed: `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: No.
- Commands run: `rg -n "Unknown" docs/agent-impact-map.md`; additional targeted file inspections.
- Checks passed: No uppercase `Unknown` entries remain in `docs/agent-impact-map.md`.
- Checks failed: None.
- Decisions made: GitHub Actions, formal tests, backend persistence, and packaged Windows/Linux builds are documented as not present in the repo.
- Known gaps: Runtime behavior was not re-tested because this was a docs-only mapping task.
- Next recommended prompt: Create `docs/agent-change-playbook.md`.

## 2026-05-09 - Repo impact map created

- Agent/task: Codex / Prompt 3 in the agent documentation system plan.
- Intent: Create a static repo map covering desktop app modules, Lite/browser site, GitHub Pages deployment, build/package scripts, assets, and verification requirements.
- Files changed: `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: No.
- Commands run: `find`, `rg`, `sed`, `ls`, targeted reads of Python, shell, docs, site, and asset files.
- Checks passed: Map is grounded in current repo files and records absent systems explicitly.
- Checks failed: None.
- Decisions made: The impact map treats desktop rendering/audio files, Pages/Lite files, packaging scripts, and generated assets as high-risk areas.
- Known gaps: No app runtime, PyInstaller build, or browser render smoke was run because the task was docs-only.
- Next recommended prompt: Tighten remaining map ambiguity.

## 2026-05-09 - Agent project log created

- Agent/task: Codex / Prompt 2 in the agent documentation system plan.
- Intent: Create persistent agent memory and require future agents to read and append it.
- Files changed: `docs/agent-log.md`, `AGENTS.md`.
- Behavior changed: No.
- Commands run: `sed -n` reads of `AGENTS.md`; docs-only repo inspection.
- Checks passed: `docs/agent-log.md` includes required behavior, baseline entry, entry template, and log rules.
- Checks failed: None.
- Decisions made: Agent log entries stay reverse chronological and factual; prior entries must not be deleted without explicit instruction.
- Known gaps: No historical pre-log tasks were reconstructed beyond the current agent-docs baseline.
- Next recommended prompt: Create `docs/agent-impact-map.md`.

## 2026-05-09 - Agent guide created

- Agent/task: Codex / Prompt 1 in the agent documentation system plan.
- Intent: Create a repo-specific root guide so future coding agents start with repo context, rules, commands, and verification expectations.
- Files changed: `AGENTS.md`.
- Behavior changed: No.
- Commands run: `git status --short --branch`; reads of README, docs, source files, scripts, requirements, assets, and ignored output conventions.
- Checks passed: `AGENTS.md` includes project summary, tech stack, repo structure, operating rules, safety rules, commands, validation matrix, and required task ending format.
- Checks failed: None.
- Decisions made: Future agents must preserve public branding/source-available licensing language, avoid generated output churn, and keep changes scoped.
- Known gaps: No `.github` workflows were found in the current checkout; no formal test runner/lint config was found.
- Next recommended prompt: Create `docs/agent-log.md`.

## Entry Template

```markdown
## YYYY-MM-DD - Short title

- Agent/task:
- Intent:
- Files changed:
- Behavior changed:
- Commands run:
- Checks passed:
- Checks failed:
- Decisions made:
- Known gaps:
- Next recommended prompt:
```

## Rules for Log Entries

- Use reverse chronological order, newest entry near the top.
- Do not include secrets.
- Do not paste huge logs.
- Link or name relevant files.
- Mention if deployment config, GitHub Pages, or build output was touched.
- Mention if generated files were intentionally avoided.
- Keep entries factual and concise.
