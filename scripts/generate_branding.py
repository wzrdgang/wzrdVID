"""Generate the //wzrdVID branding system.

The branding is intentionally a little dirty: tape-label framing, broadcast
registration, low-res block wear, and screen-print misregistration. Assets are
reproducible and exported as transparent PNGs plus lightweight SVG masters.
"""

from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from PIL import Image, ImageDraw, ImageFont
except ModuleNotFoundError:
    for candidate in (ROOT / ".venv" / "lib").glob("python*/site-packages"):
        sys.path.insert(0, str(candidate))
    from PIL import Image, ImageDraw, ImageFont

BRAND_DIR = ROOT / "assets" / "branding"
LOGO_DIR = ROOT / "assets" / "logo"

BLACK = (9, 8, 7, 255)
INK = (22, 17, 15, 255)
PAPER = (255, 243, 222, 255)
OFF_WHITE = (255, 249, 237, 255)
PINK = (246, 184, 212, 255)
HOT_PINK = (255, 127, 185, 255)
MINT = (186, 244, 200, 255)
MINT_DEEP = (117, 217, 146, 255)
DUST_CYAN = (154, 221, 218, 255)
DUST_MAGENTA = (198, 104, 158, 255)
TRANSPARENT = (0, 0, 0, 0)
RNG = random.Random(9291997)


def rgba(size: tuple[int, int], color: tuple[int, int, int, int] = TRANSPARENT) -> Image.Image:
    return Image.new("RGBA", size, color)


def with_alpha(color: tuple[int, int, int, int], alpha: int) -> tuple[int, int, int, int]:
    return (color[0], color[1], color[2], alpha)


def font(size: int, *, condensed: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if mono:
        candidates.extend([
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
        ])
    if condensed:
        candidates.extend([
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Avenir Next Condensed.ttc",
        ])
    candidates.extend([
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ])
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_speckles(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], count: int, palette: list[tuple[int, int, int, int]]) -> None:
    x0, y0, x1, y1 = box
    for _ in range(count):
        x = RNG.randrange(x0, max(x0 + 1, x1))
        y = RNG.randrange(y0, max(y0 + 1, y1))
        r = RNG.choice([1, 1, 1, 2, 3])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=RNG.choice(palette))


def rough_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int, int], outline: tuple[int, int, int, int] = BLACK, width: int = 8, radius: int = 18, wear: bool = True) -> None:
    x0, y0, x1, y1 = box
    shadow = max(2, width // 2)
    draw.rounded_rectangle((x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow), radius=radius, fill=with_alpha(HOT_PINK, 210), outline=outline, width=width)
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    if not wear:
        return
    for _ in range(90):
        edge = RNG.choice(["top", "bottom", "left", "right"])
        if edge == "top":
            x = RNG.randrange(x0, x1)
            y = RNG.randrange(y0, y0 + max(1, width * 3))
        elif edge == "bottom":
            x = RNG.randrange(x0, x1)
            y = RNG.randrange(y1 - max(1, width * 3), y1)
        elif edge == "left":
            x = RNG.randrange(x0, x0 + max(1, width * 3))
            y = RNG.randrange(y0, y1)
        else:
            x = RNG.randrange(x1 - max(1, width * 3), x1)
            y = RNG.randrange(y0, y1)
        draw.rectangle((x, y, x + RNG.randrange(3, 24), y + RNG.randrange(1, 8)), fill=RNG.choice([with_alpha(PAPER, 55), with_alpha(MINT, 45), with_alpha(HOT_PINK, 45), with_alpha(BLACK, 34)]))


def draw_slashes(draw: ImageDraw.ImageDraw, x: int, y: int, h: int, color: tuple[int, int, int, int], scale: float = 1.0) -> int:
    slash_w = int(24 * scale)
    gap = int(22 * scale)
    for i in range(2):
        sx = x + i * (slash_w + gap)
        draw.polygon(
            [
                (sx + slash_w, y),
                (sx + slash_w * 2, y),
                (sx + slash_w, y + h),
                (sx, y + h),
            ],
            fill=color,
        )
    return x + int(2 * (slash_w + gap) + 10 * scale)


def draw_alignment_bits(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], scale: float) -> None:
    x0, y0, x1, y1 = box
    colors = [BLACK, HOT_PINK, MINT_DEEP, DUST_CYAN, OFF_WHITE]
    for i in range(8):
        w = int(RNG.choice([8, 12, 16, 22, 30]) * scale)
        h = int(RNG.choice([5, 7, 10, 14]) * scale)
        x = x1 - int((260 - i * 26) * scale) + RNG.randrange(-4, 5)
        y = y0 + int(32 * scale) + RNG.randrange(-5, 6)
        draw.rectangle((x, y, x + w, y + h), fill=with_alpha(RNG.choice(colors), 230))
    for i in range(6):
        x = x0 + int((58 + i * 18) * scale)
        draw.rectangle((x, y1 - int(35 * scale), x + int(8 * scale), y1 - int(18 * scale)), fill=RNG.choice([BLACK, HOT_PINK, MINT_DEEP]))


