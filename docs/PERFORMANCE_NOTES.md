# WZRD.VID Performance Notes

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
