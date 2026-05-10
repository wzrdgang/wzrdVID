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
