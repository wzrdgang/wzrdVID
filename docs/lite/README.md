# WZRD.VID Lite

Browser-only 15/30/60-second chaos-cut prototype for the GitHub Pages site.

Privacy rule: user files stay local in the browser. The prototype uses File objects, object URLs, Canvas, Web Audio, and MediaRecorder. It does not upload files or call a server.

Rights note: WZRD.VID Lite is proprietary freeware. Current licensed copies are free for personal, professional, and commercial use, including paid work and monetized output. Do not rehost, repackage, redistribute, submit unauthorized app-store copies, or use the WZRD.VID name/branding for another product except as the WZRD.VID Freeware License permits.

Current export behavior:

- Uses MediaRecorder with MP4 when the browser supports MP4 recording.
- Falls back to WebM when MP4 recording is unavailable.
- In the Apple Lite wrapper, rendered blobs are handed to Swift for local Photos saving because iOS WKWebView download/share handling is not reliable enough by itself.
- Clip length is capped by the selected duration: 15, 30, or 60 seconds.
- Effect Strength offers bounded Low/Medium/High treatment over each existing preset; Medium is the pre-control Lite baseline.
- ANSI Coverage controls random time coverage across the final clip. It is not a gradual intensity ramp: 0% is normal video, 100% is full ANSI/text-art, and values between those build scattered ANSI intervals.
- ANSI Text Density offers bounded Coarse/Standard/Fine glyph grids without changing ANSI Coverage; Standard is the pre-control grid and Fine is capped at 5,600 sampled cells.
- The first usable local medium arms one in-memory project seed from browser cryptographic entropy. Settings/source changes and repeated renders retain it, Reroll Chaos replaces only it, and Clear Project clears it. Named deterministic substreams drive the semantic render plan; the seed is neither uploaded nor persisted.
- The PUBLIC ACCESS preset applies browser-side public-access/VHS source treatment before ANSI Coverage is applied, so 0%, 50%, and 100% ANSI remain meaningful.
- Videos are sampled as random short clips. Images become 1-3 second held/animated segments. Random assembly shuffles through all loaded media before reusing a source, then sources can repeat to fill the selected length.
- Lite targets 30 fps browser recording for Fast 480p and 24 fps for Better 720p while applying browser-side texture: tunnel zoom, punch/wobble, tape/RGB treatment, hard ANSI overlays, short ending fade, and optional added-audio bump.
- The global `Include Source Audio` control defaults on and follows the final assembled visual timeline, including random source ranges. Still/image and silent-video sections contribute source-bus silence. Explicit Add Audio remains separate and can be mixed with source audio into one MediaRecorder track.
- Lite keeps one reusable page-session AudioContext for source mixing. Persistent source-video elements cache their MediaElementSource ownership, while mixed Add Audio is decoded into the same Web Audio graph so iOS does not stop it when a source video begins playback.
- Desktop supports broader ffmpeg-backed formats. Lite depends on the browser's decoder support; HEIC/HEIF and some camera/video containers may be rejected locally with a log message.
- The desktop app remains the full MP4 renderer with deeper timeline, audio, and export controls.

Future work:

- Optional ffmpeg.wasm encoding path for reliable browser MP4.
- More precise audio trimming/mixing controls beyond the current global source switch and Add Audio bus.
- More preset tuning and share-size targets.
