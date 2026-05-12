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

## 2026-05-12 - Experimental frame-pipe launch gate audit

- Agent/task: Codex / audit why `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1 open dist/WZRD.VID.app` did not activate the experimental frame-pipe renderer in a packaged macOS render.
- Intent: Preserve default PNG-staging correctness and long-render behavior, keep pipe mode explicitly opt-in, avoid Lite/Apple Lite/site/versioning/package/publish/tag changes, and stage only relevant hunks despite unrelated Apple Lite worktree edits.
- Finding: The renderer had no preset/audio/render-configuration disable path for pipe mode. The likely cause is macOS `open`: the environment variable is applied to the `open` process, while the app bundle is launched through LaunchServices and should not be assumed to inherit that shell environment.
- Files changed this pass: `app.py`, `app_i18n.py`, `renderer.py`, `CHANGELOG.md`, `docs/PERFORMANCE_NOTES.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes, opt-in/developer-only. Default renders still use PNG staging. Render startup now logs whether the experimental frame pipe is enabled, disabled, unavailable, or falling back, with the reason. A localized desktop Output-area `Experimental frame pipe` checkbox persists in local app settings and enables the same pipe path without relying on shell env propagation. Recipe JSON is unchanged.
- Commands/tools run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; frame-pipe gate/code grep; partial and full Python compile checks; desktop localization key-coverage audit; synthetic source generation under `/tmp/wzrdvid-frame-pipe-gate`; disabled render smoke confirming PNG `frame_%06d.png` staging; enabled developer-setting render smoke confirming raw `rgb24` pipe and no PNG sequence command; direct source-run env render smoke confirming `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1` works when the render process receives it; ffprobe codec/pix_fmt/duration checks; offscreen GUI setting/persistence smoke; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`.
- Checks passed: Disabled mode produced valid H.264/yuv420p MP4 at 2.000s and logged PNG staging. Developer-setting enabled mode produced valid H.264/yuv420p MP4 at 2.000s and logged raw frame piping with no `frame_%06d.png`. Direct env source-run mode produced valid H.264/yuv420p MP4 at 1.000s and logged `WZRDVID_EXPERIMENTAL_FRAME_PIPE='1'`. Python compile, JS syntax, localization coverage, GUI setting smoke, and whitespace checks passed.
- Known gaps: The already-built packaged app does not include this new logging/toggle until rebuilt. This pass did not rerun the full real long render.
- Next recommended prompt: Rebuild the macOS app, enable Experimental frame pipe from the desktop Output panel, then run the short failure-point preview and 2-minute 53:00-55:00 render before attempting the full long render.

## 2026-05-11 - ANSI bypass render audit and interval cursor

- Agent/task: Codex / audit whether random-normal/ANSI-bypass frames still pay ANSI prep/text-rendering cost before another full long-render attempt.
- Intent: Keep visual output, audio, Lite/Apple Lite/site behavior, versioning, packaging, publishing, pushing, and tagging unchanged; optimize only if the bypass path showed a safe compute shortcut.
- Files changed this pass: `renderer.py`, `CHANGELOG.md`, `docs/PERFORMANCE_NOTES.md`, `docs/agent-log.md`.
- Bypass-path finding: Non-PUBLIC ACCESS normal frames already skip `prepare_ansi_source()`, `render_text_art_frame()`, and `ImageDraw.text()`. PUBLIC ACCESS normal frames still prepare the shared public-access source treatment, then skip text rendering when bypassed. Transitions/endings run after the normal-vs-ANSI decision and do not force an extra ANSI render for normal frames.
- Behavior changed: Yes, performance-only. `_render_frames()` now uses a monotonic bypass interval cursor instead of scanning all random-normal intervals for every output frame, and reuses per-render framing/chunky/public-access constants inside the frame loop.
- Timing/validation: 10s Amber Terminal synthetic outputs remained H.264/yuv420p at 10.000s. Short PNG matrix before/after: full ANSI 24.36s/24.38s, 55.2% normal 14.20s/14.71s, 100% normal 6.14s/6.53s. Short pipe matrix before/after: full ANSI 23.09s/23.33s, 55.2% normal 13.27s/13.37s, 100% normal 5.46s/5.63s. Long lookup simulation for 5,276s/126,624 frames with 1,967 intervals improved from 4.323s old scan to 0.028s cursor with identical bypass-hit counts.
- Commands/tools run: `git status --short --branch`; `git log --oneline -15`; required repo docs reads; bypass/ANSI hot-path grep; synthetic media generation under `/tmp/wzrdvid-bypass-audit`; temporary monkeypatch timing harness for PNG and pipe render matrices; ffprobe duration/codec/pixel-format checks; long interval lookup simulation; `python3 -m py_compile renderer.py`; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`.
- Known gaps: The optimization does not reduce text-rendering cost on frames that remain ANSI. A temporary profiler run hit an unrelated read-only NumPy array edge when enabling the glitch output effect, so that effect was omitted from the timing harness rather than mixing another bug into this bypass pass.
- Next recommended prompt: Relaunch the local dev app, run a 10s preview at the old failure point and a 2-minute 53:00-55:00 render, then run the full long render only if both pass.

## 2026-05-11 - Preview/cache cleanup threshold correction

- Agent/task: Codex / correct the v0.2.0 automatic preview/cache cleanup threshold from 14 days to 7 days.
- Intent: Change only the age threshold and stale docs/log wording; keep manual cleanup, user export/source/recipe safety boundaries, Lite/Apple Lite/site behavior, renderer output, versioning, packaging, publishing, pushing, and tagging untouched.
- Files changed this pass: `app.py`, `docs/agent-log.md`.
- Behavior changed: Yes. Startup cleanup now targets WZRD.VID-managed preview/cache/temp files older than 7 days. Manual Clear Preview Cache still deletes all managed preview/cache files after confirmation.
- Commands/tools run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; threshold grep; targeted temp-directory cleanup tests for 7-day auto threshold, manual cleanup, and outside-file safety; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`.
- Known gaps: No broad filesystem scanning is attempted by design.
- Next recommended prompt: Run the real long render with `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1` after cache cleanup lands, then compare output, wall time, temp disk use, and failure behavior.

