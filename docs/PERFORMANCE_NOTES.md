# WZRD.VID Performance Notes

## 2026-05-12 - frame pipe promoted to default transport

- Change: direct raw RGB ffmpeg frame pipe is now the default desktop render transport. Legacy PNG staging remains available through the local desktop developer opt-out, `Force legacy PNG staging`, or through `WZRDVID_FORCE_PNG_STAGING=1`. If the pipe path fails before audio muxing, the renderer logs the failure and reruns the same render through PNG staging.
- Recipe scope: the opt-out is local settings only. Recipe export/import remains unchanged.
- Logging: render startup now reports `Frame pipe transport: enabled (default desktop transport)` or `Frame pipe transport: forced legacy PNG (...)`; fallback logs `Frame pipe transport failed before audio muxing (...)` followed by `Falling back to PNG frame staging.`

| Case | Default pipe total | Legacy PNG total | Default temp frames | Legacy temp frames | Output validation |
| --- | ---: | ---: | ---: | ---: | --- |
| Warm-cache HEIC WZRD Blocks 30s + worky | 47.68s | 50.64s | 0 / 0.00 MB | 720 / 16.58 MB | 30.000s H.264/yuv420p + AAC |
| Normal video 10s | 19.09s | 20.19s | 0 / 0.00 MB | 240 / 15.48 MB | 10.000s H.264/yuv420p |
| PUBLIC ACCESS 10s | 23.59s | 25.20s | 0 / 0.00 MB | 240 / 40.48 MB | 10.000s H.264/yuv420p |
| Normal video 10s + worky audio | 19.11s | 20.21s | 0 / 0.00 MB | 240 / 15.48 MB | 10.000s H.264/yuv420p + AAC |
| Forced pipe failure fallback 2s | 0.88s fallback | n/a | fallback used PNG | 23 / 0.32 MB | 2.000s H.264/yuv420p |

- Env opt-out smoke: `WZRDVID_FORCE_PNG_STAGING=1` forced legacy PNG staging and produced a valid 1.000s H.264/yuv420p MP4.
- Current conclusion: default pipe is the better desktop default for v0.2.0 because it keeps output validation and audio behavior intact while avoiding the large PNG frame directory on successful renders. Keep legacy PNG staging as a local emergency fallback until more real long renders and HEIC batches are retested.

## 2026-05-12 - frame-pipe default readiness audit

- Goal: decide whether the experimental desktop frame pipe is safe enough to become the default render transport, using the real HEIC/WZRD Blocks slowdown shape as the target while leaving current behavior unchanged in this audit pass.
- Test matrix under `/tmp/wzrdvid-pipe-default-audit`: synthetic HEIC stills, synthetic normal MP4, synthetic external WAV, 720x406, 24 fps where applicable. The HEIC target used WZRD Blocks, chunky blocks, random clip assembly, warm HEIC proxy cache, external audio, and worky mode.

| Case | PNG total | Pipe total | PNG temp frames | Pipe temp frames | Output validation |
| --- | ---: | ---: | ---: | ---: | --- |
| Warm-cache HEIC WZRD Blocks 30s + worky | 49.80s | 47.85s | 720 / 16.58 MB | 0 / 0.00 MB | 30.000s H.264/yuv420p + AAC |
| Normal video 10s | 20.00s | 19.09s | 240 / 15.48 MB | 0 / 0.00 MB | 10.000s H.264/yuv420p |
| PUBLIC ACCESS 10s | 25.02s | 23.45s | 240 / 40.48 MB | 0 / 0.00 MB | 10.000s H.264/yuv420p |
| Normal video 10s + worky audio | 20.05s | 18.95s | 240 / 15.48 MB | 0 / 0.00 MB | 10.000s H.264/yuv420p + AAC |
| Forced pipe failure fallback 2s | n/a | 0.83s fallback | 24 / 0.33 MB | fallback used PNG | 2.000s H.264/yuv420p |