def draw_drybrush(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], color: tuple[int, int, int, int], count: int, *, diagonal: bool = True) -> None:
    x0, y0, x1, y1 = box
    for _ in range(count):
        if diagonal:
            x = RNG.randrange(x0 - 80, x1)
            y = RNG.randrange(y0 - 20, y1)
            length = RNG.randrange(80, max(100, x1 - x0))
            height = RNG.randrange(5, 30)
            poly = [
                (x, y + RNG.randrange(-10, 11)),
                (x + length, y + RNG.randrange(-30, 31)),
                (x + length + RNG.randrange(-10, 25), y + height + RNG.randrange(-12, 13)),
                (x + RNG.randrange(-25, 15), y + height + RNG.randrange(-8, 9)),
            ]
            draw.polygon(poly, fill=with_alpha(color, RNG.randrange(22, 58)))
        else:
            x = RNG.randrange(x0, x1)
            y = RNG.randrange(y0, y1)
            draw.rectangle((x, y, x + RNG.randrange(20, 160), y + RNG.randrange(3, 24)), fill=with_alpha(color, RNG.randrange(18, 48)))


def draw_noise_blocks(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], scale: float, amount: int) -> None:
    x0, y0, x1, y1 = box
    colors = [BLACK, HOT_PINK, MINT_DEEP, DUST_CYAN, OFF_WHITE]
    for _ in range(amount):
        x = RNG.randrange(x0, x1)
        y = RNG.randrange(y0, y1)
        w = int(RNG.choice([4, 7, 12, 18, 28, 42]) * scale)
        h = int(RNG.choice([3, 5, 8, 12]) * scale)
        draw.rectangle((x, y, x + w, y + h), fill=with_alpha(RNG.choice(colors), RNG.randrange(35, 130)))