## 2026-05-11 - Preview/cache cleanup

- Agent/task: Codex / add v0.2.0 cleanup support for WZRD.VID-managed preview/cache/temp leftovers after the user found large accumulated rendered junk locally.
- Intent: Keep cleanup limited to app-owned preview/cache/temp paths, do not delete user-selected final exports, source media, recipes, Lite/Apple Lite/site behavior, renderer output, version, packaging, publishing, pushing, or tagging.
- Files changed this pass: `app.py`, `app_i18n.py`, `CHANGELOG.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes. The desktop app now has a localized Clear Preview Cache button in the Output area, confirmation copy with approximate size/counts, and best-effort startup cleanup of WZRD.VID-managed preview/cache/temp files older than 7 days. Cleanup failures log and continue.
- Safety boundaries: Manual cleanup targets the app-owned Previews directory plus old exact-prefix WZRD temp folders; automatic cleanup uses the 7-day age threshold. User-selected exports, source media, recipes, and arbitrary Desktop/Documents/custom folders are not scanned or deleted.
- Commands/tools run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; preview/cache/temp path audit grep; app localization coverage audit; helper cleanup tests with temp preview/cache/temp roots; offscreen GUI smoke for the cleanup button/confirmation and language switching; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`.
- Known gaps: No broad filesystem scanning is attempted by design. Real user-space cleanup should be verified cautiously by checking the confirmation size/counts before using the manual button on a machine with old previews.
- Next recommended prompt: Run the real long render with `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1` after cache cleanup lands, then compare output, wall time, temp disk use, and failure behavior.

## 2026-05-11 - Experimental direct frame-pipe renderer prototype

- Agent/task: Codex / prototype a reversible direct ffmpeg raw-frame pipe path after the v0.2.0 render-speed profiling found PNG staging secondary to ANSI/text drawing.
- Intent: Keep PNG frame staging as the default/fallback, add only an internal `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1` path, preserve visual frame generation and all audio/Lite/Apple Lite/website/version/package behavior, and stage only this pass despite unrelated Apple Lite worktree edits.
- Files changed this pass: `renderer.py`, `ffmpeg_utils.py`, `CHANGELOG.md`, `docs/PERFORMANCE_NOTES.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes, experimental/internal only. Default renders still stage PNG frames and encode as before. With `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1`, rendered RGB frames stream to ffmpeg stdin for the silent MP4; if that pre-audio pipe path fails, the renderer logs the failure and reruns the default PNG path from frame 0.
- Commands/tools run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; frame encode path grep; synthetic media generation under `/tmp/wzrdvid-frame-pipe`; `.venv/bin/python` PNG-vs-pipe render matrix; ffprobe output duration/codec/audio checks; forced pipe-failure fallback smoke; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`.
- Timing/validation: Amber 5s PNG 11.78s vs pipe 11.24s; Amber 10s 25.29s vs 24.01s; PUBLIC ACCESS 10s 27.52s vs 25.72s; Amber 10s with worky audio 25.65s vs 24.13s with AAC retained; Amber 30s 77.40s vs 72.55s; 31-minute synthetic source capped to 10s 22.37s vs 20.76s. All outputs were H.264/yuv420p with expected durations; worky audio output included AAC. Pipe mode did not log PNG staging and did not fall back during the matrix.
- Decisions made: Keep the pipe path experimental for v0.2.0. It reduces temp PNG disk pressure and gives modest wall-time wins, but text rendering remains the main bottleneck, so it should not be promoted to default until tested on the user's real long render and more real media.
- Known gaps: No visual pixel-diff was done beyond preserving the shared frame-generation path and checking codecs/durations/audio. The biggest speedup still requires future text rendering optimization or a broader renderer refactor.
- Next recommended prompt: Run the real long render with `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1` and compare output, wall time, temp disk use, and failure behavior against the PNG-staging renderer.

## 2026-05-11 - Desktop frame-render speed profiling