- Pipe path did not emit `frame_%06d.png` in successful pipe runs and did not create a PNG frame directory. The default PNG path did create the expected frame sequence.
- Worky/external audio stayed unchanged: the HEIC worky case and normal-video worky case both preserved AAC output, with external audio mux at about 0.14s and 0.07s respectively in both transports.
- Forced-failure smoke monkeypatched the raw-frame encoder to raise before audio muxing. The renderer logged the pipe failure, logged fallback to PNG frame staging, and produced a valid fallback MP4.
- Decision: the measured current pipe path is stable and consistently no worse on this matrix. It is reasonable to promote it to the default desktop render transport in a separate narrow code pass, preserving the existing automatic fallback to PNG staging and leaving the developer/env override available as an emergency off-switch if added. This audit pass does not change the default behavior.

## 2026-05-12 - warm-cache HEIC motion/text render audit

- Finding: warm-cache HEIC slideshow planning is now bounded, but the 30s WZRD Blocks render still spends most time in per-frame HEIC motion plus ANSI/text drawing.
- Motion cache audit: the measured 720-frame random HEIC slideshow had no exact repeated motion-frame keys. Exact `(path, local_time, loop_duration)` and rounded phase keys both produced `total=720 unique=720 reusable_hits=0`. A quantized phase cache could create hits, but would change motion sampling, so it was not implemented.
- Change kept: HEIC/HEIF motion frames now stay as `Image.Image` objects after the motion crop/contrast step instead of round-tripping through NumPy before the normal output-size framing path. Text layout now precomputes column and row pixel positions once per render layout.
- Change rejected: a vectorized per-frame color grid for WZRD Blocks was tested and removed because it regressed text-render time on the warm-cache 30s matrix.
- Same synthetic matrix as the prior HEIC pass: 12 generated HEIC stills, WZRD Blocks, 720x406, 24 fps, CRF 28, random clip assembly, external audio plus worky mode, warm proxy cache.
- Unmodified `HEAD` comparison: 50.93s total, 49.98s frame render, 13.13s source/still, 5.98s ANSI prep, 28.92s text render, 1.46s frame write, 0.76s encode.
- After kept changes: 49.32s total, 48.37s frame render, 12.54s source/still, 5.41s ANSI prep, 28.48s text render, 1.46s frame write, 0.76s encode.
- Output validation: both before and after outputs were 30.000s H.264/yuv420p plus AAC. The renderer still logged PNG staging by default because the experimental frame pipe was not enabled.
- Current conclusion: the safe local win is small, about 1.6s on this 30s matrix, and it does not change visual output intentionally. The remaining cost is still intentional HEIC motion and ImageDraw/text rendering; larger gains need a deeper text-rendering or frame-transport refactor.

## 2026-05-12 - HEIC/photo still import and render performance

- Finding: the HEIC/photo slowdown was still-specific, not caused by the recent ANSI bypass optimization. The desktop import path synchronously decoded HEIC/HEIF files for validation, and `_build_timeline()` decoded every photo again during every preview/render planning pass. During rendering, HEIC motion frames were animated from full-resolution decoded images.
- Change: HEIC/HEIF files can now be selected from the normal media picker. HEIC validation is deferred so adding many stills does not block the UI on full decodes. A shared still cache stores HEIC proxy PNGs keyed by source path, size, mtime, and proxy size. Render-time stills use a proxy sized to about 2x the selected output dimension, preserving the final output size while avoiding full phone-resolution work on every frame.
- Cache scope: still proxies live under the WZRD.VID app-support cache area and are included in the existing automatic/manual preview/cache cleanup flow. User exports, source media, and recipes are not touched.
- Logging added: media import timing, random assembly timing, audio-reactive analysis timing, still decode/cache/motion timing, frame timing detail, and explicit frame-pipe enabled/disabled/fallback logs.
- Synthetic phone-sized HEIC matrix under `/tmp/wzrdvid-heic-perf-hi`: 12 generated 3024x4032 HEIC files, WZRD Blocks, Social Share-style 720x406, 24 fps, CRF 28, random clip assembly, external audio plus worky mode.
- Before: `_build_timeline()` took 3.91s and 3.92s on repeated runs; 5s/120-frame render took 38.44s total with 34.13s in frame render.
- After: `_build_timeline()` took effectively 0.000s on repeated runs; 5s cold-cache render took 8.60s, and 5s warm-cache render took 6.81s. A 10s warm render took 13.72s. A 30s/720-frame render took 42.47s total with 41.32s in frame render and valid H.264/yuv420p plus AAC output.
- Pipe smoke: the same 5s HEIC case with the desktop developer frame-pipe setting enabled produced a valid 5.000s H.264/yuv420p plus AAC output and logged direct frame piping instead of `frame_%06d.png`.
- Current conclusion: repeated HEIC planning and full-resolution still motion were the immediate v0.2.0 blockers for HEIC slideshows. The remaining frame cost is now primarily the intentional still motion plus ANSI/chunky rendering at output size; real user HEIC batches should be retested, but the synthetic matrix moved from preview-like unusable performance to materially faster behavior.

