# WZRD.VID Lite

Browser-only 30-second chaos-cut prototype for the GitHub Pages site.

Privacy rule: user files stay local in the browser. The prototype uses File objects, object URLs, Canvas, Web Audio, and MediaRecorder. It does not upload files or call a server.

Current export behavior:

- Uses MediaRecorder with MP4 when the browser supports MP4 recording.
- Falls back to WebM when MP4 recording is unavailable.
- The desktop app remains the full MP4 renderer.

Future work:

- Optional ffmpeg.wasm encoding path for reliable browser MP4.
- More precise audio trimming/mixing controls.
- More preset tuning and share-size targets.