- Agent/task: Codex / implement the v0.2.0 desktop render speed measurement-first plan after the hue-shift overflow blocker fix.
- Intent: Measure render hot paths before optimizing, avoid visual/audio/Lite/Apple Lite/deployment/version/package changes, and keep any commit isolated from the dirty Apple Lite worktree.
- Files changed this pass: `docs/PERFORMANCE_NOTES.md`, `docs/agent-log.md`.
- Behavior changed: No. A trial renderer micro-optimization was measured and then reverted because it did not produce a real speedup.
- Commands/tools run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; hot-path grep; synthetic media generation with ffmpeg under `/tmp/wzrdvid-speed`; temporary `/tmp` profiling harness with `.venv/bin/python`; baseline and rejected-trial render matrix; ffprobe checks for output duration/streams; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`; hunk-limited staging review.
- Findings: Frame rendering dominates. On the 64-column 720x406/24fps synthetic matrix, Amber Terminal 10s took 24.41s total with 23.48s in frame render, 16.03s in `render_text_art_frame()`, and 12.18s in `ImageDraw.text()`. Amber Terminal 30s scaled linearly at 73.95s total. PNG writes and ffmpeg encode were secondary, and worky audio mux was about 0.06s.
- Optimization decision: Skipping literal-space glyph draws was the only tiny low-risk code change found, but the after-run was not faster on the test matrix, so it was reverted and no renderer code change was kept.
- Known gaps: Major speedup likely needs a v0.3.0 renderer refactor such as direct ffmpeg frame piping and/or batched/vectorized text drawing. The user's real long render should still be rerun after the hue-overflow fix to validate failure behavior and actual wall time.
- Next recommended prompt: Plan a v0.3.0 direct-frame-pipe renderer refactor for major long-render speedups.

## 2026-05-11 - Hue-shift overflow long-render blocker fix

- Agent/task: Codex / fix v0.2.0 blocker where a real v0.1.9 long render failed around frame 78,001/126,624 with `Python integer 65536 out of bounds for uint16` in `renderer._hue_shift_image()`.
- Intent: Fix the crash without blocking long renders, removing worky music mode, disabling Amber Terminal, changing Lite/Apple Lite, packaging, publishing, pushing, tagging, or doing a broad renderer rewrite.
- Files changed this pass: `renderer.py`, `CHANGELOG.md`, `docs/PERFORMANCE_NOTES.md`, `docs/agent-log.md`.
- Behavior changed: Yes. Hue-shift color math now uses safe wider integer arithmetic and explicit modulo before casting back to `uint8`, avoiding Python 3.14/newer NumPy unsigned overflow while preserving the intended 0-255 hue wrap behavior.
- Commands/tools run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; renderer/preset overflow audit grep; reproduced the pre-fix `_hue_shift_image(..., 65536)` failure under `.venv/bin/python`; direct hue edge test covering tiny RGB arrays, 0/255 source values, 256/65535 clipped input values, and shift amounts including 65535/65536; synthetic media generation with ffmpeg; Amber Terminal render smokes for tiny render, Buffer Underrun transition plus Buffer Exhausted ending, external audio with worky mode, medium 192-frame color path, and capped 31-minute synthetic `.mov`; ffprobe output duration/codec/audio checks; full Python compile command; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `git diff --check`.
- Checks passed: Direct hue edge test passed with valid `uint8` output range. All five render smokes passed; ffprobe showed valid H.264 video outputs, AAC audio on the worky external-audio case, and expected durations. Python compile, JavaScript syntax checks, and whitespace diff check passed.
- Checks failed/blocked: System `python3` lacks numpy, so direct hue/repro tests and render smokes used the repo `.venv/bin/python`. The original 126k-frame real render was not rerun in this pass.
- Decisions made: Do not add any long-render cap or rejection. Existing frame-count and long-media warning logs are sufficient for this crash fix; the root cause was isolated numeric hue math.
- Known gaps: Rerun the user's failing long `.mov` render after this fix. Full-length renders can still be expensive because they stage one PNG per output frame, and resume/disk-use controls remain future v0.2.0 hardening candidates.
- Next recommended prompt: Rerun the failing long render after the hue-shift overflow fix, then decide whether v0.2.0 needs stronger long-render progress, disk-use, or resume support.

## 2026-05-10 - Apple Lite added-audio Web Audio fallback

- Agent/task: Codex / update the Apple Lite device-test result after manual export retest passed but audio remained silent, then implement the narrow added-audio fix.
- Intent: Keep the native export bridge, fix only the explicit Add Audio bus for iOS WKWebView, preserve Lite's local-only/no-upload boundary, and avoid desktop renderer/media changes.
- Files changed this pass: `docs/lite/app.js`, `apple-lite/WZRDVIDLite/App/LiteSmokeHarness.swift`, `apple-lite/README.md`, `docs/lite/README.md`, `docs/APPLE_LITE_APP_RESEARCH.md`, `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-impact-map.md`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes, Lite/Apple Lite added-audio behavior only. Lite still tries `HTMLAudioElement.captureStream()` first, then falls back to Web Audio `createMediaElementSource()` plus `createMediaStreamDestination()` for the explicit Add Audio bus. The fallback also connects to `audioContext.destination` so added audio should be audible during render and captured into MediaRecorder. Source clip audio is still not preserved from Lite's visual source timeline.
- Commands/tools run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; targeted `rg`/`sed` inspections of Lite audio/export code and docs; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py apple-lite/scripts/prepare_lite_web_bundle.py apple-lite/scripts/run_simulator_smoke.py`; `plutil -lint apple-lite/WZRDVIDLite/App/Info.plist`; Lite forbidden-network grep; `python3 apple-lite/scripts/run_simulator_smoke.py`; physical iPhone `xcodebuild`; `xcrun devicectl device install app`; physical iPhone smoke launch with `WZRDVID_LITE_SMOKE=1`; normal physical iPhone launch; local static server with `curl` checks for `/`, `/lite/`, and `lite/app.js`; `git diff --check`.
- Checks passed: Manual user retest confirmed native export/download now works. JavaScript, Python, plist, forbidden-network, static site, and whitespace checks passed. Simulator smoke passed with `audioCaptureStream: false`, `audioContext: true`, `mediaStreamDestination: true`, `audioMode: "webAudio"`, `audioPipelineReady: true`, and all prior Lite smoke checks passing. Physical iPhone Debug build/install passed; physical smoke passed with the same `webAudio` audio pipeline result; normal physical launch succeeded.
- Checks failed/blocked: Manual user retest before this fallback found added audio/source clip audio silent in preview and exported clip. The Web Audio fallback is smoke-selected on the physical iPhone, but audible/exported audio with real added audio still needs direct hand retest. Source clip audio remains future work.
- Decisions made: Export bridge is confirmed useful and remains. Native import bridge is not needed. The narrow audio fix is browser-side Web Audio fallback for explicitly added audio, not a native audio renderer or source-clip audio mixer.
- Known gaps: Retest real added audio on iPhone. If the Web Audio fallback is still silent in the saved clip, inspect whether iOS MediaRecorder is dropping Web Audio destination tracks and consider a more native audio/export strategy.
- Next recommended prompt: Retest WZRD.VID Lite on the iPhone with an explicitly added audio file after the Web Audio fallback, then report whether audio is audible during render and present in the downloaded/shared clip.

