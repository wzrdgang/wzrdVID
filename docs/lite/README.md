# WZRD.VID Lite

Browser-only 15/30/60-second chaos-cut prototype for the GitHub Pages site.

Privacy rule: user files stay local in the browser. The prototype uses File objects, object URLs, Canvas, Web Audio, and MediaRecorder. It does not upload files or call a server.

Current export behavior:

- Uses MediaRecorder with MP4 when the browser supports MP4 recording.
- Falls back to WebM when MP4 recording is unavailable.
- Clip length is capped by the selected duration: 15, 30, or 60 seconds.
- ANSI Coverage controls random time coverage across the final clip. It is not a gradual intensity ramp: 0% is normal video, 100% is full ANSI/text-art, and values between those build scattered ANSI intervals.
- The PUBLIC ACCESS preset applies browser-side public-access/VHS source treatment before ANSI Coverage is applied, so 0%, 50%, and 100% ANSI remain meaningful.
- Videos are sampled as random short clips. Images become 1-3 second held/animated segments. Sources can be reused to fill the selected length.
- Desktop supports broader ffmpeg-backed formats. Lite depends on the browser's decoder support; HEIC/HEIF and some camera/video containers may be rejected locally with a log message.
- The desktop app remains the full MP4 renderer with deeper timeline, audio, and export controls.

Future work:

- Optional ffmpeg.wasm encoding path for reliable browser MP4.
- More precise audio trimming/mixing controls.
- More preset tuning and share-size targets.