def draw_wordmark_text(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], size: int, *, fill: tuple[int, int, int, int] = BLACK) -> None:
    x, y = xy
    main_font = font(size, condensed=False)
    draw.text((x + max(1, size // 32), y + max(1, size // 28)), text, font=main_font, fill=with_alpha(HOT_PINK, 165))
    draw.text((x - max(1, size // 42), y), text, font=main_font, fill=with_alpha(MINT_DEEP, 115))
    draw.text((x, y), text, font=main_font, fill=fill)


def primary_mark(width: int, height: int, path: Path, *, dark: bool = False, mono: bool = False) -> Image.Image:
    scale = width / 1500
    img = rgba((width, height))
    draw = ImageDraw.Draw(img)
    panel_fill = BLACK if dark else (PAPER if mono else MINT)
    text_fill = PAPER if dark else BLACK
    accent = PAPER if mono else PINK
    shadow = HOT_PINK if not mono else BLACK

    outer = (int(22 * scale), int(38 * scale), width - int(34 * scale), height - int(44 * scale))
    back = (outer[0] + int(18 * scale), outer[1] + int(18 * scale), outer[2] + int(18 * scale), outer[3] + int(18 * scale))
    draw.rounded_rectangle(back, radius=int(26 * scale), fill=with_alpha(shadow, 225), outline=BLACK, width=max(5, int(8 * scale)))
    rough_rect(draw, outer, panel_fill, outline=BLACK, width=max(5, int(8 * scale)), radius=int(28 * scale), wear=True)

    draw_drybrush(draw, (outer[0] + int(20 * scale), outer[1], outer[2], outer[3]), accent, 18, diagonal=True)
    draw_noise_blocks(draw, (outer[0], outer[1], outer[2], outer[3]), scale, 92)
    draw_speckles(draw, outer, 1300, [with_alpha(BLACK, 20), with_alpha(PINK, 32), with_alpha(MINT_DEEP, 30), with_alpha(OFF_WHITE, 40)])

    slash_end = draw_slashes(draw, int(76 * scale), int(78 * scale), int(200 * scale), text_fill, scale=1.08 * scale)
    draw.rectangle((int(68 * scale), int(70 * scale), int(84 * scale), int(260 * scale)), fill=with_alpha(PINK if not mono else BLACK, 210))
    draw_wordmark_text(draw, "wzrdVID", (slash_end + int(18 * scale), int(74 * scale)), int(166 * scale), fill=text_fill)

    small = font(int(27 * scale), condensed=True, mono=True)
    draw.text((slash_end + int(25 * scale), int(260 * scale)), "sam.mode / wzrdgang", font=small, fill=text_fill)
    draw.text((int(930 * scale), int(72 * scale)), "VTR-B // TXT FEED // SYNC 29.97", font=font(int(24 * scale), mono=True), fill=text_fill)
    draw_alignment_bits(draw, outer, scale)
    draw.rectangle((width - int(170 * scale), height - int(84 * scale), width - int(88 * scale), height - int(68 * scale)), fill=text_fill)
    img.save(path)
    return img


def compact_mark(size: int, path: Path, *, dark: bool = False, mono: bool = False) -> Image.Image:
    scale = size / 1024
    img = rgba((size, size))
    draw = ImageDraw.Draw(img)
    fill = BLACK if dark else (PAPER if mono else PINK)
    text_fill = PAPER if dark else BLACK
    accent = MINT if not mono else OFF_WHITE

    rough_rect(draw, (int(62 * scale), int(62 * scale), int(962 * scale), int(962 * scale)), fill, width=max(8, int(34 * scale)), radius=int(145 * scale), wear=True)
    draw_drybrush(draw, (int(68 * scale), int(76 * scale), int(956 * scale), int(940 * scale)), accent, 26, diagonal=True)
    draw_noise_blocks(draw, (int(72 * scale), int(72 * scale), int(952 * scale), int(952 * scale)), scale, 120)
    draw_speckles(draw, (int(80 * scale), int(80 * scale), int(944 * scale), int(944 * scale)), 1700, [with_alpha(BLACK, 20), with_alpha(HOT_PINK, 32), with_alpha(MINT_DEEP, 36), with_alpha(OFF_WHITE, 44)])

    inner = (int(138 * scale), int(145 * scale), int(886 * scale), int(560 * scale))
    rough_rect(draw, inner, MINT if not dark else INK, width=max(6, int(24 * scale)), radius=int(54 * scale), wear=True)
    draw_slashes(draw, int(220 * scale), int(218 * scale), int(252 * scale), text_fill, scale=1.85 * scale)
    draw_wordmark_text(draw, "wzrd", (int(205 * scale), int(580 * scale)), int(150 * scale), fill=text_fill)
    draw_wordmark_text(draw, "VID", (int(510 * scale), int(710 * scale)), int(132 * scale), fill=text_fill)
    draw.rectangle((int(212 * scale), int(880 * scale), int(820 * scale), int(918 * scale)), fill=text_fill)
    draw.rectangle((int(212 * scale), int(880 * scale), int(454 * scale), int(918 * scale)), fill=MINT if not mono else OFF_WHITE)
    draw_alignment_bits(draw, (int(96 * scale), int(90 * scale), int(928 * scale), int(936 * scale)), scale)
    img.save(path)
    return img


def favicon_mark(size: int, path: Path, *, dark: bool = False) -> Image.Image:
    img = rgba((size, size))
    draw = ImageDraw.Draw(img)
    s = size / 128
    fill = BLACK if dark else MINT
    text = PAPER if dark else BLACK
    rough_rect(draw, (int(8 * s), int(10 * s), int(120 * s), int(118 * s)), fill, width=max(2, int(5 * s)), radius=int(17 * s), wear=False)
    draw_slashes(draw, int(25 * s), int(28 * s), int(58 * s), text, scale=0.45 * s)
    draw.rectangle((int(76 * s), int(84 * s), int(106 * s), int(91 * s)), fill=text)
    draw.rectangle((int(90 * s), int(24 * s), int(101 * s), int(34 * s)), fill=HOT_PINK if not dark else PAPER)
    img.save(path)
    return img


def write_svg(path: Path, *, variant: str) -> None:
    if variant == "mono":
        fill = "#fff3de"
        accent = "#090807"
        label = "//wzrdVID monochrome"
    elif variant == "compact":
        fill = "#f6b8d4"
        accent = "#baf4c8"
        label = "//wzrdVID compact"
    else:
        fill = "#baf4c8"
        accent = "#f6b8d4"
        label = "//wzrdVID primary"
    svg = f"""<svg width=\"1500\" height=\"350\" viewBox=\"0 0 1500 350\" xmlns=\"http://www.w3.org/2000/svg\">
  <title>{label}</title>
  <rect x=\"42\" y=\"56\" width=\"1390\" height=\"236\" rx=\"28\" fill=\"#ff7fb9\" stroke=\"#090807\" stroke-width=\"9\"/>
  <rect x=\"24\" y=\"38\" width=\"1390\" height=\"236\" rx=\"28\" fill=\"{fill}\" stroke=\"#090807\" stroke-width=\"9\"/>
  <path d=\"M95 82h30L84 258H54L95 82Z\" fill=\"#090807\"/>
  <path d=\"M148 82h30l-41 176h-30l41-176Z\" fill=\"#090807\"/>
  <rect x=\"68\" y=\"70\" width=\"16\" height=\"190\" fill=\"{accent}\" opacity=\"0.75\"/>
  <text x=\"214\" y=\"210\" font-family=\"Arial Black, Arial, sans-serif\" font-size=\"132\" font-weight=\"900\" fill=\"#75d992\" opacity=\"0.45\">wzrdVID</text>
  <text x=\"220\" y=\"216\" font-family=\"Arial Black, Arial, sans-serif\" font-size=\"132\" font-weight=\"900\" fill=\"#ff7fb9\" opacity=\"0.62\">wzrdVID</text>
  <text x=\"210\" y=\"205\" font-family=\"Arial Black, Arial, sans-serif\" font-size=\"132\" font-weight=\"900\" fill=\"#090807\">wzrdVID</text>
  <text x=\"238\" y=\"270\" font-family=\"Menlo, monospace\" font-size=\"25\" font-weight=\"900\" fill=\"#090807\">sam.mode / wzrdgang</text>
  <text x=\"870\" y=\"84\" font-family=\"Menlo, monospace\" font-size=\"23\" font-weight=\"900\" fill=\"#090807\">VTR-B // TXT FEED // SYNC 29.97</text>
  <rect x=\"1265\" y=\"254\" width=\"82\" height=\"16\" fill=\"#090807\"/>
  <rect x=\"1132\" y=\"70\" width=\"18\" height=\"13\" fill=\"#090807\"/>
  <rect x=\"1164\" y=\"70\" width=\"12\" height=\"13\" fill=\"#ff7fb9\"/>
  <rect x=\"1188\" y=\"70\" width=\"24\" height=\"13\" fill=\"#090807\"/>
  <rect x=\"1228\" y=\"70\" width=\"14\" height=\"13\" fill=\"#baf4c8\"/>
</svg>"""
    path.write_text(svg)


def make_preview_sheet() -> None:
    backgrounds = [("cream", PAPER), ("black", BLACK), ("mint", MINT), ("pink", PINK)]
    variants = [
        ("primary", BRAND_DIR / "wzrdvid_primary.png"),
        ("compact", BRAND_DIR / "wzrdvid_compact.png"),
        ("app icon", BRAND_DIR / "wzrdvid_app_icon_source.png"),
        ("mono", BRAND_DIR / "wzrdvid_mono.png"),
        ("tiny", BRAND_DIR / "wzrdvid_favicon_128.png"),
    ]
    w, h = 1800, 1280
    sheet = Image.new("RGBA", (w, h), PAPER)
    draw = ImageDraw.Draw(sheet)
    title_font = font(38, mono=True)
    label_font = font(22, mono=True)
    draw.text((42, 34), "//wzrdVID BRAND SYSTEM // broadcast-media artifact marks", font=title_font, fill=BLACK)
    cell_w = 320
    cell_h = 270
    for row, (bg_name, bg) in enumerate(backgrounds):
        y = 110 + row * cell_h
        draw.text((38, y + 16), bg_name.upper(), font=label_font, fill=BLACK if bg != BLACK else PINK)
        for col, (name, asset_path) in enumerate(variants):
            x = 160 + col * cell_w
            panel = (x, y, x + 290, y + 220)
            draw.rounded_rectangle(panel, radius=18, fill=bg, outline=BLACK, width=4)
            logo = Image.open(asset_path).convert("RGBA")
            if name in {"primary", "mono"}:
                logo.thumbnail((260, 86), Image.Resampling.LANCZOS)
            elif name in {"compact", "app icon"}:
                logo.thumbnail((142, 142), Image.Resampling.LANCZOS)
            else:
                logo.thumbnail((76, 76), Image.Resampling.LANCZOS)
            sheet.alpha_composite(logo, (x + (290 - logo.width) // 2, y + 28 + (142 - logo.height) // 2))
            draw.text((x + 8, y + 190), name, font=label_font, fill=BLACK if bg != BLACK else MINT)
    sheet.save(BRAND_DIR / "wzrdvid_brand_preview_sheet.png")


def main() -> None:
    BRAND_DIR.mkdir(parents=True, exist_ok=True)
    LOGO_DIR.mkdir(parents=True, exist_ok=True)

    primary_mark(1500, 350, BRAND_DIR / "wzrdvid_primary.png")
    primary_mark(3000, 700, BRAND_DIR / "wzrdvid_primary@2x.png")
    primary_mark(1500, 350, BRAND_DIR / "wzrdvid_primary_dark.png", dark=True)
    primary_mark(1500, 350, BRAND_DIR / "wzrdvid_mono.png", mono=True)
    compact_mark(1024, BRAND_DIR / "wzrdvid_compact.png")
    compact_mark(1024, BRAND_DIR / "wzrdvid_compact_dark.png", dark=True)
    compact_mark(1024, BRAND_DIR / "wzrdvid_app_icon_source.png")
    favicon_mark(128, BRAND_DIR / "wzrdvid_favicon_128.png")
    favicon_mark(64, BRAND_DIR / "wzrdvid_favicon_64.png")
    favicon_mark(32, BRAND_DIR / "wzrdvid_favicon_32.png")
    favicon_mark(16, BRAND_DIR / "wzrdvid_favicon_16.png")
    favicon_mark(128, BRAND_DIR / "wzrdvid_favicon_dark_128.png", dark=True)

    write_svg(BRAND_DIR / "wzrdvid_primary.svg", variant="primary")
    write_svg(BRAND_DIR / "wzrdvid_compact.svg", variant="compact")
    write_svg(BRAND_DIR / "wzrdvid_mono.svg", variant="mono")

    shutil.copyfile(BRAND_DIR / "wzrdvid_primary.png", LOGO_DIR / "wzrdvid_wordmark_header.png")
    shutil.copyfile(BRAND_DIR / "wzrdvid_primary@2x.png", LOGO_DIR / "wzrdvid_wordmark_header@2x.png")
    shutil.copyfile(BRAND_DIR / "wzrdvid_compact.png", LOGO_DIR / "wzrdvid_wordmark_compact.png")
    shutil.copyfile(BRAND_DIR / "wzrdvid_compact.png", LOGO_DIR / "wzrdvid_logo_square.png")
    shutil.copyfile(BRAND_DIR / "wzrdvid_favicon_128.png", LOGO_DIR / "wzrdvid_logo_square_small.png")
    shutil.copyfile(BRAND_DIR / "wzrdvid_primary.svg", LOGO_DIR / "wzrdvid_wordmark.svg")

    make_preview_sheet()
    print(f"Wrote branding assets to {BRAND_DIR}")
    print(f"Wrote compatibility logo exports to {LOGO_DIR}")


if __name__ == "__main__":
    main()