## 2026-05-12 - experimental frame-pipe launch gate audit

- Finding: `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1 open dist/WZRD.VID.app` is not a reliable way to enable the experimental renderer in the packaged macOS app. The environment variable is applied to the `open` command, but the app bundle is launched by macOS LaunchServices and the WZRD.VID process should not be assumed to inherit that shell environment.
- Renderer-side evidence: the frame-pipe code has no preset/audio/render-configuration rejection path. If the render process sees `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1`, or the new desktop developer checkbox is enabled, it attempts the raw RGB ffmpeg pipe path before audio muxing. If it does not see an explicit enable, it logs the disabled reason and uses PNG frame staging.
- Added render-start logging for the experimental frame pipe gate: enabled, disabled, unavailable, or fallback, including the reason. A packaged app render that still logs `WZRDVID_EXPERIMENTAL_FRAME_PIPE is not set` confirms the bundle process did not receive the shell variable.
- Added a local desktop developer setting, `Experimental frame pipe`, in the Output area. It persists only in the local app settings JSON and is intentionally not exported in recipe JSON. The default remains off, so PNG staging remains the normal renderer unless pipe mode is explicitly enabled.
- Validation under source run: explicit disabled mode logged PNG staging and the ffmpeg `frame_%06d.png` input; explicit enabled mode logged raw `rgb24` pipe encoding with no PNG sequence command. Both outputs were H.264/yuv420p at the expected duration.

## 2026-05-11 - v0.2.0 ANSI bypass / random-normal audit

- Audit answer: for non-PUBLIC ACCESS presets, `_render_frames()` already decides normal/bypass before `prepare_ansi_source()` and `render_text_art_frame()`. True normal frames do not call `prepare_ansi_source()`, `render_text_art_frame()`, or `ImageDraw.text()`.
- PUBLIC ACCESS is different by design: it prepares one public-access-treated source frame first, then either outputs that normal frame or sends it through ANSI/text rendering. Bypassed PUBLIC ACCESS frames still skip `render_text_art_frame()`.
- Transitions, global artifacts, endings, and loop-friendly blending run after the normal-vs-ANSI decision. They do not force an extra ANSI render for a normal frame, though transitions can visually blend from a prior ANSI frame.
- The safe optimization landed here is not a visual shortcut. It changes bypass membership lookup inside `_render_frames()` from a per-frame scan of all intervals to a monotonic interval cursor, and reuses per-render framing/chunky/public-access constants in the frame loop.
- Synthetic 10s Amber Terminal 720x406/24fps/CRF28 outputs stayed valid H.264/yuv420p at 10.000s. The short render matrix is dominated by text/normal frame work, so wall-time variation is noise-level: PNG path before/after was full ANSI 24.36s/24.38s, 55.2% normal 14.20s/14.71s, and 100% normal 6.14s/6.53s. Pipe path before/after was full ANSI 23.09s/23.33s, 55.2% normal 13.27s/13.37s, and 100% normal 5.46s/5.63s.
- The long-render win is in interval lookup scale. A simulated 5,276s/126,624-frame render with 1,967 random-normal intervals took 4.323s for the old `is_bypass_time()` scan and 0.028s with the cursor logic, with identical bypass-hit counts.
- Current conclusion: random-normal sections already reduce the expensive ANSI/text cost proportionally. This pass removes avoidable interval-scan overhead for long renders with many random-normal sections, but the dominant remaining cost is still text rendering on the ANSI frames that remain.