## 2026-05-10 - Apple Lite native export bridge

- Agent/task: Codex / update the native bridge decision from manual iPhone results and implement only the narrow native bridge needed for the confirmed export blocker.
- Intent: Fix the confirmed WZRD.VID Lite Apple export handoff failure while preserving Lite's local-only/no-upload boundary, avoiding desktop renderer/performance changes, and avoiding a broader audio rewrite.
- Files changed this pass: `docs/lite/app.js`, `apple-lite/WZRDVIDLite/App/LiteWebView.swift`, `apple-lite/WZRDVIDLite/App/LiteSmokeHarness.swift`, `apple-lite/README.md`, `docs/APPLE_LITE_APP_RESEARCH.md`, `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-impact-map.md`, `CHANGELOG.md`, `docs/agent-log.md`.
- Behavior changed: Yes, Apple Lite wrapper export behavior only. The static Lite app now retains the latest rendered Blob for native handoff, and the Apple wrapper intercepts the rendered clip button, sends the Blob to Swift through `WKScriptMessageHandler`, writes a temporary local file, and presents the iOS share sheet. Browser Lite download behavior outside the native wrapper remains intact.
- Commands/tools run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; targeted `rg`/`sed` inspections of Lite export/audio code and Apple wrapper files; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `python3 -m py_compile app.py app_i18n.py renderer.py ffmpeg_utils.py presets.py theme.py run.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py apple-lite/scripts/prepare_lite_web_bundle.py apple-lite/scripts/run_simulator_smoke.py`; `plutil -lint apple-lite/WZRDVIDLite/App/Info.plist`; Lite forbidden-network grep; `python3 apple-lite/scripts/run_simulator_smoke.py`; physical iPhone `xcodebuild`; `xcrun devicectl device install app`; physical iPhone smoke launch with `WZRDVID_LITE_SMOKE=1`; normal physical iPhone launch; local static server with `curl` checks for `/`, `/lite/`, and `lite/app.js`; `git diff --check`.
- Checks passed: JavaScript, Python, plist, and whitespace checks passed. Forbidden-network grep returned no matches. Static `/` and `/lite/` loaded. Simulator smoke passed with `nativeExportBridge: true`, `nativeRenderedClipReady: true`, and all existing Lite smoke checks passing. Physical iPhone Debug build/install passed, physical smoke passed with `nativeExportBridge: true` and `nativeRenderedClipReady: true`, and the updated app launched normally afterward.
- Checks failed/blocked: Manual user testing found real Photos/Files import and visual preview worked, but audio was silent from both added audio and source clips. Manual user testing also confirmed pre-bridge export failed because tapping Download opened the rendered clip for playback. The post-bridge iOS share sheet still needs a hand retest.
- Decisions made: Native import bridge is not needed based on the manual import pass. Native export/share bridge is needed and has a first implementation. The no-audio result is a separate Apple Lite audio-capture blocker and was not folded into the export bridge.
- Known gaps: Direct iPhone retest is needed to confirm tapping the updated rendered clip button presents the share sheet and can save/share/open the file. Apple Lite iOS audio capture needs a separate focused pass before TestFlight.
- Next recommended prompt: Retest WZRD.VID Lite on the iPhone with the updated native export bridge: render a short clip, tap the rendered clip button, confirm the iOS share sheet save/share path, and then start a separate Apple Lite audio-capture investigation for missing music/source audio.

## 2026-05-10 - Apple Lite manual import/export handoff pending

- Agent/task: Codex / manually test real Photos/Files import and rendered clip export/share on the installed WZRD.VID Lite iPhone app, then implement a narrow native export/share bridge only if the blob download handoff fails.
- Intent: Push the real-device checklist as far as available local tooling allows without changing Lite/browser behavior, desktop behavior, publishing, pushing, tagging, or release packaging.
- Files changed this pass: `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-log.md`.
- Behavior changed: No. Documentation/logging only; no native import/share bridge was implemented because no real Photos/Files import failure or export/share failure was confirmed.
- Commands/tools run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; `rg` audit of the device log and agent log; `xcrun devicectl --help` and device subcommand help; `xcrun devicectl device info displays`; `xcrun devicectl device info lockState`; `xcrun devicectl device info processes`; normal non-smoke `xcrun devicectl device process launch`; Xcode Devices and Simulators UI via Computer Use; Xcode device screenshot; local screenshot view.
- Checks passed: The connected iPhone was unlocked, the installed `com.samhowell.wzrdvid.lite` app launched normally again, Xcode Devices listed `WZRD.VID Lite` as installed, and an Xcode device screenshot confirmed the native shell was open to the bundled WZRD.VID Lite UI with the `ADD MEDIA` area visible.
- Checks failed/blocked: CoreDevice/Xcode exposed launch, install, process inspection, app listing, display info, logs, and screenshots, but no remote tap/gesture control for the physical iPhone in this session. Real Photos picker import, Files picker import, real local media render, and tapping the generated blob download/export link remain pending direct hand testing on the phone.
- Decisions made: Do not add a native import/share bridge yet. The current evidence still shows no confirmed import/export blocker; if hand testing proves the rendered blob download cannot produce a user-accessible save/share/open handoff, prefer a narrow native export/share bridge.
- Known gaps: Direct iPhone testing is still needed for Photos/Files picker import and user-visible export/share behavior before TestFlight.
- Next recommended prompt: I manually tested WZRD.VID Lite on the iPhone with real Photos/Files media. Import worked/failed and export/share worked/failed: [results]. Update the bridge decision and implement the narrow bridge only if needed.

