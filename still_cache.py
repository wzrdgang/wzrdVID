"""Still-image loading and HEIC proxy caching for WZRD.VID."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

import ffmpeg_utils


HEIC_EXTENSIONS = {".heic", ".heif"}
LogCallback = Callable[[str], None] | None


@dataclass(frozen=True)
class StillImage:
    image: Image.Image
    source_size: tuple[int, int]
    proxy_size: tuple[int, int]
    cache_hit: bool
    cache_path: Path | None
    decode_seconds: float
    downscaled: bool


def is_heic_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in HEIC_EXTENSIONS


def still_cache_dir() -> Path:
    override = os.environ.get("WZRDVID_STILL_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "WZRD.VID" / "StillCache"
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "WZRD.VID" / "StillCache"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wzrdvid" / "StillCache"


def load_still_image(path: str | Path, *, max_dimension: int | None = None, log: LogCallback = None) -> StillImage:
    source = Path(path).expanduser()
    started = time.perf_counter()
    if is_heic_path(source):
        return _load_heic_proxy(source, max_dimension=max_dimension, started=started, log=log)

    with Image.open(source) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
    source_size = rgb.size
    downscaled = _downscale_in_place(rgb, max_dimension)
    return StillImage(
        image=rgb,
        source_size=source_size,
        proxy_size=rgb.size,
        cache_hit=False,
        cache_path=None,
        decode_seconds=max(0.0, time.perf_counter() - started),
        downscaled=downscaled,
    )


def managed_still_cache_targets(*, cache_dir: Path | None = None, older_than_seconds: int | None) -> list[Path]:
    root = Path(cache_dir) if cache_dir is not None else still_cache_dir()
    if not root.exists() or not root.is_dir():
        return []
    try:
        if older_than_seconds is None or older_than_seconds <= 0:
            return list(root.iterdir())
    except OSError:
        return []
    cutoff = time.time() - max(0, int(older_than_seconds))
    targets: list[Path] = []
    try:
        children = list(root.rglob("*"))
    except OSError:
        return []
    for child in children:
        if child.is_dir():
            continue
        if _path_is_older_than(child, cutoff):
            targets.append(child)
    return targets


def _load_heic_proxy(
    source: Path,
    *,
    max_dimension: int | None,
    started: float,
    log: LogCallback,
) -> StillImage:
    cache_root = still_cache_dir() / "heic"
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / f"{_cache_key(source, max_dimension)}.png"

    if cache_path.exists():
        with Image.open(cache_path) as image:
            rgb = ImageOps.exif_transpose(image).convert("RGB")
        return StillImage(
            image=rgb,
            source_size=rgb.size,
            proxy_size=rgb.size,
            cache_hit=True,
            cache_path=cache_path,
            decode_seconds=max(0.0, time.perf_counter() - started),
            downscaled=False,
        )

    with tempfile.TemporaryDirectory(prefix="wzrd_heic_decode_") as temp_dir:
        decoded = Path(temp_dir) / "decoded.png"
        ffmpeg_utils.extract_still_frame(source, decoded)
        with Image.open(decoded) as image:
            rgb = ImageOps.exif_transpose(image).convert("RGB")

    source_size = rgb.size
    downscaled = _downscale_in_place(rgb, max_dimension)
    temp_cache = cache_path.with_suffix(".tmp.png")
    rgb.save(temp_cache, format="PNG", optimize=False, compress_level=1)
    temp_cache.replace(cache_path)
    elapsed = max(0.0, time.perf_counter() - started)
    if log:
        detail = f"{source_size[0]}x{source_size[1]}"
        if downscaled:
            detail += f" -> {rgb.size[0]}x{rgb.size[1]}"
        log(f"HEIC/HEIF decode cached: {source.name} ({detail}) in {elapsed:.2f}s.")
    return StillImage(
        image=rgb,
        source_size=source_size,
        proxy_size=rgb.size,
        cache_hit=False,
        cache_path=cache_path,
        decode_seconds=elapsed,
        downscaled=downscaled,
    )


def _downscale_in_place(image: Image.Image, max_dimension: int | None) -> bool:
    if not max_dimension:
        return False
    limit = max(1, int(max_dimension))
    if max(image.size) <= limit:
        return False
    image.thumbnail((limit, limit), _resampling_lanczos())
    return True


def _cache_key(source: Path, max_dimension: int | None) -> str:
    try:
        stat = source.stat()
        mtime_ns = stat.st_mtime_ns
        size = stat.st_size
    except OSError:
        mtime_ns = 0
        size = 0
    payload = "|".join(
        (
            str(source.resolve(strict=False)),
            str(size),
            str(mtime_ns),
            str(max_dimension or "original"),
        )
    )
    return hashlib.sha256(payload.encode("utf-8", errors="surrogateescape")).hexdigest()[:32]


def _path_is_older_than(path: Path, cutoff: float) -> bool:
    try:
        return path.stat().st_mtime < cutoff
    except OSError:
        return False


def _resampling_lanczos() -> int:
    return getattr(getattr(Image, "Resampling", Image), "LANCZOS")