## 2026-05-11 - v0.2.0 experimental direct frame-pipe renderer

- Added an experimental desktop render transport behind `WZRDVID_EXPERIMENTAL_FRAME_PIPE=1`. The default path still renders each frame to `frame_%06d.png` and then encodes the PNG sequence. The experimental path generates the same final `Image.Image` frames but writes RGB24 bytes directly into ffmpeg stdin for the silent MP4 encode.
- The pipe path keeps audio mux/mix/source-audio/optimization behavior after silent video creation unchanged. If the pipe encode fails before audio muxing, the renderer logs the failure, removes the partial silent video, and reruns the default PNG-staging path from frame 0.
- Synthetic comparison media lived under `/tmp/wzrdvid-frame-pipe` and was not committed. Test settings used 720x406, 24 fps, 64 text columns, CRF 28, Amber Terminal/PUBLIC ACCESS presets, and common visible effects.

| Case | PNG total | Pipe total | Output validation | Notes |
| --- | ---: | ---: | --- | --- |
| Amber Terminal 5s | 11.78s | 11.24s | 5.000s H.264/yuv420p | pipe avoided PNG staging |
| Amber Terminal 10s | 25.29s | 24.01s | 10.000s H.264/yuv420p | pipe avoided PNG staging |
| PUBLIC ACCESS 10s | 27.52s | 25.72s | 10.000s H.264/yuv420p | pipe avoided PNG staging |
| Amber Terminal 10s + worky audio | 25.65s | 24.13s | 10.000s H.264/yuv420p + AAC | audio mux stayed 0.06s in both modes |
| Amber Terminal 30s | 77.40s | 72.55s | 30.000s H.264/yuv420p | pipe avoided PNG staging |
| 31-minute synthetic source capped to 10s | 22.37s | 20.76s | 10.000s H.264/yuv420p | long-source output stayed bounded |

- A forced pipe failure smoke monkeypatched the raw-frame encoder to raise before audio muxing. The render logged the pipe failure, logged fallback to PNG frame staging, and produced a valid fallback MP4.
- Recommendation: keep the pipe path experimental for v0.2.0. It reduces temp-frame disk pressure and produced modest 5-7% wall-time wins on the matrix, but text rendering remains the dominant cost, so this should not be promoted to default until it is tested against the user's real long render and more real media.

## 2026-05-11 - v0.2.0 frame-render speed profiling

- A temporary `/tmp` profiling harness measured the desktop renderer without committing debug instrumentation. Test outputs used 720x406, 24 fps, 64 text columns, Amber Terminal/PUBLIC ACCESS presets, all common visible effects enabled, and synthetic media under `/tmp/wzrdvid-speed`.
- The dominant cost was ANSI/text rendering, not audio, source duration, PNG staging, or ffmpeg encode. For a 10s Amber Terminal render, total time was 24.41s: frame render 23.48s, `render_text_art_frame()` 16.03s, `ImageDraw.text()` 12.18s, source read/seek 2.05s, PNG writes 1.18s, and ffmpeg PNG-sequence encode 0.84s.
- The 30s Amber Terminal render scaled linearly: total time 73.95s, frame render 71.57s, text rendering 48.52s, text drawing 36.88s, source read/seek 6.75s, PNG writes 3.58s, and encode 2.32s.
- PUBLIC ACCESS 10s was similar but slightly heavier at 26.54s total because its public-access source-prep pass added 5.43s before ANSI rendering.
- Worky external audio stayed bounded: 10s Amber Terminal with worky audio was 24.63s total, with external audio mux taking only 0.06s.
- A capped 10s render from a synthetic 31-minute source was 23.03s total. Source read/seek was 0.43s on that indexed synthetic file, confirming this class of long-source render remains bounded by output frames.
- A low-risk trial to skip drawing literal space glyphs was rejected because it did not improve the measured matrix on bright/test-pattern media: Amber 10s was 24.47s, Amber 30s was 74.16s, PUBLIC ACCESS 10s was 26.71s, worky 10s was 25.05s, and long-source capped 10s was 22.73s. No source optimization was kept.
- Current conclusion: there are no obvious safe v0.2.0 micro-optimizations from this pass. The meaningful speedup remains a future renderer refactor, most likely batching/vectorizing text rendering or piping frames directly to ffmpeg instead of staging PNGs.