## 2026-05-10 - Apple Lite physical-device smoke passed

- Agent/task: Codex / continue after Xcode signing was configured and rerun the Apple Lite real-device checklist/native bridge decision.
- Intent: Verify as much as possible on the connected iPhone without changing Lite/browser behavior, desktop behavior, publishing, pushing, tagging, or release packaging.
- Files changed this pass: `apple-lite/WZRDVIDLite.xcodeproj/project.pbxproj`, `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-log.md`.
- Behavior changed: No shipped behavior changed. The Xcode project keeps the local Personal Team signing setting for device builds; Apple Lite and desktop runtime code were not changed.
- Commands/tools run: prior signing/device commands from this pass; `git diff --check`; `plutil -lint apple-lite/WZRDVIDLite/App/Info.plist`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; physical-device `xcodebuild`; `xcrun devicectl device install app`; `xcrun devicectl device process launch --environment-variables '{"WZRDVID_LITE_SMOKE":"1"}' com.samhowell.wzrdvid.lite`; normal non-smoke `xcrun devicectl device process launch`; targeted Lite/export grep.
- Checks passed: The physical-device Debug build succeeded after selecting `Samuel Howell (Personal Team)`. `WZRD.VID Lite` version `0.2.0` build `1` installed on the connected iPhone. After the developer profile was trusted on-device, the Debug smoke harness launched and passed on the physical iPhone with no errors or warnings: bundled Lite load, file input surface, export blob surface, Spanish language switching, 15-second duration, Random clip assembly, synthetic local file import, random render completion, and generated `wzrdvid-lite-15s` download-link readiness. `Blob`, `URL.createObjectURL`, `File`, `DataTransfer`, `MediaRecorder`, `canvas.captureStream`, and `navigator.share` were available in the device WKWebView. Normal non-smoke app launch also succeeded.
- Checks failed/blocked: Real Photos picker import, Files picker import, local video render, local video+photo random render, local audio import/render, and user-visible export/share/open behavior still require hand testing on the iPhone. The current Lite app creates a blob download link; it does not yet call `navigator.share`.
- Decisions made: Do not add a native import/share bridge yet. No native bridge blocker has been confirmed. The main remaining bridge-decision item is whether tapping the rendered blob download link creates a user-accessible save/share/open handoff with real media; if it does not, prefer a narrow native export/share bridge.
- Known gaps: Manual device testing is still needed for real Photos/Files media and user-facing export/share behavior before TestFlight.
- Next recommended prompt: Manually test real Photos/Files import and rendered clip export/share on the installed WZRD.VID Lite iPhone app, then implement a narrow native export/share bridge only if the blob download handoff fails.

## 2026-05-10 - Apple Lite installed on device, blocked by profile trust

- Agent/task: Codex / configure Xcode signing for WZRD.VID Lite on the connected iPhone, rerun the real-device checklist, and update the native bridge decision.
- Intent: Use local Xcode signing only, then install/launch the existing Apple Lite wrapper on the physical iPhone without changing Lite/browser behavior, desktop behavior, publishing, pushing, tagging, or release packaging.
- Files changed this pass: `apple-lite/WZRDVIDLite.xcodeproj/project.pbxproj`, `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-log.md`.
- Behavior changed: No shipped behavior changed. The Xcode project now has a local Personal Team signing setting for device builds; Lite code and desktop code were not changed.
- Commands/tools run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; Xcode Signing & Capabilities UI via Computer Use; `security find-identity -v -p codesigning`; provisioning-profile checks; `xcrun devicectl list devices --timeout 30`; `xcodebuild -showdestinations -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -destination-timeout 30`; `python3 apple-lite/scripts/prepare_lite_web_bundle.py`; physical-device `xcodebuild`; `xcrun devicectl device install app`; `xcrun devicectl device process launch` with `WZRDVID_LITE_SMOKE=1`; `xcrun devicectl device info apps`.
- Checks passed: Xcode showed the connected `iPhone14` destination. Selecting `Samuel Howell (Personal Team)` in Signing & Capabilities created an Xcode-managed provisioning profile for `com.samhowell.wzrdvid.lite`. The physical-device Debug build succeeded with the Apple Development certificate and managed profile. `devicectl` installed `WZRD.VID Lite` version `0.2.0` build `1` on the connected iPhone.
- Checks failed/blocked: Launching the installed app failed before startup because iOS reported the development profile has not been explicitly trusted by the user: `Unable to launch com.samhowell.wzrdvid.lite because it has an invalid code signature, inadequate entitlements or its profile has not been explicitly trusted by the user`. The debug smoke harness did not run.
- Decisions made: Do not add a native import/share bridge yet. The pass is blocked at device profile trust before WKWebView launch, so there is still no confirmed import/export failure to fix.
- Known gaps: Trust the developer profile on the iPhone, then rerun device launch/smoke. Physical-device Lite launch, offline load, language switching, Photos/Files import, random clip rendering, and export/share behavior remain unverified.
- Next recommended prompt: Trust the WZRD.VID Lite developer profile on the iPhone, then rerun the installed app smoke and real-device checklist.

