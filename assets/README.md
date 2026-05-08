# //wzrdVID Assets

`assets/branding/` is the source of truth for the //wzrdVID identity system. It contains the SVG masters, transparent PNG exports, dark/light variants, app icon source, compact/avatar mark, tiny favicon-style slash mark, monochrome mark, and the brand preview sheet.

`assets/logo/` contains compatibility exports used by older app/docs paths. These are refreshed by `scripts/generate_branding.py`.

## GitHub / Release Banners

`assets/logo/wzrdvid-github-banner.png` and `assets/logo/wzrdvid-github-banner-medium.jpeg` are official //wzrdVID banner assets for public repo and distribution surfaces.

Use them for:

- GitHub social preview or repo banner art.
- Website hero/banner graphics on future wzrdgang.com pages.
- Release graphics, social posts, and download-page branding.

The source dimensions are 1280 x 640, which works well for wide social preview cards and can be cropped or scaled for release pages. Prefer the PNG when quality matters and the medium JPEG when a smaller file is useful.

`wzrd_vid_icon.png` and `wzrd_vid.icns` are generated macOS app icon assets derived from `assets/branding/wzrdvid_app_icon_source.png`.

Regenerate branding and icon assets with:

```bash
python3 scripts/generate_branding.py
python3 scripts/generate_icon.py
```