## 2026-05-11 - v0.2.0 hue-shift overflow blocker

- A real v0.1.9 packaged long render failed after about 78,001 of 126,624 frames with `OverflowError: Python integer 65536 out of bounds for uint16` in `renderer._hue_shift_image()`.
- The failure was caused by hue-shift arithmetic during frame rendering, not worky audio or final audio muxing. Newer Python/NumPy behavior rejected adding the Python integer `65536` to a `uint16` hue array instead of silently wrapping it.
- The fix keeps hue math in a wider signed integer dtype, applies modulo 256 explicitly, and casts back to `uint8` only after the hue channel is in image range.
- Long renders remain supported. The app should not block long outputs for this issue.
- Full-length renders can still be expensive because WZRD.VID writes one rendered PNG frame per output frame before ffmpeg encodes the MP4. Very long outputs can still use substantial time and temporary disk even when the source is sampled efficiently.

## 2026-05-10 - v0.2.0 long-media audit and conservative hardening

### Audit findings

- Duration and stream metadata flowed through `ffmpeg_utils.probe_media()`, which was uncached before this pass. UI collection, timeline build, source-audio checks, optimization, and recipe fallback paths can ask for the same metadata repeatedly.
- Frame rendering does not intentionally decode full source videos. `renderer._TimelineFrameSource._video_frame()` keeps one `cv2.VideoCapture` per path and seeks by timestamp for each output frame. This keeps short capped outputs bounded by output frame count, but random mode and far-apart seeks can still be slow on long GOP or difficult codecs.
- Render frames are written as PNG files under `TemporaryDirectory(prefix="wzrd_vid_render_")` before ffmpeg encodes the silent MP4. Disk usage grows with output duration, FPS, resolution, and text/effect detail, not directly with source duration.
- Source audio is assembled by `ffmpeg_utils.build_timeline_audio()` as per-segment WAV pieces plus silence pieces, then concatenated to AAC. Random clip assembly can increase the number of short extraction calls.
- External audio mux/mix paths already trim the active span before worky music filters. Worky mode remains external-audio-only and does not process source audio directly.
- Match-to-music can intentionally expand output duration when speed or loop mode uses a long external track. Random clip assembly rejects match-to-music before render.

### Conservative changes made

- Added in-process ffprobe metadata caching keyed by resolved path, file mtime, and file size. Existing helper signatures are unchanged.
- Added render timing logs for probe/planning, frame render, frame encode, source-audio build, audio mix/mux, silent output, and optimization stages.
- Added long-media warnings for video sources or external audio at 30+ minutes, with stronger wording at 60+ minutes.
- Left visual rendering, frame seeking strategy, ffmpeg command structure, worky sound profile, recipe schema, and Lite behavior unchanged.

### Stress environment

- Test media root: `/tmp/wzrdvid-v020-stress`
- Source-run Python: repo `.venv`
- Synthetic media:
  - `short.mp4`: 12 seconds, 160x90, H.264/AAC
  - `long.mp4`: 31:05, 160x90, 1 fps H.264 plus AAC
  - `long_audio.m4a`: 31:05 AAC sine tone
  - `photo.png`: generated still image
- Probe cache smoke: `get_duration`, `has_audio_stream`, `get_video_info`, and `get_audio_duration` on the same file issued 1 ffprobe call total after caching.