## 2026-05-10 - Apple Lite real-device checklist blocked by signing

- Agent/task: Codex / rerun the Apple Lite real-device checklist after Developer Mode was enabled on the connected iPhone.
- Intent: Re-attempt physical-device build/install, update the device-test log and native bridge decision, and avoid code changes unless a confirmed import/export blocker appears.
- Files changed this pass: `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-log.md`.
- Behavior changed: No. Documentation/logging only; Apple Lite code, desktop renderer/performance, Lite browser behavior, packaging, publishing, pushing, and tagging were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; `xcrun xcdevice list --timeout 10`; `xcodebuild -showdestinations -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -destination-timeout 30`; `xcrun devicectl list devices --timeout 30`; `python3 apple-lite/scripts/prepare_lite_web_bundle.py`; `security find-identity -v -p codesigning`; physical-device `xcodebuild` with `DEVELOPMENT_TEAM=3367V5767A`; `find ~/Library/MobileDevice/Provisioning Profiles ...`; `xcrun devicectl device info details --device E3AA485E-F6D0-51A3-848F-9143BA1FC07E`; checked for existing installed WZRD.VID Lite app on the device.
- Checks passed: The connected `iPhone14` is now a usable physical destination in Xcode destination discovery. CoreDevice reports Developer Mode enabled, DDI services available, wired tunnel connected, install and launch capabilities, and UDID `00008110-001C4D410C85401E`. The local Apple Development signing identity `Apple Development: samchasehowell@gmail.com (3367V5767A)` exists.
- Checks failed/blocked: The physical-device build failed before install because Xcode has no configured account/provisioning profile for Team `3367V5767A` and bundle ID `com.samhowell.wzrdvid.lite`: `No Account for Team "3367V5767A"` and `No profiles for 'com.samhowell.wzrdvid.lite' were found`. No provisioning profiles were present under `~/Library/MobileDevice/Provisioning Profiles`, and no existing WZRD.VID Lite app was installed on the device.
- Decisions made: Do not add a native import/share bridge yet. The pass is blocked by local signing/provisioning before app launch, so there is still no confirmed WKWebView import/export failure to fix.
- Known gaps: Physical-device Lite launch, offline load, language switching, Photos/Files import, random clip rendering, and export/share behavior remain unverified until Xcode account/provisioning is configured.
- Next recommended prompt: Configure Xcode signing for WZRD.VID Lite on the connected iPhone, then rerun the Apple Lite real-device checklist and update the native bridge decision.

## 2026-05-10 - Apple Lite real-device checklist blocked by Developer Mode

- Agent/task: Codex / continue the Apple Lite real-device checklist after the user connected an unlocked trusted iPhone with Developer Mode reportedly enabled.
- Intent: Attempt the physical-device WZRD.VID Lite checklist and update the device-test log, without changing Apple Lite, desktop, renderer, Lite browser behavior, packaging, publishing, pushing, or tagging.
- Files changed this pass: `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-log.md`.
- Behavior changed: No. Documentation/logging only; no native import/share bridge was implemented because no app-level import/export blocker was reached.
- Commands run: `git status --short --branch`; `git log --oneline -8`; required repo docs reads; `xcrun devicectl list devices --timeout 30`; `xcrun xctrace list devices`; `xcodebuild -showdestinations -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite -destination-timeout 30`; `system_profiler SPUSBDataType` with iPhone/iPad grep; `xcrun devicectl device info details --device 47F38D01-B5D9-5F4F-8976-808134B26783`; `xcrun devicectl manage pair --device 47F38D01-B5D9-5F4F-8976-808134B26783 --timeout 30`; `ioreg -p IOUSB -l -w0` with iPhone/iPad grep; `xcrun xcdevice list --timeout 10`; physical-device `xcodebuild` attempt for UDID `00008110-001C4D410C85401E`.
- Checks passed: `ioreg` showed a physical USB `iPhone`, and `xcrun xcdevice list --timeout 10` showed USB device `iPhone14` on iOS `26.4.2` as available with UDID `00008110-001C4D410C85401E`.
- Checks failed/blocked: The stale CoreDevice record for `rivers' iPhone` remained `unavailable`/offline. `devicectl device info details` reported `developerModeStatus: disabled`, `ddiServicesAvailable: false`, and `tunnelState: unavailable`; `devicectl manage pair` failed with CoreDevice error `4000`. The direct physical-device `xcodebuild` attempt for the available USB UDID failed before build/install with `Developer Mode disabled To use iPhone14 for development, enable Developer Mode in Settings -> Privacy & Security.`
- Decisions made: Do not add a native import/share bridge yet. The real-device checklist remains blocked before app launch, so there is no confirmed WKWebView import/export failure to fix.
- Known gaps: Physical-device Lite launch, offline load, language switching, local Photos/Files import, random clip rendering, and export/share behavior remain unverified.
- Next recommended prompt: Re-enable Developer Mode on the connected iPhone, reboot/reconnect until Xcode lists it as an available run destination, then rerun the Apple Lite real-device checklist and update the native bridge decision.

## 2026-05-10 - Apple Lite real-device manual test guide

