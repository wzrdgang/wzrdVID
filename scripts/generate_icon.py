"""Generate WZRD.VID app icon assets from the //wzrdVID mark."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError:
    for candidate in (ROOT / ".venv" / "lib").glob("python*/site-packages"):
        sys.path.insert(0, str(candidate))
    from PIL import Image, ImageDraw, ImageFont


ASSETS = ROOT / "assets"
LOGO_DIR = ASSETS / "logo"
BRAND_DIR = ASSETS / "branding"
ICONSET = ASSETS / "wzrd_vid.iconset"
PNG_PATH = ASSETS / "wzrd_vid_icon.png"
ICNS_PATH = ASSETS / "wzrd_vid.icns"

PINK = (246, 184, 212, 255)
MINT = (186, 244, 200, 255)
BLACK = (9, 8, 7, 255)
HOT_PINK = (255, 127, 185, 255)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    ICONSET.mkdir(exist_ok=True)
    for existing in ICONSET.glob("*.png"):
        existing.unlink()
    source_icon = BRAND_DIR / "wzrdvid_app_icon_source.png"
    if not source_icon.exists():
        source_icon = LOGO_DIR / "wzrdvid_logo_square.png"
    icon = Image.open(source_icon).convert("RGBA") if source_icon.exists() else draw_icon(1024)
    if icon.size != (1024, 1024):
        icon = icon.resize((1024, 1024), Image.Resampling.LANCZOS)
    icon.save(PNG_PATH)
    icon_for_iconset = icon.convert("RGB")

    icon_specs = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    for filename, pixel_size in icon_specs:
        icon_for_iconset.resize((pixel_size, pixel_size), Image.Resampling.LANCZOS).save(
            ICONSET / filename
        )

    icon.save(
        ICNS_PATH,
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512), (1024, 1024)],
    )
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICNS_PATH}")


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    stroke = max(6, int(size * 0.035))
    margin = int(size * 0.07)
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=int(size * 0.16),
        fill=PINK,
        outline=BLACK,
        width=stroke,
    )
    panel = (int(size * 0.14), int(size * 0.17), int(size * 0.86), int(size * 0.56))
    draw.rounded_rectangle(panel, radius=int(size * 0.055), fill=MINT, outline=BLACK, width=stroke)
    slash_w = int(size * 0.055)
    slash_h = int(size * 0.27)
    slash_y = int(size * 0.22)
    for x in (int(size * 0.22), int(size * 0.32)):
        draw.polygon(
            [(x + slash_w, slash_y), (x + slash_w * 2, slash_y), (x + slash_w, slash_y + slash_h), (x, slash_y + slash_h)],
            fill=BLACK,
        )
    draw.rectangle((int(size * 0.40), int(size * 0.20), int(size * 0.45), int(size * 0.25)), fill=HOT_PINK)
    draw.text((int(size * 0.21), int(size * 0.57)), "wzrd", font=load_font(int(size * 0.14)), fill=BLACK)
    draw.text((int(size * 0.50), int(size * 0.705)), "VID", font=load_font(int(size * 0.115)), fill=BLACK)
    draw.rectangle((int(size * 0.20), int(size * 0.86), int(size * 0.80), int(size * 0.895)), fill=BLACK)
    draw.rectangle((int(size * 0.20), int(size * 0.86), int(size * 0.43), int(size * 0.895)), fill=MINT)
    return img


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


if __name__ == "__main__":
    main()