### Stress results

| Case | Result | Render time | Output duration | Audio | Notes |
| --- | ---: | ---: | ---: | --- | --- |
| Baseline short render | pass | 0.34s | 3.000s | no | silent output path |
| Long source to 10s | pass | 0.93s | 10.000s | no | long-source warning emitted |
| Long source to 90s | pass | 8.66s | 90.000s | no | long-source warning emitted |
| Long source + photo random 30s | pass | 2.84s | 30.000s | no | random long-seek warning emitted |
| Long source audio only | pass | 0.73s | 6.000s | yes | source audio stage timed |
| Long external audio only | pass | 0.65s | 6.000s | yes | long-audio warning emitted |
| Long external audio with worky mode | pass | 0.61s | 6.000s | yes | worky path stayed bounded by output span |
| External + selected source audio | pass | 0.85s | 6.000s | yes | source build, mix, and mux stages timed |
| Random + source audio | pass | 1.04s | 6.000s | yes | random source-audio path stayed valid |
| Random + match-to-music | pass | 0.00s | n/a | n/a | rejected before render |
| Preview-like 5s segment | pass | 0.54s | 5.000s | no | long-source warning emitted |
| Preview-like 10s segment | pass | 1.02s | 10.000s | no | long-source warning emitted |

### Remaining risks

- OpenCV timestamp seeking is still the most likely long-video bottleneck for random mode on real-world phone footage, long-GOP exports, or codecs with poor seek indexes.
- PNG frame staging is simple and reliable, but very long outputs can still create large temp directories.
- Source-audio random assembly can still become expensive if many short segments are selected from long videos.
- The synthetic stress media is intentionally small and low-resolution; real 4K/60fps or variable-frame-rate footage still needs manual beta testing before a broader v0.2.0 push.

## 2026-05-10 - v0.2.0 real long-media beta pass

### Test media

- Source: local AVI file outside the repo, not committed.
- Container/codecs: AVI, MPEG-4 video, MP3 audio.
- Duration: 1:52:10.01.
- Size: 700.26 MB.
- Video: 608x272 at 23.976 fps.
- Audio: present, 1:52:10.01.
- Probe cache smoke: `get_duration`, `has_audio_stream`, `get_video_info`, and `get_audio_duration` on the same file issued 1 ffprobe call total after caching.

### Results

| Case | Result | Render time | Output duration | Audio | Main stage evidence |
| --- | ---: | ---: | ---: | --- | --- |
| Long source to 10s | pass | 1.02s | 10.000s | no | frame render 0.94s |
| Long source to 90s max | pass | 10.43s | 90.000s | no | frame render 10.04s |
| Long random video + photo 30s | pass | 2.84s | 30.000s | no | frame render 2.70s |
| Source audio only 6s | pass | 0.83s | 6.000s | yes | source audio 0.19s |
| External audio from same AVI 6s | pass | 0.71s | 6.000s | yes | external mux 0.15s |
| worky external audio from same AVI 6s | pass | 0.63s | 6.000s | yes | external mux 0.06s |
| External + selected source audio 6s | pass | 0.98s | 6.000s | yes | source audio 0.19s, mix 0.15s |
| Random + source audio 6s | pass | 1.09s | 6.000s | yes | source audio 0.34s |
| Random + match-to-music | pass | 0.00s | n/a | n/a | rejected before render |
| Preview-like 5s mid-file | pass | 0.58s | 5.000s | no | frame render 0.52s |
| Preview-like 10s mid-file | pass | 1.08s | 10.000s | no | frame render 0.99s |

### Decision

The supplied long AVI did not reveal a v0.2.0 desktop performance blocker. No additional desktop performance fix is required before starting WZRD.VID Lite Apple app packaging groundwork for this tested media class.

Keep the previous caution in place: this does not prove difficult high-resolution phone footage is solved. 4K/60fps, HEVC, variable-frame-rate, rotated phone video, and long-GOP exports still deserve beta coverage if available.