- Agent/task: Codex / manually test WZRD.VID Lite on a real iPhone/iPad with local videos/photos, then decide whether a native import/share bridge is needed before TestFlight setup.
- Intent: Keep this as guided manual-test and results logging only, without code changes, unless a specific real-device blocker is found.
- Files changed this pass: `apple-lite/README.md`, `docs/APPLE_LITE_APP_RESEARCH.md`, `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, `docs/agent-log.md`.
- Behavior changed: No. Documentation/logging only; desktop renderer/performance, Lite browser behavior, Apple wrapper code, signing, packaging, publishing, pushing, and tagging were not changed.
- Commands run: `git status --short --branch`; required repo docs reads; `xcrun devicectl list devices`; `xcrun xctrace list devices`; `xcrun devicectl device install app --help`; `xcrun devicectl device process launch --help`; `xcodebuild -showdestinations -project apple-lite/WZRDVIDLite.xcodeproj -scheme WZRDVIDLite`; targeted docs grep; `git diff --check`; final `git status --short --branch`.
- Checks passed: Xcode project destinations are available for simulators and the generic iOS device placeholder. The device/install/launch command help confirms the current local Xcode CLI path for later real-device install and launch when signing/device availability is ready. Added a guided real-device checklist and bridge decision rubric.
- Checks failed/blocked: A real iPhone was visible but not testable: `xcrun devicectl list devices` showed `rivers' iPhone` as `unavailable`, and `xcrun xctrace list devices` listed `rivers' iPhone (26.3)` under `Devices Offline`. No physical-device manual test was executed.
- Decisions made: Do not add a native import/share bridge yet. The need for a bridge remains pending until the real device checklist proves WKWebView file input or blob export/download fails with user media.
- Known gaps: Real iPhone/iPad import from Photos/Files, local video/photo renders, random clips, and export/share behavior remain unverified on physical hardware.
- Next recommended prompt: Run the Apple Lite real-device checklist on an unlocked iPhone/iPad, fill `docs/APPLE_LITE_DEVICE_TEST_LOG.md`, and implement only the narrow native bridge needed for any confirmed import/export blocker.

## 2026-05-10 - Apple Lite Xcode project and simulator smoke

- Agent/task: Codex / create the WZRD.VID Lite Xcode project from the Apple wrapper groundwork, then run simulator smoke tests for local file import, language switching, random clips, and export/share behavior.
- Intent: Move Apple Lite from source-only wrapper groundwork to a simulator-ready local Xcode project while preserving the bundled local Lite shell, no-upload/no-network stance, desktop performance freeze, and no publish/push/tag/package boundary.
- Files changed this pass: `AGENTS.md`, `CHANGELOG.md`, `apple-lite/README.md`, `apple-lite/WZRDVIDLite.xcodeproj/project.pbxproj`, `apple-lite/WZRDVIDLite.xcodeproj/xcshareddata/xcschemes/WZRDVIDLite.xcscheme`, `apple-lite/WZRDVIDLite/App/LiteSmokeHarness.swift`, `apple-lite/WZRDVIDLite/App/LiteWebView.swift`, `apple-lite/scripts/run_simulator_smoke.py`, `docs/APPLE_LITE_APP_RESEARCH.md`, `docs/agent-change-playbook.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: Yes, Apple Lite groundwork only. A simulator-ready Xcode project now builds the existing SwiftUI/WKWebView shell, and Debug builds can run a dormant smoke harness when launched with `WZRDVID_LITE_SMOKE=1` or `--lite-smoke`. Desktop renderer/performance code, desktop UI, static Lite browser behavior, website behavior, release packaging, version files, publishing, pushing, and tagging were not changed.
- Commands run: `git status --short --branch`; `git log --oneline -12`; required repo docs reads; Apple Lite source/project inspection; `xcodebuild -list -project apple-lite/WZRDVIDLite.xcodeproj`; `python3 -m py_compile apple-lite/scripts/prepare_lite_web_bundle.py apple-lite/scripts/run_simulator_smoke.py`; `plutil -lint apple-lite/WZRDVIDLite/App/Info.plist`; `python3 apple-lite/scripts/run_simulator_smoke.py`; full Python compile command including Apple Lite scripts; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; Lite forbidden-network grep across `docs/lite`, `docs/index.html`, `docs/i18n.js`, and `apple-lite`; `git diff --check`; final status checks.
- Checks passed: Xcode 26.3 recognized the committed project target and shared scheme. The simulator smoke built the project with `CODE_SIGNING_ALLOWED=NO`, installed it on the iPhone 17 iOS 26.2 simulator, launched the local bundled WKWebView shell, and reported passing checks for Lite load, local file input surface, synthetic local image import through the Lite code path, Spanish language switching, 15-second duration, Random clip assembly, MediaRecorder/canvas capture, blob export surface, and generated `wzrdvid-lite-15s` download readiness. Python and JavaScript syntax checks passed, Info.plist lint passed, forbidden-network grep returned no matches, and diff whitespace check passed.
- Checks failed: The first hand-written project file had one bad Sources build-phase reference; fixed before the final project read/build. The first smoke harness used `evaluateJavaScript` for an async result and returned an unsupported-type error; fixed by using `WKWebView.callAsyncJavaScript`.
- Decisions made: Kept the smoke harness Debug-only and environment/argument gated so normal app launches do not run tests. Kept generated `LiteWeb/`, `DerivedData/`, and Python cache output ignored and removed after validation.
- Known gaps: The smoke uses a synthetic image file to exercise the local file import code path; it does not manually drive the iOS document/photo picker with real user media. Native share sheet/export bridge, final Team ID, production Bundle ID, App Store Connect record, TestFlight build, and real-device smoke remain future work.
- Next recommended prompt: Manually test WZRD.VID Lite on a real iPhone/iPad with local videos/photos, then decide whether a native import/share bridge is needed before TestFlight setup.

