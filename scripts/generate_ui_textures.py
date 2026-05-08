"""Generate lightweight WZRD.VID UI texture assets.

The textures are intentionally sparse RGBA overlays. They are used across
decorative surfaces and lightly on controls so the UI feels printed and worn
without losing readability.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    from PIL import Image, ImageDraw, ImageFilter
except ModuleNotFoundError:
    for candidate in (ROOT / ".venv" / "lib").glob("python*/site-packages"):
        sys.path.insert(0, str(candidate))
    from PIL import Image, ImageDraw, ImageFilter

OUT = ROOT / "assets" / "ui"

BLACK = (9, 8, 7)
INK = (22, 17, 15)
PAPER = (255, 243, 222)
OFF_WHITE = (255, 249, 237)
PINK = (246, 184, 212)
HOT_PINK = (255, 127, 185)
MINT = (186, 244, 200)
MINT_DEEP = (117, 217, 146)
DUST_CYAN = (154, 221, 218)
DUST_MAGENTA = (198, 104, 158)

RNG = random.Random(23101996)


def rgba(size: tuple[int, int], color: tuple[int, int, int, int] = (0, 0, 0, 0)) -> Image.Image:
    return Image.new("RGBA", size, color)


def dot(draw: ImageDraw.ImageDraw, x: int, y: int, r: int, color: tuple[int, int, int, int]) -> None:
    draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def add_speckles(draw: ImageDraw.ImageDraw, width: int, height: int, count: int, colors: list[tuple[int, int, int, int]], *, max_r: int = 2) -> None:
    for _ in range(count):
        dot(draw, RNG.randrange(width), RNG.randrange(height), RNG.randrange(1, max_r + 1), RNG.choice(colors))


def paper_noise_tile() -> None:
    w, h = 96, 96
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    add_speckles(
        draw,
        w,
        h,
        320,
        [(*INK, 6), (*BLACK, 5), (*PINK, 14), (*MINT_DEEP, 12), (*OFF_WHITE, 18)],
        max_r=1,
    )
    for _ in range(38):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        length = RNG.randrange(8, 26)
        draw.line((x, y, (x + length) % w, y + RNG.randrange(-2, 3)), fill=(*INK, 4), width=1)
    img.save(OUT / "paper_noise_tile.png", optimize=True)


def mint_pink_speckle() -> None:
    w, h = 420, 180
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for _ in range(34):
        x = RNG.randrange(-40, w + 20)
        y = RNG.randrange(-20, h + 20)
        rx = RNG.randrange(20, 70)
        ry = RNG.randrange(8, 28)
        color = (*MINT, RNG.randrange(10, 22)) if RNG.random() < 0.56 else (*HOT_PINK, RNG.randrange(8, 18))
        draw.ellipse((x, y, x + rx, y + ry), fill=color)
    add_speckles(draw, w, h, 620, [(*BLACK, 7), (*MINT_DEEP, 18), (*HOT_PINK, 16), (*OFF_WHITE, 18)], max_r=2)
    for _ in range(26):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(2, 8), y + RNG.randrange(2, 8)), fill=(*PAPER, 16))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.25))
    img.save(OUT / "mint_pink_speckle.png", optimize=True)


def swoosh(path: Path, base: tuple[int, int, int], accent: tuple[int, int, int]) -> None:
    w, h = 720, 120
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for i in range(7):
        y = 20 + i * 11 + RNG.randrange(-5, 6)
        amp = 18 + i * 2
        points: list[tuple[int, int]] = []
        for x in range(-80, w + 100, 18):
            yy = int(y + math.sin((x / 92.0) + i * 0.7) * amp + (x / w) * 26)
            points.append((x, yy))
        width = RNG.randrange(5, 12)
        draw.line(points, fill=(*base, RNG.randrange(34, 62)), width=width, joint="curve")
        if i % 2 == 0:
            offset = RNG.randrange(5, 12)
            draw.line([(x + offset, yy + offset // 2) for x, yy in points], fill=(*accent, 24), width=max(2, width // 2))
    add_speckles(draw, w, h, 520, [(*BLACK, 12), (*base, 30), (*accent, 28), (*OFF_WHITE, 30)], max_r=2)
    for _ in range(44):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(2, 10), y + RNG.randrange(2, 8)), fill=(*BLACK, RNG.randrange(5, 12)))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.18))
    img.save(path, optimize=True)


def halftone_edge() -> None:
    w, h = 640, 76
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for x in range(0, w, 9):
        for y in range(0, h, 9):
            edge = min(y, h - y)
            if edge > 28 and RNG.random() > 0.18:
                continue
            r = max(1, int(4 - edge / 10 + RNG.random() * 2))
            dot(draw, x + RNG.randrange(-1, 2), y + RNG.randrange(-1, 2), r, (*BLACK, int(max(6, 24 - edge * 0.5))))
    add_speckles(draw, w, h, 260, [(*HOT_PINK, 16), (*MINT_DEEP, 14), (*BLACK, 8)], max_r=1)
    img.save(OUT / "halftone_edge.png", optimize=True)


def block_noise_strip() -> None:
    w, h = 720, 42
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    colors = [(*MINT, 46), (*PINK, 38), (*OFF_WHITE, 34), (*HOT_PINK, 36), (*BLACK, 28)]
    widths = [3, 4, 6, 8, 12, 18]
    heights = [3, 4, 6, 9, 14]
    for x in range(0, w, 12):
        if RNG.random() < 0.48:
            continue
        y = RNG.randrange(3, h - 8)
        draw.rectangle((x, y, min(w, x + RNG.choice(widths)), min(h, y + RNG.choice(heights))), fill=RNG.choice(colors))
    for _ in range(24):
        y = RNG.randrange(h)
        draw.line((0, y, w, y), fill=(*BLACK, RNG.randrange(4, 10)), width=1)
    img.save(OUT / "block_noise_strip.png", optimize=True)


def distressed_corner() -> None:
    w, h = 260, 92
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    # Sparse worn-corner field, strongest at top/right, fading inward.
    for _ in range(240):
        x = int(w - 1 - (RNG.random() ** 2) * w)
        y = int((RNG.random() ** 2) * h)
        alpha = int(max(5, 28 - (x / w) * 7 - y * 0.18))
        color = RNG.choice([(*BLACK, alpha), (*HOT_PINK, alpha + 6), (*MINT_DEEP, alpha + 4), (*OFF_WHITE, alpha + 10)])
        if RNG.random() < 0.28:
            draw.rectangle((x, y, x + RNG.randrange(2, 9), y + RNG.randrange(1, 5)), fill=color)
        else:
            dot(draw, x, y, RNG.randrange(1, 3), color)
    for _ in range(12):
        x = RNG.randrange(w // 2, w)
        y = RNG.randrange(0, h // 2)
        draw.line((x, y, min(w, x + RNG.randrange(18, 80)), y + RNG.randrange(-2, 3)), fill=(*BLACK, RNG.randrange(10, 22)), width=1)
    img.save(OUT / "distressed_corner.png", optimize=True)


def deck_footer_wear() -> None:
    w, h = 760, 34
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    # Broken timing bars and printed hardware wear.
    for x in range(0, w, 18):
        if RNG.random() < 0.36:
            continue
        y = RNG.randrange(7, 22)
        draw.rectangle((x, y, x + RNG.choice([2, 3, 5, 9, 14, 22]), y + RNG.choice([2, 3, 4])), fill=RNG.choice([(*BLACK, 22), (*MINT_DEEP, 28), (*HOT_PINK, 24), (*OFF_WHITE, 28)]))
    for x in range(0, w, 58):
        draw.line((x, 4, x, 12), fill=(*BLACK, 18), width=1)
        if RNG.random() < 0.45:
            draw.line((x + 3, h - 10, x + 3, h - 4), fill=(*HOT_PINK, 18), width=1)
    for _ in range(160):
        dot(draw, RNG.randrange(w), RNG.randrange(h), 1, RNG.choice([(*BLACK, 6), (*PINK, 16), (*MINT, 18)]))
    img.save(OUT / "deck_footer_wear.png", optimize=True)


def registration_marks() -> None:
    w, h = 280, 72
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    # Small misregistered tape ticks and broadcast deck labels. Avoid plus/cross marks.
    colors = [(*BLACK, 40), (*HOT_PINK, 32), (*MINT_DEEP, 32), (*DUST_CYAN, 24)]
    for i, color in enumerate(colors):
        x = 14 + i * 44 + RNG.randrange(-3, 4)
        y = 12 + RNG.randrange(-3, 4)
        draw.rectangle((x, y, x + RNG.randrange(18, 32), y + RNG.randrange(4, 8)), fill=color)
        draw.rectangle((x + RNG.randrange(3, 18), y + RNG.randrange(13, 24), x + RNG.randrange(22, 36), y + RNG.randrange(18, 31)), fill=(*color[:3], max(14, color[3] - 10)))
    for x in range(168, 262, 12):
        y = RNG.randrange(34, 46)
        draw.rectangle((x, y, x + RNG.randrange(3, 8), y + RNG.randrange(8, 24)), fill=RNG.choice([(*BLACK, 22), (*MINT, 30), (*PINK, 30)]))
    for _ in range(16):
        x = RNG.randrange(0, w - 32)
        y = RNG.randrange(5, h - 8)
        draw.line((x, y, x + RNG.randrange(14, 48), y + RNG.randrange(-1, 2)), fill=RNG.choice([(*BLACK, 12), (*HOT_PINK, 18), (*MINT_DEEP, 16)]), width=1)
    add_speckles(draw, w, h, 150, [(*BLACK, 8), (*HOT_PINK, 16), (*MINT_DEEP, 14)], max_r=1)
    img.save(OUT / "registration_marks.png", optimize=True)


def control_patina_tile() -> None:
    w, h = 128, 128
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    add_speckles(
        draw,
        w,
        h,
        560,
        [(*BLACK, 10), (*INK, 8), (*HOT_PINK, 18), (*MINT_DEEP, 18), (*DUST_CYAN, 12), (*OFF_WHITE, 22)],
        max_r=1,
    )
    for _ in range(42):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        length = RNG.randrange(5, 24)
        color = RNG.choice([(*BLACK, 8), (*HOT_PINK, 13), (*MINT_DEEP, 12), (*DUST_MAGENTA, 9)])
        draw.line((x, y, (x + length) % w, y + RNG.randrange(-1, 2)), fill=color, width=1)
    for _ in range(28):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(2, 7), y + RNG.randrange(1, 4)), fill=RNG.choice([(*BLACK, 8), (*HOT_PINK, 14), (*MINT, 16)]))
    img.save(OUT / "control_patina_tile.png", optimize=True)


def button_print_tile() -> None:
    w, h = 180, 72
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for y in (0, h - 4):
        for x in range(0, w, 7):
            if RNG.random() < 0.62:
                draw.rectangle((x, y + RNG.randrange(0, 3), x + RNG.randrange(2, 9), y + RNG.randrange(3, 7)), fill=RNG.choice([(*BLACK, 14), (*HOT_PINK, 24), (*MINT_DEEP, 20), (*OFF_WHITE, 24)]))
    for _ in range(130):
        dot(draw, RNG.randrange(w), RNG.randrange(h), 1, RNG.choice([(*BLACK, 8), (*HOT_PINK, 18), (*MINT_DEEP, 16), (*PAPER, 24)]))
    for _ in range(18):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(3, 15), y + RNG.randrange(2, 8)), fill=RNG.choice([(*BLACK, 9), (*HOT_PINK, 16), (*MINT, 18)]))
    img.save(OUT / "button_print_tile.png", optimize=True)


def table_static_tile() -> None:
    w, h = 240, 160
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for x in range(0, w, 31):
        if RNG.random() < 0.78:
            draw.line((x + RNG.randrange(-1, 2), 0, x + RNG.randrange(-1, 2), h), fill=RNG.choice([(*BLACK, 5), (*HOT_PINK, 10), (*MINT_DEEP, 9)]), width=1)
    for y in range(0, h, 30):
        draw.line((0, y, w, y), fill=(*BLACK, 5), width=1)
    add_speckles(draw, w, h, 360, [(*BLACK, 7), (*HOT_PINK, 13), (*MINT_DEEP, 12), (*OFF_WHITE, 18)], max_r=1)
    for _ in range(34):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(2, 9), y + RNG.randrange(2, 6)), fill=RNG.choice([(*BLACK, 8), (*HOT_PINK, 15), (*MINT, 15)]))
    img.save(OUT / "table_static_tile.png", optimize=True)


def log_static_tile() -> None:
    w, h = 220, 120
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for y in range(0, h, 4):
        draw.line((0, y, w, y), fill=(*MINT, 8), width=1)
    for _ in range(210):
        dot(draw, RNG.randrange(w), RNG.randrange(h), 1, RNG.choice([(*MINT, 18), (*HOT_PINK, 13), (*OFF_WHITE, 9), (*DUST_CYAN, 12)]))
    for _ in range(26):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(2, 13), y + RNG.randrange(1, 5)), fill=RNG.choice([(*MINT, 13), (*HOT_PINK, 11), (*OFF_WHITE, 7)]))
    img.save(OUT / "log_static_tile.png", optimize=True)


def slider_track_texture() -> None:
    w, h = 256, 40
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for x in range(0, w, 16):
        if RNG.random() < 0.52:
            draw.rectangle((x, 14 + RNG.randrange(-2, 3), x + RNG.randrange(2, 10), 22 + RNG.randrange(-1, 3)), fill=RNG.choice([(*BLACK, 12), (*HOT_PINK, 18), (*MINT_DEEP, 18)]))
    for _ in range(170):
        dot(draw, RNG.randrange(w), RNG.randrange(h), 1, RNG.choice([(*BLACK, 7), (*HOT_PINK, 14), (*MINT_DEEP, 14), (*OFF_WHITE, 22)]))
    draw.line((0, h // 2, w, h // 2), fill=(*BLACK, 8), width=1)
    img.save(OUT / "slider_track_texture.png", optimize=True)


def jagged_polyline(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], color: tuple[int, int, int, int], width: int) -> None:
    jittered: list[tuple[int, int]] = []
    for x, y in points:
        jittered.append((x + RNG.randrange(-3, 4), y + RNG.randrange(-3, 4)))
    draw.line(jittered, fill=color, width=width, joint="curve")
    # Break the stroke edges with paper-colored chips so it feels printed, not vector-clean.
    for _ in range(max(10, width * 3)):
        px, py = RNG.choice(jittered)
        x1 = px + RNG.randrange(-width, max(1, width))
        y1 = py + RNG.randrange(-width, max(1, width))
        x2 = x1 + RNG.randrange(2, width + 12)
        y2 = y1 + RNG.randrange(1, max(2, width // 2))
        draw.rectangle((x1, y1, x2, y2), fill=(*PAPER, RNG.randrange(18, 34)))


def add_broadcast_artifacts(draw: ImageDraw.ImageDraw, width: int, height: int, density: int = 1) -> None:
    for _ in range(30 * density):
        y = RNG.randrange(height)
        x = RNG.randrange(width)
        length = RNG.randrange(28, 190)
        draw.line((x, y, min(width, x + length), y + RNG.randrange(-1, 2)), fill=RNG.choice([(*BLACK, 10), (*HOT_PINK, 16), (*MINT_DEEP, 14), (*OFF_WHITE, 20)]), width=1)
    for _ in range(42 * density):
        x = RNG.randrange(width)
        y = RNG.randrange(height)
        draw.rectangle((x, y, x + RNG.randrange(3, 18), y + RNG.randrange(2, 9)), fill=RNG.choice([(*BLACK, 8), (*HOT_PINK, 18), (*MINT, 18), (*DUST_CYAN, 12)]))
    for _ in range(260 * density):
        dot(draw, RNG.randrange(width), RNG.randrange(height), 1, RNG.choice([(*BLACK, 8), (*HOT_PINK, 18), (*MINT_DEEP, 16), (*OFF_WHITE, 24), (*DUST_MAGENTA, 10)]))



def _band_polygon(points: list[tuple[int, int]], width: int, jitter: int) -> list[tuple[int, int]]:
    top: list[tuple[int, int]] = []
    bottom: list[tuple[int, int]] = []
    for index, (x, y) in enumerate(points):
        if index == 0:
            nx, ny = points[1][0] - x, points[1][1] - y
        elif index == len(points) - 1:
            nx, ny = x - points[index - 1][0], y - points[index - 1][1]
        else:
            nx, ny = points[index + 1][0] - points[index - 1][0], points[index + 1][1] - points[index - 1][1]
        length = max(1.0, math.hypot(nx, ny))
        px, py = -ny / length, nx / length
        wobble = width // 2 + RNG.randrange(-jitter, jitter + 1)
        top.append((int(x + px * wobble + RNG.randrange(-jitter, jitter + 1)), int(y + py * wobble + RNG.randrange(-jitter, jitter + 1))))
        bottom.append((int(x - px * wobble + RNG.randrange(-jitter, jitter + 1)), int(y - py * wobble + RNG.randrange(-jitter, jitter + 1))))
    return top + bottom[::-1]


def drybrush_band(
    img: Image.Image,
    points: list[tuple[int, int]],
    color: tuple[int, int, int],
    *,
    alpha: int,
    width: int,
    jitter: int = 28,
    dropout: int = 160,
    overspray: int = 260,
) -> None:
    """Draw a large ripped screen-print band with transparent paint dropout."""
    layer = rgba(img.size)
    draw = ImageDraw.Draw(layer)
    poly = _band_polygon(points, width, jitter)
    draw.polygon(poly, fill=(*color, alpha))

    # Uneven roller passes through the body of the shape.
    for _ in range(9):
        shifted = [(x + RNG.randrange(-18, 19), y + RNG.randrange(-18, 19)) for x, y in points]
        draw.line(shifted, fill=(*color, max(10, alpha // RNG.randrange(3, 6))), width=max(4, width // RNG.randrange(4, 8)))

    # Transparent ripped holes and dry brush dropout.
    min_x = max(0, min(x for x, _ in poly) - 40)
    max_x = min(img.size[0], max(x for x, _ in poly) + 40)
    min_y = max(0, min(y for _, y in poly) - 40)
    max_y = min(img.size[1], max(y for _, y in poly) + 40)
    if max_x > min_x and max_y > min_y:
        for _ in range(dropout):
            x = RNG.randrange(min_x, max_x)
            y = RNG.randrange(min_y, max_y)
            if RNG.random() < 0.42:
                draw.rectangle((x, y, x + RNG.randrange(8, 86), y + RNG.randrange(2, 18)), fill=(0, 0, 0, 0))
            else:
                dot(draw, x, y, RNG.randrange(2, 9), (0, 0, 0, 0))
        for _ in range(overspray):
            x = RNG.randrange(min_x, max_x)
            y = RNG.randrange(min_y, max_y)
            dot(draw, x, y, RNG.randrange(1, 3), (*color, RNG.randrange(10, max(12, alpha // 2))))

    # Stencil-edge chips.
    step = max(1, len(poly) // 48)
    for x, y in poly[::step]:
        x1 = x + RNG.randrange(-22, 23)
        y1 = y + RNG.randrange(-16, 17)
        x2 = x1 + RNG.randrange(18, 92)
        y2 = y1 + RNG.randrange(5, 24)
        draw.rectangle(
            (x1, y1, x2, y2),
            fill=RNG.choice([(*PAPER, RNG.randrange(20, 42)), (0, 0, 0, 0), (*BLACK, RNG.randrange(5, 12))]),
        )
    img.alpha_composite(layer)


def drybrush_burst(
    img: Image.Image,
    origin: tuple[int, int],
    color: tuple[int, int, int],
    *,
    alpha: int,
    radius: int,
    count: int,
    direction: float,
) -> None:
    """Paint a corner explosion made of torn drybrush slashes."""
    ox, oy = origin
    for i in range(count):
        angle = direction + RNG.uniform(-0.62, 0.62)
        length = RNG.randrange(radius // 2, radius)
        start = (
            ox + int(math.cos(angle) * RNG.randrange(0, radius // 5)),
            oy + int(math.sin(angle) * RNG.randrange(0, radius // 5)),
        )
        end = (
            ox + int(math.cos(angle) * length) + RNG.randrange(-70, 71),
            oy + int(math.sin(angle) * length) + RNG.randrange(-46, 47),
        )
        mid = ((start[0] + end[0]) // 2 + RNG.randrange(-80, 81), (start[1] + end[1]) // 2 + RNG.randrange(-46, 47))
        drybrush_band(
            img,
            [start, mid, end],
            color,
            alpha=max(12, alpha - i * 2 + RNG.randrange(-8, 9)),
            width=RNG.randrange(18, 58),
            jitter=RNG.randrange(16, 38),
            dropout=RNG.randrange(32, 90),
            overspray=RNG.randrange(80, 180),
        )



def jazz_backdrop_field() -> None:
    w, h = 1280, 760
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)

    # Broad damaged print events. The target is not dust: it is abused paper-cup ink.
    drybrush_burst(img, (1160, -40), MINT, alpha=64, radius=820, count=7, direction=2.72)
    drybrush_burst(img, (-80, 710), PINK, alpha=48, radius=760, count=5, direction=-0.28)
    drybrush_band(img, [(-180, 120), (380, 34), (860, 210), (1460, 110)], DUST_CYAN, alpha=32, width=118, jitter=42, dropout=190, overspray=260)
    drybrush_band(img, [(-220, 600), (340, 510), (820, 690), (1440, 620)], HOT_PINK, alpha=34, width=150, jitter=52, dropout=230, overspray=340)
    drybrush_band(img, [(120, 810), (520, 675), (1100, 820), (1450, 735)], OFF_WHITE, alpha=46, width=142, jitter=48, dropout=210, overspray=220)

    # Torn stencil geometry crossing the whole surface.
    polygons = [
        [(-160, 64), (440, -28), (720, 94), (310, 230), (-120, 198)],
        [(735, 18), (1360, -42), (1300, 160), (850, 250), (640, 145)],
        [(-120, 520), (420, 430), (720, 560), (120, 690)],
        [(760, 520), (1350, 470), (1450, 710), (880, 700)],
    ]
    for poly in polygons:
        rough = [(x + RNG.randrange(-26, 27), y + RNG.randrange(-22, 23)) for x, y in poly]
        draw.polygon(rough, fill=RNG.choice([(*MINT, 26), (*PINK, 24), (*OFF_WHITE, 36), (*DUST_CYAN, 22)]))
        for _ in range(38):
            x = RNG.randrange(max(0, min(p[0] for p in rough)), min(w, max(p[0] for p in rough) + 1))
            y = RNG.randrange(max(0, min(p[1] for p in rough)), min(h, max(p[1] for p in rough) + 1))
            draw.rectangle((x, y, x + RNG.randrange(10, 90), y + RNG.randrange(3, 18)), fill=(*PAPER, RNG.randrange(18, 38)))

    for _ in range(28):
        x = RNG.randrange(-80, w - 120)
        y = RNG.randrange(0, h)
        draw.rectangle((x, y, x + RNG.randrange(160, 560), y + RNG.randrange(8, 34)), fill=RNG.choice([(*MINT, 20), (*PINK, 24), (*OFF_WHITE, 34), (*DUST_CYAN, 18), (*BLACK, 7)]))
    add_broadcast_artifacts(draw, w, h, density=4)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.05))
    img.save(OUT / "jazz_backdrop_field.png", optimize=True)


def header_broadcast_field() -> None:
    w, h = 1280, 260
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)

    # The header gets the strongest one-corner hit, like a misprinted broadcast card.
    drybrush_burst(img, (1185, -20), MINT, alpha=112, radius=820, count=9, direction=2.72)
    drybrush_band(img, [(610, -42), (930, 30), (1280, -4), (1500, 72)], MINT_DEEP, alpha=78, width=138, jitter=48, dropout=220, overspray=430)
    drybrush_band(img, [(-180, 175), (260, 118), (760, 210), (1330, 162)], PINK, alpha=48, width=154, jitter=56, dropout=230, overspray=360)
    drybrush_band(img, [(-80, 70), (320, 22), (740, 100), (1290, 62)], OFF_WHITE, alpha=34, width=78, jitter=32, dropout=120, overspray=160)

    # Hard-edge awkward clipping and print collision.
    for poly, color in [
        ([(-20, 32), (410, 0), (610, 82), (120, 150)], MINT),
        ([(740, 20), (1320, -24), (1210, 140), (820, 178)], DUST_CYAN),
        ([(95, 180), (510, 145), (700, 252), (180, 282)], HOT_PINK),
    ]:
        rough = [(x + RNG.randrange(-18, 19), y + RNG.randrange(-14, 15)) for x, y in poly]
        draw.polygon(rough, fill=(*color, RNG.randrange(18, 34)))
        for _ in range(26):
            x = RNG.randrange(max(0, min(p[0] for p in rough)), min(w, max(p[0] for p in rough) + 1))
            y = RNG.randrange(max(0, min(p[1] for p in rough)), min(h, max(p[1] for p in rough) + 1))
            draw.rectangle((x, y, x + RNG.randrange(14, 76), y + RNG.randrange(3, 16)), fill=(*PAPER, RNG.randrange(15, 32)))

    for _ in range(72):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.line((x, y, min(w, x + RNG.randrange(28, 260)), y + RNG.randrange(-2, 3)), fill=RNG.choice([(*BLACK, 9), (*HOT_PINK, 18), (*MINT_DEEP, 18), (*OFF_WHITE, 22)]), width=RNG.choice([1, 1, 2]))
    add_broadcast_artifacts(draw, w, h, density=4)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.04))
    img.save(OUT / "header_broadcast_field.png", optimize=True)

def panel_overprint_field() -> None:
    w, h = 920, 360
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for i in range(5):
        base = RNG.choice([MINT, PINK, DUST_CYAN, MINT_DEEP])
        y0 = RNG.randrange(-40, h)
        points = []
        for x in range(-120, w + 160, 30):
            points.append((x, int(y0 + math.sin((x / 115) + i * 0.8) * RNG.randrange(20, 62) + x * RNG.uniform(-0.04, 0.06))))
        jagged_polyline(draw, points, (*base, RNG.randrange(14, 28)), RNG.randrange(10, 26))
    for x in range(0, w, 72):
        if RNG.random() < 0.42:
            draw.line((x, 0, x + RNG.randrange(-6, 7), h), fill=RNG.choice([(*BLACK, 6), (*HOT_PINK, 10), (*MINT_DEEP, 10)]), width=1)
    add_broadcast_artifacts(draw, w, h, density=2)
    img.save(OUT / "panel_overprint_field.png", optimize=True)



def black_bar_broadcast() -> None:
    w, h = 1120, 64
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)

    # Dirty strip material: streaks, paper chips, color bleed, and inconsistent ink density.
    for y in range(0, h, 2):
        draw.line((0, y, w, y), fill=RNG.choice([(*MINT, 16), (*HOT_PINK, 14), (*OFF_WHITE, 8), (*DUST_CYAN, 11), (*BLACK, 0)]), width=1)
    for _ in range(260):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(8, 108), y + RNG.randrange(1, 7)), fill=RNG.choice([(*MINT, 42), (*HOT_PINK, 34), (*OFF_WHITE, 18), (*DUST_CYAN, 28), (*DUST_MAGENTA, 22), (*BLACK, 0)]))
    for _ in range(82):
        x = RNG.randrange(w)
        y = RNG.choice([RNG.randrange(0, 13), RNG.randrange(h - 15, h)])
        draw.rectangle((x, y, x + RNG.randrange(14, 130), y + RNG.randrange(1, 7)), fill=RNG.choice([(*PAPER, 28), (*MINT, 34), (*HOT_PINK, 28), (*OFF_WHITE, 18)]))
    for _ in range(34):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.line((x, y, min(w, x + RNG.randrange(120, 420)), y + RNG.randrange(-1, 2)), fill=RNG.choice([(*PINK, 22), (*MINT, 24), (*OFF_WHITE, 15)]), width=RNG.choice([1, 2, 3]))
    for _ in range(560):
        dot(draw, RNG.randrange(w), RNG.randrange(h), 1, RNG.choice([(*MINT, 22), (*HOT_PINK, 20), (*OFF_WHITE, 12), (*DUST_CYAN, 16)]))
    img.save(OUT / "black_bar_broadcast.png", optimize=True)

def edge_wear_tile() -> None:
    w, h = 320, 120
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for y in list(range(0, 18)) + list(range(h - 18, h)):
        alpha = int(22 - min(y, h - 1 - y))
        if alpha <= 0:
            continue
        for x in range(0, w, RNG.randrange(5, 13)):
            if RNG.random() < 0.55:
                draw.rectangle((x, y, x + RNG.randrange(2, 18), y + 1), fill=RNG.choice([(*BLACK, alpha), (*HOT_PINK, alpha + 8), (*MINT_DEEP, alpha + 6), (*OFF_WHITE, alpha + 8)]))
    for _ in range(260):
        edge = RNG.choice([0, 1, 2, 3])
        if edge == 0:
            x, y = RNG.randrange(w), RNG.randrange(0, 28)
        elif edge == 1:
            x, y = RNG.randrange(w), RNG.randrange(h - 28, h)
        elif edge == 2:
            x, y = RNG.randrange(0, 28), RNG.randrange(h)
        else:
            x, y = RNG.randrange(w - 28, w), RNG.randrange(h)
        dot(draw, x, y, 1, RNG.choice([(*BLACK, 10), (*HOT_PINK, 18), (*MINT_DEEP, 16)]))
    img.save(OUT / "edge_wear_tile.png", optimize=True)


def dense_control_patina_tile() -> None:
    w, h = 128, 128
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    add_speckles(draw, w, h, 860, [(*BLACK, 12), (*INK, 8), (*HOT_PINK, 21), (*MINT_DEEP, 20), (*DUST_CYAN, 14), (*OFF_WHITE, 26)], max_r=1)
    for _ in range(70):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.line((x, y, (x + RNG.randrange(6, 34)) % w, y + RNG.randrange(-1, 2)), fill=RNG.choice([(*BLACK, 9), (*HOT_PINK, 15), (*MINT_DEEP, 14)]), width=1)
    for _ in range(46):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.rectangle((x, y, x + RNG.randrange(2, 9), y + RNG.randrange(1, 5)), fill=RNG.choice([(*BLACK, 9), (*HOT_PINK, 17), (*MINT, 18)]))
    img.save(OUT / "dense_control_patina_tile.png", optimize=True)


def scroll_wear_field() -> None:
    w, h = 96, 520
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    for y in range(0, h, 16):
        draw.rectangle((0, y, RNG.randrange(4, 18), y + RNG.randrange(2, 8)), fill=RNG.choice([(*BLACK, 12), (*HOT_PINK, 20), (*MINT_DEEP, 18)]))
        if RNG.random() < 0.52:
            draw.rectangle((w - RNG.randrange(8, 24), y + RNG.randrange(0, 8), w, y + RNG.randrange(8, 18)), fill=RNG.choice([(*BLACK, 10), (*HOT_PINK, 18), (*MINT, 16)]))
    add_speckles(draw, w, h, 340, [(*BLACK, 8), (*HOT_PINK, 16), (*MINT_DEEP, 14), (*OFF_WHITE, 18)], max_r=1)
    img.save(OUT / "scroll_wear_field.png", optimize=True)



def artifact_surface_field() -> None:
    w, h = 1600, 1040
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)

    # Huge asymmetrical print abuse. One corner should feel physically overprinted.
    drybrush_burst(img, (1510, -35), MINT, alpha=104, radius=1060, count=10, direction=2.64)
    drybrush_burst(img, (-110, 930), HOT_PINK, alpha=62, radius=920, count=7, direction=-0.38)
    drybrush_band(img, [(720, -110), (1060, 36), (1510, -10), (1830, 102)], MINT_DEEP, alpha=72, width=198, jitter=68, dropout=340, overspray=560)
    drybrush_band(img, [(-240, 160), (360, 70), (780, 220), (1510, 125)], DUST_CYAN, alpha=34, width=140, jitter=54, dropout=240, overspray=300)
    drybrush_band(img, [(-260, 645), (300, 535), (810, 735), (1650, 650)], HOT_PINK, alpha=58, width=220, jitter=76, dropout=390, overspray=560)
    drybrush_band(img, [(70, 1050), (520, 835), (1120, 980), (1700, 850)], OFF_WHITE, alpha=54, width=165, jitter=58, dropout=280, overspray=280)
    drybrush_band(img, [(-160, 420), (390, 330), (960, 430), (1760, 350)], PINK, alpha=28, width=115, jitter=42, dropout=210, overspray=260)

    # Hard torn geometric fields. These are low alpha, but the edges are intentionally ugly.
    polys = [
        [(-180, 90), (550, -20), (900, 145), (210, 302), (-150, 230)],
        [(770, 16), (1690, -70), (1490, 220), (790, 282), (610, 140)],
        [(-180, 720), (500, 600), (875, 815), (65, 1000)],
        [(790, 705), (1730, 575), (1630, 940), (900, 1000)],
        [(220, 370), (760, 285), (1080, 392), (540, 500)],
    ]
    for poly in polys:
        rough = [(x + RNG.randrange(-32, 33), y + RNG.randrange(-28, 29)) for x, y in poly]
        draw.polygon(rough, fill=RNG.choice([(*MINT, 30), (*PINK, 32), (*OFF_WHITE, 42), (*DUST_CYAN, 26)]))
        min_x = max(0, min(x for x, _ in rough))
        max_x = min(w, max(x for x, _ in rough))
        min_y = max(0, min(y for _, y in rough))
        max_y = min(h, max(y for _, y in rough))
        if max_x > min_x and max_y > min_y:
            for _ in range(58):
                x = RNG.randrange(min_x, max_x)
                y = RNG.randrange(min_y, max_y)
                draw.rectangle((x, y, x + RNG.randrange(12, 116), y + RNG.randrange(3, 24)), fill=RNG.choice([(*PAPER, 24), (*OFF_WHITE, 28), (*BLACK, 5)]))

    # Collision marks and long tracking wounds crossing section boundaries.
    for _ in range(46):
        x = RNG.randrange(-80, w - 120)
        y = RNG.randrange(0, h)
        draw.rectangle((x, y, x + RNG.randrange(140, 680), y + RNG.randrange(8, 38)), fill=RNG.choice([(*MINT, 24), (*PINK, 28), (*OFF_WHITE, 36), (*DUST_CYAN, 20), (*BLACK, 8)]))
    for _ in range(78):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.line((x, y, min(w, x + RNG.randrange(80, 520)), y + RNG.randrange(-3, 4)), fill=RNG.choice([(*BLACK, 9), (*HOT_PINK, 17), (*MINT_DEEP, 17), (*OFF_WHITE, 20)]), width=RNG.choice([1, 1, 2]))
    add_broadcast_artifacts(draw, w, h, density=5)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.04))
    img.save(OUT / "artifact_surface_field.png", optimize=True)


def panel_surface(path: Path, mood: str) -> None:
    w, h = 1280, 460
    img = rgba((w, h))
    draw = ImageDraw.Draw(img)
    if mood == "mint":
        sweep_colors = [(MINT, 68), (DUST_CYAN, 44), (PINK, 30), (OFF_WHITE, 40)]
        anchor = MINT
    elif mood == "cream":
        sweep_colors = [(OFF_WHITE, 62), (MINT, 44), (PINK, 34), (DUST_CYAN, 26)]
        anchor = OFF_WHITE
    elif mood == "washed":
        sweep_colors = [(PINK, 48), (MINT, 48), (OFF_WHITE, 54), (DUST_MAGENTA, 24)]
        anchor = PINK
    else:
        sweep_colors = [(PINK, 54), (MINT, 54), (OFF_WHITE, 44), (DUST_CYAN, 30)]
        anchor = HOT_PINK

    # Panel interiors get big wounded ink fields, not only dust.
    drybrush_burst(img, (w + 40, -30), anchor, alpha=66, radius=620, count=5, direction=2.6)
    drybrush_band(img, [(-120, 80), (300, 20), (760, 135), (1370, 70)], RNG.choice([MINT, PINK, DUST_CYAN]), alpha=50, width=118, jitter=48, dropout=190, overspray=260)
    drybrush_band(img, [(-160, 330), (300, 250), (760, 380), (1360, 318)], RNG.choice([PINK, MINT, OFF_WHITE]), alpha=54, width=148, jitter=54, dropout=220, overspray=280)

    for i in range(5):
        color, alpha = RNG.choice(sweep_colors)
        y0 = RNG.randrange(-60, h + 40)
        points = []
        for x in range(-160, w + 220, 34):
            points.append((x, int(y0 + math.sin((x / RNG.randrange(145, 240)) + i) * RNG.randrange(28, 88) + x * RNG.uniform(-0.06, 0.08))))
        drybrush_band(img, points, color, alpha=alpha + RNG.randrange(-8, 10), width=RNG.randrange(28, 84), jitter=RNG.randrange(20, 42), dropout=RNG.randrange(80, 160), overspray=RNG.randrange(90, 180))

    for _ in range(32):
        x = RNG.randrange(-30, w)
        y = RNG.randrange(-20, h)
        draw.rectangle((x, y, x + RNG.randrange(60, 270), y + RNG.randrange(7, 38)), fill=RNG.choice([(*OFF_WHITE, 34), (*MINT, 30), (*PINK, 30), (*HOT_PINK, 16), (*BLACK, 6)]))
    for _ in range(50):
        x = RNG.randrange(w)
        y = RNG.randrange(h)
        draw.line((x, y, min(w, x + RNG.randrange(38, 260)), y + RNG.randrange(-2, 3)), fill=RNG.choice([(*BLACK, 10), (*HOT_PINK, 16), (*MINT_DEEP, 14), (*OFF_WHITE, 22)]), width=1)
    add_speckles(draw, w, h, 1050, [(*BLACK, 7), (*HOT_PINK, 14), (*MINT_DEEP, 13), (*OFF_WHITE, 20), (*DUST_CYAN, 10)], max_r=1)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.04))
    img.save(path, optimize=True)

def panel_surface_variants() -> None:
    panel_surface(OUT / "panel_surface_pink.png", "pink")
    panel_surface(OUT / "panel_surface_mint.png", "mint")
    panel_surface(OUT / "panel_surface_cream.png", "cream")
    panel_surface(OUT / "panel_surface_washed.png", "washed")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paper_noise_tile()
    mint_pink_speckle()
    swoosh(OUT / "cup_swoosh_mint.png", MINT, PINK)
    swoosh(OUT / "cup_swoosh_pink.png", PINK, MINT)
    halftone_edge()
    block_noise_strip()
    distressed_corner()
    deck_footer_wear()
    registration_marks()
    slider_track_texture()
    log_static_tile()
    table_static_tile()
    button_print_tile()
    control_patina_tile()
    scroll_wear_field()
    dense_control_patina_tile()
    edge_wear_tile()
    black_bar_broadcast()
    panel_overprint_field()
    header_broadcast_field()
    jazz_backdrop_field()
    panel_surface_variants()
    artifact_surface_field()
    for path in sorted(OUT.glob("*.png")):
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
