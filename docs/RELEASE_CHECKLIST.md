# Release Checklist

Use this before tagging or publishing a public WZRD.VID release.

## Legal / Docs

- [ ] `LICENSE` exists and contains AGPL-3.0.
- [ ] `NOTICE.md` exists and preserves Sam Howell branding ownership language.
- [ ] `THIRD_PARTY_NOTICES.md` lists ffmpeg/ffprobe, PySide6/Qt, OpenCV, Pillow, numpy, and PyInstaller.
- [ ] README has current install, run, build, rights, and media-rights sections.
- [ ] No copyrighted sample media is included.

## Hygiene

- [ ] `.gitignore` excludes virtualenvs, caches, build outputs, rendered media, logs, and temp folders.
- [ ] No local absolute paths are present in source/docs.
- [ ] No stale project names, third-party show references, fantasy-themed copy, or forbidden dither labels remain.
- [ ] No large media files are tracked.

## Verification

```bash
python3 -m py_compile app.py renderer.py ffmpeg_utils.py presets.py theme.py scripts/generate_logo.py scripts/generate_icon.py scripts/generate_ui_textures.py scripts/generate_branding.py
./build_app.sh
```

- [ ] `dist/WZRD.VID.app` exists.
- [ ] Finder-style launch works.
- [ ] Branding assets are bundled.
- [ ] App icon appears correctly in Finder/Dock.

## GitHub Metadata

Suggested description:

```text
//wzrdVID — ANSI motion lab for lo-fi frames and cursed little files.
```

Suggested topics:

```text
video-art, ansi-art, ascii-art, glitch-art, ffmpeg, pyside6, video-effects, creative-tools, lo-fi, compression-art, macos
```