## 2026-05-10 - Apple Lite packaging groundwork

- Agent/task: Codex / start WZRD.VID Lite Apple app packaging groundwork while keeping desktop v0.2.0 performance fixes frozen.
- Intent: Add a minimal native-shell groundwork path for WZRD.VID Lite that bundles the existing static Lite app locally in WKWebView, without adding desktop renderer parity, ffmpeg, backend services, analytics, accounts, remote config, packaging, publishing, pushing, or tagging.
- Files changed this pass: `apple-lite/.gitignore`, `apple-lite/README.md`, `apple-lite/WZRDVIDLite/App/ContentView.swift`, `apple-lite/WZRDVIDLite/App/Info.plist`, `apple-lite/WZRDVIDLite/App/LiteWebView.swift`, `apple-lite/WZRDVIDLite/App/WZRDVIDLiteApp.swift`, `apple-lite/WZRDVIDLite/Resources/.gitkeep`, `apple-lite/scripts/prepare_lite_web_bundle.py`, `AGENTS.md`, `CHANGELOG.md`, `docs/APPLE_LITE_APP_RESEARCH.md`, `docs/agent-change-playbook.md`, `docs/agent-impact-map.md`, `docs/agent-log.md`.
- Behavior changed: No shipped app behavior changed. This adds Apple Lite wrapper source/docs only; desktop renderer/performance code, Lite browser behavior, website deployment config, release packaging, version files, and `docs/CNAME` were not changed.
- Commands run: `git status --short --branch`; required repo docs reads; Lite path/asset audits; local Xcode/Swift SDK inspection; `python3 apple-lite/scripts/prepare_lite_web_bundle.py`; generated-bundle static server with `curl` checks for `/lite/`, `/i18n.js`, and referenced assets; `python3 -m py_compile ... apple-lite/scripts/prepare_lite_web_bundle.py`; `node --check docs/i18n.js`; `node --check docs/lite/app.js`; `plutil -lint apple-lite/WZRDVIDLite/App/Info.plist`; Swift parse with the iPhone Simulator SDK; Lite forbidden-network grep; `git diff --check`; final `git status --short --branch`.
- Checks passed: Xcode 26.3 and iPhone Simulator SDK were available. The bundle prep script generated 18 local web files from existing Lite/site assets, and local static smoke loaded the generated Lite page, `i18n.js`, and required UI/logo assets. SwiftUI/WKWebView source parsed cleanly against the iPhone Simulator SDK. Info.plist lint passed. Python and JavaScript syntax checks passed. Forbidden-network grep returned no matches. Generated `LiteWeb/` and Python cache outputs were removed and are ignored.
- Checks failed: None.
- Decisions made: Added source-only SwiftUI/WKWebView wrapper groundwork and a bundle prep script instead of committing an `.xcodeproj` before the final Team ID/Bundle ID are known. The wrapper blocks non-local navigation and hides the public-site back link in the native shell.
- Known gaps: No committed Xcode project, signing config, Team ID, App Store Connect record, TestFlight build, native export/share bridge, or device smoke yet. WKWebView file input, MediaRecorder, and blob download/export behavior still need simulator and real-device testing.
- Next recommended prompt: Create the WZRD.VID Lite Xcode project from the Apple wrapper groundwork, then run simulator smoke tests for local file import, language switching, random clips, and export/share behavior.

## 2026-05-10 - Real long-media beta pass

- Agent/task: Codex / v0.2.0 real long-media beta pass before Apple Lite app packaging.
- Intent: Run the v0.2.0 desktop performance-smoke matrix against the user-supplied long local AVI, decide whether more desktop performance fixes are needed before Apple Lite packaging, and avoid committing private media or generated outputs.
- Files changed this pass: `docs/PERFORMANCE_NOTES.md`, `docs/agent-log.md`.
- Behavior changed: No. Validation/docs only; app behavior, renderer/media behavior, Lite behavior, versioning, packaging, publishing, pushing, and tagging were not changed.
- Commands run: `git status --short --branch`; required repo docs reads; `ffprobe` metadata inspection; source render matrix with the repo `.venv`; output duration/audio checks with `ffprobe`; `git diff --check`; final `git status --short --branch`.
- Checks passed: Supplied media is a 700.26 MB AVI, 1:52:10.01 duration, MPEG-4 video at 608x272/23.976 fps with MP3 audio. Probe cache smoke again issued 1 ffprobe call total for repeated helper calls. Real-media render smokes passed for long source to 10s, long source to 90s, random video plus photo 30s, source audio only, external audio from the same AVI, worky external audio, external plus selected source audio, random plus source audio, random plus match-to-music rejection, and 5s/10s mid-file preview-like renders. Output durations and audio presence matched expectations.
- Checks failed: None.
- Decisions made: The supplied long AVI did not reveal a v0.2.0 desktop performance blocker. No additional desktop performance fix is required before starting Apple Lite app packaging groundwork for this tested media class.
- Known gaps: This was not a 4K/60fps, HEVC, variable-frame-rate, rotated phone video, or high-bitrate long-GOP phone export. Those media classes remain worth beta testing if available.
- Next recommended prompt: Start WZRD.VID Lite Apple app packaging groundwork while keeping desktop v0.2.0 performance fixes frozen unless a blocker appears.

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
