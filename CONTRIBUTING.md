# Contributing

Thanks for wanting to work on //wzrdVID. The project is meant to stay weird, useful, and readable.

## How To Contribute

- Open focused PRs. A tight fix or one coherent feature is easier to review than a broad rewrite.
- Keep the app responsive. Rendering belongs in worker threads, not the UI thread.
- Preserve the visual identity: pastel pink/mint/black, terminal-mixtape energy, broadcast/print artifacts, readable controls.
- Avoid fantasy, gamer RGB, glossy SaaS, generic AI branding, or corporate-clean redesigns.
- Keep output compatibility in mind: H.264 MP4, `yuv420p`, AAC when audio is present, and `+faststart`.
- Do not add copyrighted sample media. Use placeholders, generated fixtures, or clearly licensed assets.

## Local Checks

Before opening a PR, run:

```bash
python3 -m py_compile app.py renderer.py ffmpeg_utils.py presets.py theme.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py
```

If you touch packaging, also run:

```bash
./build_app.sh
```

## Branding

The source code is AGPL-3.0, but the //wzrdVID name, logos, and visual identity are reserved. Do not ship competing branded builds or imply official endorsement without permission. Forks should use their own identity unless permission is granted.
