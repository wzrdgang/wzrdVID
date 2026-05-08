# //wzrdVID Assets

`assets/branding/` is the source of truth for the //wzrdVID identity system. It contains the SVG masters, transparent PNG exports, dark/light variants, app icon source, compact/avatar mark, tiny favicon-style slash mark, monochrome mark, and the brand preview sheet.

`assets/logo/` contains compatibility exports used by older app/docs paths. These are refreshed by `scripts/generate_branding.py`.

`wzrd_vid_icon.png` and `wzrd_vid.icns` are generated macOS app icon assets derived from `assets/branding/wzrdvid_app_icon_source.png`.

Regenerate branding and icon assets with:

```bash
python3 scripts/generate_branding.py
python3 scripts/generate_icon.py
```
