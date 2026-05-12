"""PySide6 desktop GUI for WZRD.VID."""

from __future__ import annotations

import html
import json
import os
import platform
import random
import re
import shutil
import ssl
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from app_i18n import SUPPORTED_LANGUAGES, language_label, resolve_language, translate
import cv2
from PIL import Image
from PySide6.QtCore import QThread, QTimer, QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import ffmpeg_utils
import still_cache
from presets import get_preset, preset_description, preset_names
from renderer import (
    AUDIO_EXTERNAL,
    AUDIO_MIX,
    AUDIO_SILENT,
    AUDIO_SOURCE,
    BYPASS_FULL_ANSI,
    BYPASS_MANUAL,
    BYPASS_MANUAL_RANDOM,
    BYPASS_RANDOM,
    MATCH_LOOP,
    MATCH_SPEED,
    MATCH_TRIM,
    RenderSettings,
    TimelineItem,
    build_bypass_intervals,
    fit_frame_to_output,
    render_project,
)
from theme import MONO_FONT_STACK, PALETTE, app_stylesheet


APP_NAME = "WZRD.VID"
APP_SUBTITLE = "ANSI broadcast lab // lo-fi fragment synthesis // public-access hallucinations"
RELEASES_LATEST_URL = "https://github.com/wzrdgang/wzrdVID/releases/latest"
LATEST_RELEASE_API_URL = "https://api.github.com/repos/wzrdgang/wzrdVID/releases/latest"
UPDATE_CHECK_TIMEOUT_SECONDS = 6
RELEASE_TAG_RE = re.compile(r"/releases/tag/([^/?#\"'<>]+)")
APP_VERSION_FALLBACK = "0.1.9"


def _resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _load_app_version() -> str:
    for candidate in (_resource_path("VERSION"), Path(__file__).resolve().parent / "VERSION"):
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value.lstrip("v")
    return APP_VERSION_FALLBACK


def _version_tuple(value: str) -> tuple[int, int, int]:
    clean = value.strip().lstrip("vV").split("-", 1)[0]
    parts: list[int] = []
    for piece in clean.split("."):
        digits = "".join(char for char in piece if char.isdigit())
        parts.append(int(digits or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _is_newer_version(latest: str, current: str) -> bool:
    return _version_tuple(latest) > _version_tuple(current)


class UpdateCheckError(RuntimeError):
    """Raised when the latest release cannot be resolved."""


def _sanitize_update_error(message: object, max_length: int = 260) -> str:
    text = str(message).replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    for value in (str(Path.home()), os.environ.get("USER"), os.environ.get("USERNAME")):
        if value:
            text = text.replace(value, "~")
    if len(text) > max_length:
        return f"{text[: max_length - 1]}..."
    return text or "unknown update-check error"


def _is_ssl_verify_error(exc: BaseException) -> bool:
    current: BaseException | object | None = exc
    while current is not None:
        if isinstance(current, ssl.SSLCertVerificationError):
            return True
        reason = getattr(current, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return True
        text = str(current)
        if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text.lower():
            return True
        current = getattr(current, "__cause__", None)
    return False


def _update_headers(current_version: str, *, json_api: bool) -> dict[str, str]:
    headers = {
        "User-Agent": f"WZRD.VID/{current_version} (+https://github.com/wzrdgang/wzrdVID)",
        "Accept": "application/vnd.github+json" if json_api else "text/html,application/xhtml+xml",
    }
    if json_api:
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    return headers


def _read_update_url(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = UPDATE_CHECK_TIMEOUT_SECONDS,
    context: ssl.SSLContext | None = None,
) -> tuple[str, str]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read(512_000).decode(charset, errors="replace")
            return body, response.geturl()
    except urllib.error.HTTPError as exc:
        body = exc.read(4096).decode("utf-8", errors="replace")
        detail = _sanitize_update_error(body)
        rate_detail = ""
        if exc.code in {403, 429}:
            remaining = exc.headers.get("X-RateLimit-Remaining")
            reset = exc.headers.get("X-RateLimit-Reset")
            rate_detail = f" rate-limit remaining={remaining or '?'} reset={reset or '?'};"
        raise UpdateCheckError(f"HTTP {exc.code};{rate_detail} {detail}") from exc
    except urllib.error.URLError as exc:
        raise UpdateCheckError(_sanitize_update_error(exc.reason or exc)) from exc
    except TimeoutError as exc:
        raise UpdateCheckError("timed out") from exc
    except OSError as exc:
        raise UpdateCheckError(_sanitize_update_error(exc)) from exc


def _read_update_url_with_ssl_fallback(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = UPDATE_CHECK_TIMEOUT_SECONDS,
) -> tuple[str, str, str]:
    try:
        body, final_url = _read_update_url(url, headers, timeout=timeout)
        return body, final_url, ""
    except UpdateCheckError as exc:
        if not _is_ssl_verify_error(exc):
            raise
        try:
            insecure_context = ssl._create_unverified_context()  # noqa: SLF001 - public release metadata fallback only.
            body, final_url = _read_update_url(url, headers, timeout=timeout, context=insecure_context)
            return body, final_url, "certificate verification failed; retried release metadata check without local CA validation"
        except UpdateCheckError as fallback_exc:
            raise UpdateCheckError(
                f"certificate verification failed; fallback also failed: {_sanitize_update_error(fallback_exc)}"
            ) from fallback_exc


def _parse_latest_release_api(body: str) -> tuple[str, str]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise UpdateCheckError(f"invalid JSON response: {_sanitize_update_error(exc)}") from exc
    latest_tag = str(payload.get("tag_name") or "").strip()
    if not latest_tag:
        raise UpdateCheckError("latest release response missing tag_name")
    release_url = str(payload.get("html_url") or RELEASES_LATEST_URL).strip() or RELEASES_LATEST_URL
    return latest_tag, release_url


def _extract_release_tag_from_url(value: str) -> str:
    match = RELEASE_TAG_RE.search(value)
    return match.group(1).strip() if match else ""


def fetch_latest_release_info(current_version: str) -> tuple[str, bool, str, str]:
    errors: list[str] = []
    api_headers = _update_headers(current_version, json_api=True)
    try:
        body, _final_url, warning = _read_update_url_with_ssl_fallback(LATEST_RELEASE_API_URL, api_headers)
        latest_tag, release_url = _parse_latest_release_api(body)
        detail = "GitHub API"
        if warning:
            detail = f"{detail}; {warning}"
        return latest_tag, _is_newer_version(latest_tag, current_version), release_url, detail
    except UpdateCheckError as exc:
        errors.append(f"API: {_sanitize_update_error(exc)}")

    page_headers = _update_headers(current_version, json_api=False)
    try:
        body, final_url, warning = _read_update_url_with_ssl_fallback(RELEASES_LATEST_URL, page_headers)
        latest_tag = _extract_release_tag_from_url(final_url) or _extract_release_tag_from_url(body)
        if not latest_tag:
            raise UpdateCheckError("latest release page did not expose a release tag")
        release_url = f"https://github.com/wzrdgang/wzrdVID/releases/tag/{latest_tag}"
        detail = "GitHub release-page fallback"
        if warning:
            detail = f"{detail}; {warning}"
        return latest_tag, _is_newer_version(latest_tag, current_version), release_url, detail
    except UpdateCheckError as exc:
        errors.append(f"release page: {_sanitize_update_error(exc)}")

    raise UpdateCheckError("; ".join(errors))


APP_VERSION = _load_app_version()


def _user_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "WZRD.VID"
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "WZRD.VID"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "wzrdvid"


def _default_app_font() -> QFont:
    families = set(QFontDatabase.families())
    for family in (
        "Avenir Next",
        "Helvetica Neue",
        "Segoe UI",
        "Noto Sans",
        "Microsoft YaHei",
        "Yu Gothic",
        "Apple SD Gothic Neo",
        "Arial Unicode MS",
        "Arial",
    ):
        if family in families:
            return QFont(family, 13)
    fallback = QFont()
    fallback.setPointSize(13)
    return fallback


SETTINGS_PATH = _user_data_dir() / "settings.json"
PREVIEW_DIR = SETTINGS_PATH.parent / "Previews"
CACHE_CLEANUP_MAX_AGE_DAYS = 7
CACHE_CLEANUP_MAX_AGE_SECONDS = CACHE_CLEANUP_MAX_AGE_DAYS * 24 * 60 * 60
WZRD_TEMP_PREFIXES = (
    "wzrd_vid_render_",
    "wzrd_vid_ffmpeg_pass_",
    "wzrd_heic_decode_",
    "wzrd_heic_preview_",
)
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
APP_ICON_PATH = ASSETS_DIR / "wzrd_vid_icon.png"
LOGO_HEADER_PATH = ASSETS_DIR / "branding" / "wzrdvid_primary.png"
PREVIEW_SECONDS = 5.0
PREVIEW_DURATION_OPTIONS = {
    "5s": 5.0,
    "10s": 10.0,
}
AUDIO_MODES = [AUDIO_SILENT, AUDIO_EXTERNAL, AUDIO_SOURCE, AUDIO_MIX]
MATCH_TIMELINE_MODES = [MATCH_SPEED, MATCH_TRIM, MATCH_LOOP]


@dataclass
class CacheCleanupSummary:
    files: int = 0
    dirs: int = 0
    bytes: int = 0
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    @property
    def items(self) -> int:
        return self.files + self.dirs

    def add(self, other: "CacheCleanupSummary") -> None:
        self.files += other.files
        self.dirs += other.dirs
        self.bytes += other.bytes
        self.errors.extend(other.errors or [])


def format_cache_size(byte_count: int) -> str:
    size = float(max(0, byte_count))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.1f} TB"


def preview_cache_usage(
    *,
    preview_dir: Path = PREVIEW_DIR,
    temp_dir: Path | None = None,
    still_cache_dir: Path | None = None,
    temp_age_seconds: int = CACHE_CLEANUP_MAX_AGE_SECONDS,
) -> CacheCleanupSummary:
    summary = CacheCleanupSummary()
    for path in _managed_preview_cache_targets(preview_dir, older_than_seconds=None):
        summary.add(_path_usage(path))
    for path in still_cache.managed_still_cache_targets(cache_dir=still_cache_dir, older_than_seconds=None):
        summary.add(_path_usage(path))
    for path in _managed_temp_targets(temp_dir=temp_dir, older_than_seconds=temp_age_seconds):
        summary.add(_path_usage(path))
    return summary


def clear_preview_cache(
    *,
    preview_dir: Path = PREVIEW_DIR,
    temp_dir: Path | None = None,
    still_cache_dir: Path | None = None,
    preview_age_seconds: int = 0,
    still_age_seconds: int | None = None,
    temp_age_seconds: int = CACHE_CLEANUP_MAX_AGE_SECONDS,
    delete_path: Callable[[Path], None] | None = None,
) -> CacheCleanupSummary:
    delete_path = delete_path or _delete_cache_path
    summary = CacheCleanupSummary()
    if still_age_seconds is None:
        still_age_seconds = preview_age_seconds
    targets = list(_managed_preview_cache_targets(preview_dir, older_than_seconds=preview_age_seconds))
    targets.extend(
        still_cache.managed_still_cache_targets(
            cache_dir=still_cache_dir,
            older_than_seconds=still_age_seconds,
        )
    )
    targets.extend(_managed_temp_targets(temp_dir=temp_dir, older_than_seconds=temp_age_seconds))
    for path in targets:
        usage = _path_usage(path)
        try:
            delete_path(path)
        except Exception as exc:  # noqa: BLE001 - cleanup is best-effort.
            summary.errors.append(f"{path}: {exc}")
            continue
        summary.files += usage.files
        summary.dirs += usage.dirs
        summary.bytes += usage.bytes
    return summary


def _managed_preview_cache_targets(preview_dir: Path, *, older_than_seconds: int | None) -> list[Path]:
    root = Path(preview_dir).expanduser()
    if not root.exists() or not root.is_dir():
        return []
    cutoff = _cache_cutoff(older_than_seconds)
    targets: list[Path] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    for child in children:
        if cutoff is not None and not _path_is_older_than(child, cutoff):
            continue
        targets.append(child)
    return targets


def _managed_temp_targets(*, temp_dir: Path | None, older_than_seconds: int) -> list[Path]:
    root = Path(temp_dir) if temp_dir is not None else Path(tempfile.gettempdir())
    if not root.exists() or not root.is_dir():
        return []
    cutoff = _cache_cutoff(older_than_seconds)
    targets: list[Path] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    for child in children:
        if not child.name.startswith(WZRD_TEMP_PREFIXES):
            continue
        if cutoff is not None and not _path_is_older_than(child, cutoff):
            continue
        targets.append(child)
    return targets


def _cache_cutoff(age_seconds: int | None) -> float | None:
    if age_seconds is None:
        return None
    return time.time() - max(0, int(age_seconds))


def _path_is_older_than(path: Path, cutoff: float) -> bool:
    try:
        return path.stat().st_mtime < cutoff
    except OSError:
        return False


def _path_usage(path: Path) -> CacheCleanupSummary:
    summary = CacheCleanupSummary()
    try:
        if path.is_symlink() or path.is_file():
            summary.files = 1
            summary.bytes = path.lstat().st_size
            return summary
        if path.is_dir():
            summary.dirs = 1
            for root, dirs, files in os.walk(path, followlinks=False):
                summary.dirs += len(dirs)
                for name in files:
                    child = Path(root) / name
                    try:
                        summary.files += 1
                        summary.bytes += child.lstat().st_size
                    except OSError as exc:
                        summary.errors.append(f"{child}: {exc}")
            return summary
    except OSError as exc:
        summary.errors.append(f"{path}: {exc}")
    return summary


def _delete_cache_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


RESOLUTIONS = [
    ("960 x 540", (960, 540)),
    ("1280 x 720", (1280, 720)),
    ("1920 x 1080", (1920, 1080)),
    ("2560 x 1440", (2560, 1440)),
]
OUTPUT_SIZE_PRESETS = {
    "Full Quality": {
        "max_width": 1280,
        "fps": 24,
        "crf": 22,
        "audio_kbps": 128,
        "video_kbps_hint": 4200,
        "description": "Full-detail 720p ANSI output with a quality-first H.264 encode.",
    },
    "Text Message Small": {
        "max_width": 540,
        "fps": 18,
        "crf": 32,
        "audio_kbps": 64,
        "video_kbps_hint": 620,
        "description": "Compact texting preset that trades frame rate and sharpness for much smaller files.",
    },
    "Text Message Tiny": {
        "max_width": 360,
        "fps": 15,
        "crf": 35,
        "audio_kbps": 48,
        "video_kbps_hint": 260,
        "description": "Lowest-size texting preset for short clips when delivery matters more than detail.",
    },
    "Social Share": {
        "max_width": 720,
        "fps": 24,
        "crf": 28,
        "audio_kbps": 96,
        "video_kbps_hint": 1350,
        "description": "Balanced 720-wide H.264 output for sharing without the huge full-quality file.",
    },
    "Custom": {
        "max_width": 540,
        "fps": 18,
        "crf": 32,
        "audio_kbps": 64,
        "video_kbps_hint": 620,
        "description": "Manual max width, FPS, CRF, audio bitrate, and optional target size.",
    },
}
OPTIMIZE_PRESETS = {
    "29 MB Text Limit": {
        "target_mb": 29.0,
        "max_width": 540,
        "fps": 18,
        "crf": 32,
        "audio_kbps": 64,
        "description": "One-click texting target that writes a separate optimized file under 29 MB when possible.",
    },
    "32 MB Sweet Spot": {
        "target_mb": 32.0,
        "max_width": 720,
        "fps": 24,
        "crf": 26,
        "audio_kbps": 96,
        "description": "Balanced 720-wide, 24 fps, CRF 26 quality target with a 32 MB cap.",
    },
    "50 MB Better Quality": {
        "target_mb": 50.0,
        "max_width": 960,
        "fps": 24,
        "crf": 24,
        "audio_kbps": 128,
        "description": "Higher-quality share target that still keeps the final MP4 bounded.",
    },
    "Custom": {
        "target_mb": 29.0,
        "description": "Use the current Output Size settings and your own max MB target.",
    },
}
EFFECTS = [
    ("ken_burns", "Ken Burns", "Slow source motion for stills and clips."),
    ("tunnel_zoom", "Tunnel Zoom", "Loops a slow push-in, then snaps back to wide like a busted tape zoom."),
    ("punch_zoom", "Punch Zooms", "Short impact zooms on a repeating pulse."),
    ("glitch", "Glitch", "Horizontal offsets, slice jumps, and damaged-frame shifts."),
    ("rgb_split", "RGB Split", "Offsets color channels for cheap-video separation."),
    ("color_drift", "Color Drift", "Slow hue movement through the render."),
    ("scanlines", "Scanlines", "CRT-style line darkening."),
    ("char_noise", "Random Character Noise", "Random character replacement in ANSI frames."),
    ("vhs_wobble", "VHS Wobble", "Subtle analog line wobble and rotation."),
    ("boost", "Contrast/Saturation Boost", "Harder contrast and stronger source color."),
    ("stutter_hold", "Stutter Hold", "Occasionally freezes video for 2-8 frames while audio continues."),
    ("motion_melt", "Motion Melt", "Datamosh-lite frame persistence and smeared motion drag."),
    ("terminal_scroll", "Terminal Scroll Drift", "Subtle vertical crawl like old terminal overflow."),
    ("tape_damage", "Tape Damage", "Horizontal tears, dropouts, and luma dents."),
    ("mosaic_collapse", "Mosaic Collapse", "Impact moments collapse into chunky compression blocks."),
    ("audio_reactive", "Audio Reactive Hits", "Lets the audio trigger punch zooms, RGB splits, and glitch bursts."),
]
DEFAULT_OFF_EFFECTS = {
    "tunnel_zoom",
    "stutter_hold",
    "motion_melt",
    "terminal_scroll",
    "tape_damage",
    "mosaic_collapse",
    "audio_reactive",
}
DEFAULT_TRANSITION_MODE = "CRT Flash"
DEFAULT_ENDING_MODE = "Fade Out"
FIT_MODES = ["Fill/Crop", "Fit/Letterbox", "Smart Portrait", "Stretch"]
ANCHORS = ["Center", "Top", "Bottom", "Left", "Right"]
LETTERBOX_BACKGROUNDS = ["Black", "Pastel Pink", "Blurred Source"]
DITHER_MODES = ["None", "Bayer", "Floyd-Steinberg", "CRT dot matrix", "Pocket Camera", "Newspaper halftone"]
TRANSITION_MODES = [
    "Hard Cut",
    "CRT Flash",
    "Frame Burn",
    "Block Dissolve",
    "VHS Roll",
    "Terminal Wipe",
    "RGB Burst",
    "Buffer Underrun",
    "Corrupted Carryover",
    "Random",
]
ENDING_MODES = [
    "Hard Cut",
    "Fade Out",
    "VHS Collapse",
    "Loop Freeze",
    "Seamless Loop",
    "CRT Shutdown",
    "Buffer Exhausted",
]
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mts", ".m2ts", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".aiff", ".aif"}
AUDIO_CONTAINER_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
HEIC_EXTENSIONS = {".heic", ".heif"}
BATCH_VARIANTS = [
    "29 MB Text Limit",
    "32 MB Sweet Spot",
    "Classic ANSI",
    "Chunkcore",
    "WZRD Blocks",
    "Dial-Up Neon",
    "Custom Current Settings",
]
BATCH_SUFFIXES = {
    "29 MB Text Limit": "wzrd_29mb",
    "32 MB Sweet Spot": "wzrd_32mb",
    "Classic ANSI": "wzrd_classic",
    "Chunkcore": "wzrd_chunkcore",
    "WZRD Blocks": "wzrd_blocks",
    "Dial-Up Neon": "wzrd_dialup",
    "Custom Current Settings": "wzrd_custom",
}


def is_image_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in PHOTO_EXTENSIONS


def is_video_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def is_audio_container_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in AUDIO_CONTAINER_EXTENSIONS


def media_kind(path: str | Path) -> str | None:
    suffix = Path(path).suffix.lower()
    if suffix in PHOTO_EXTENSIONS:
        return "photo"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return None


def has_audio_stream(path: str | Path) -> bool:
    return ffmpeg_utils.has_audio_stream(path)


def _drop_file_paths(event) -> list[str]:  # noqa: ANN001 - Qt event type varies by handler.
    mime = event.mimeData()
    if not mime.hasUrls():
        return []
    paths: list[str] = []
    for url in mime.urls():
        if url.isLocalFile():
            local_path = url.toLocalFile()
            if local_path:
                paths.append(local_path)
    return paths


def _refresh_drop_style(widget: QWidget, active: bool) -> None:
    widget.setProperty("dropActive", active)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class MediaDropTableWidget(QTableWidget):
    files_dropped = Signal(list)

    def __init__(self, rows: int, columns: int, accepted_kinds: set[str]) -> None:
        super().__init__(rows, columns)
        self.accepted_kinds = accepted_kinds
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)

    def _accepts_paths(self, paths: list[str]) -> bool:
        return any(media_kind(path) in self.accepted_kinds for path in paths)

    def dragEnterEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        paths = _drop_file_paths(event)
        if paths:
            _refresh_drop_style(self, self._accepts_paths(paths))
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        paths = _drop_file_paths(event)
        if paths:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        _refresh_drop_style(self, False)
        event.accept()

    def dropEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        paths = _drop_file_paths(event)
        _refresh_drop_style(self, False)
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        event.ignore()


class MediaDropLineEdit(QLineEdit):
    files_dropped = Signal(list)

    def __init__(self, accepted_kinds: set[str]) -> None:
        super().__init__()
        self.accepted_kinds = accepted_kinds
        self.setAcceptDrops(True)

    def _accepts_paths(self, paths: list[str]) -> bool:
        return any(media_kind(path) in self.accepted_kinds for path in paths)

    def dragEnterEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        paths = _drop_file_paths(event)
        if paths:
            _refresh_drop_style(self, self._accepts_paths(paths))
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        paths = _drop_file_paths(event)
        if paths:
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        _refresh_drop_style(self, False)
        event.accept()

    def dropEvent(self, event) -> None:  # noqa: N802, ANN001 - Qt signature.
        paths = _drop_file_paths(event)
        _refresh_drop_style(self, False)
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        event.ignore()


class RenderThread(QThread):
    progress_changed = Signal(int)
    log_message = Signal(str)
    render_finished = Signal(str)
    render_failed = Signal(str)

    def __init__(self, settings: RenderSettings) -> None:
        super().__init__()
        self.settings = settings

    def run(self) -> None:
        try:
            output_path = render_project(
                self.settings,
                progress=self.progress_changed.emit,
                log=self.log_message.emit,
            )
        except Exception as exc:  # noqa: BLE001 - GUI should surface all failures.
            self.log_message.emit(traceback.format_exc())
            self.render_failed.emit(str(exc))
            return
        self.render_finished.emit(output_path)


class BatchRenderThread(QThread):
    progress_changed = Signal(int)
    log_message = Signal(str)
    render_finished = Signal(str)
    render_failed = Signal(str)
    variant_changed = Signal(str, int, int)

    def __init__(self, variants: list[tuple[str, RenderSettings]]) -> None:
        super().__init__()
        self.variants = variants
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        outputs: list[str] = []
        total = len(self.variants)
        try:
            for index, (name, settings) in enumerate(self.variants, start=1):
                if self._cancel_requested:
                    raise RuntimeError("Batch canceled by user.")
                self.variant_changed.emit(name, index, total)
                self.log_message.emit(f"--- Variant {index}/{total}: {name} ---")

                def progress(value: int) -> None:
                    if self._cancel_requested:
                        raise RuntimeError("Batch canceled by user.")
                    self.progress_changed.emit(value)

                output_path = render_project(settings, progress=progress, log=self.log_message.emit)
                outputs.append(output_path)
            self.render_finished.emit("\n".join(outputs))
        except Exception as exc:  # noqa: BLE001 - GUI should surface all failures.
            self.log_message.emit(traceback.format_exc())
            self.render_failed.emit(str(exc))


class UpdateCheckThread(QThread):
    update_checked = Signal(str, bool, str, str)
    update_failed = Signal(str)

    def __init__(self, current_version: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_version = current_version

    def run(self) -> None:
        try:
            latest_tag, is_newer, release_url, detail = fetch_latest_release_info(self.current_version)
            self.update_checked.emit(latest_tag, is_newer, release_url, detail)
        except UpdateCheckError as exc:
            self.update_failed.emit(_sanitize_update_error(exc))


class CacheCleanupThread(QThread):
    cleanup_finished = Signal(object, bool)

    def __init__(
        self,
        *,
        manual: bool,
        preview_age_seconds: int,
        temp_age_seconds: int = CACHE_CLEANUP_MAX_AGE_SECONDS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manual = manual
        self.preview_age_seconds = preview_age_seconds
        self.temp_age_seconds = temp_age_seconds

    def run(self) -> None:
        summary = clear_preview_cache(
            preview_age_seconds=self.preview_age_seconds,
            temp_age_seconds=self.temp_age_seconds,
        )
        self.cleanup_finished.emit(summary, self.manual)


class ManualBlockRow(QWidget):
    remove_requested = Signal(object)
    changed = Signal()

    def __init__(
        self,
        start: str = "0:12",
        end: str = "0:18",
        translator: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__()
        self._translator = translator or (lambda key: translate("en", key))
        self.start_label = QLabel()
        self.start_field = QLineEdit(start)
        self.end_label = QLabel()
        self.end_field = QLineEdit(end)
        self.remove_button = QPushButton()
        self.remove_button.setObjectName("dangerButton")

        self.start_field.setPlaceholderText("0:12")
        self.end_field.setPlaceholderText("0:18")
        self.start_field.textChanged.connect(self.changed.emit)
        self.end_field.textChanged.connect(self.changed.emit)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_field)
        layout.addWidget(self.end_label)
        layout.addWidget(self.end_field)
        layout.addWidget(self.remove_button)
        self.apply_i18n(self._translator)

    def values(self) -> tuple[str, str]:
        return self.start_field.text().strip(), self.end_field.text().strip()

    def apply_i18n(self, translator: Callable[[str], str]) -> None:
        self._translator = translator
        self.start_label.setText(translator("label.start"))
        self.end_label.setText(translator("label.end"))
        self.remove_button.setText(translator("button.remove"))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: RenderThread | BatchRenderThread | None = None
        self.update_worker: UpdateCheckThread | None = None
        self.cache_cleanup_worker: CacheCleanupThread | None = None
        self.timeline_items: list[dict[str, object]] = []
        self._timeline_table_updating = False
        self.video_duration_seconds: float | None = None
        self.audio_duration_seconds: float | None = None
        self.random_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.weird_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.block_rows: list[ManualBlockRow] = []
        self.last_output_path: str | None = None
        self.last_preview_path: str | None = None
        self.last_render_error = ""
        self.active_task = "render"
        self._chunky_auto = False
        self.signal_status_label: QLabel | None = None
        self.ui_language = "system"
        self._updating_language_combo = False
        self._i18n_text_widgets: list[tuple[object, str]] = []
        self._i18n_tooltip_widgets: list[tuple[QWidget, str]] = []
        self._i18n_group_boxes: list[tuple[QGroupBox, str]] = []
        self._signal_message_keys = [
            "signal.locked",
            "signal.ghost",
            "signal.clean",
            "signal.source",
        ]
        self._signal_index = 0
        self.latest_release_url = RELEASES_LATEST_URL

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.resize(1080, 700)

        self.video_path = QLineEdit()
        self.language_combo = QComboBox()
        self._populate_language_combo()
        self.video_duration = self._label("status.timeline_none")
        self.timeline_table = MediaDropTableWidget(0, 6, {"video", "photo"})
        self._apply_timeline_headers()
        self.timeline_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.timeline_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.timeline_table.setAlternatingRowColors(True)
        self.timeline_table.setMinimumHeight(132)
        self.timeline_table.verticalHeader().setDefaultSectionSize(30)
        self.timeline_table.verticalHeader().setMinimumWidth(34)
        self.timeline_table.horizontalHeader().setMinimumSectionSize(72)
        self.timeline_table.setObjectName("timelineTable")
        self.add_videos_button = self._button("button.add_videos")
        self.add_videos_button.setObjectName("secondaryButton")
        self.add_photos_button = self._button("button.add_photos")
        self.add_photos_button.setObjectName("secondaryButton")
        self.remove_source_button = self._button("button.remove")
        self.remove_source_button.setObjectName("dangerButton")
        self.move_source_up_button = self._button("button.up")
        self.move_source_up_button.setObjectName("secondaryButton")
        self.move_source_down_button = self._button("button.down")
        self.move_source_down_button.setObjectName("secondaryButton")
        self.clear_sources_button = self._button("button.clear_all")
        self.clear_sources_button.setObjectName("dangerButton")
        self.shuffle_sources_button = self._button("button.shuffle")
        self.shuffle_sources_button.setObjectName("secondaryButton")
        self.preview_source_button = self._button("button.preview_selected")
        self.preview_source_button.setObjectName("secondaryButton")
        for button, minimum_width in (
            (self.add_videos_button, 120),
            (self.add_photos_button, 120),
            (self.remove_source_button, 88),
            (self.move_source_up_button, 56),
            (self.move_source_down_button, 72),
            (self.shuffle_sources_button, 88),
            (self.clear_sources_button, 96),
            (self.preview_source_button, 152),
        ):
            button.setMinimumWidth(minimum_width)
        self.audio_path = MediaDropLineEdit({"audio", "video"})
        self.audio_path.setObjectName("audioPath")
        self._register_tooltip(self.audio_path, "tooltip.audio_path")
        self.audio_duration = self._label("status.duration_empty")
        self.worky_music_mode = self._checkbox("check.worky_music")
        self._register_tooltip(self.worky_music_mode, "tooltip.worky_music")
        self.audio_mode = QComboBox()
        self.audio_mode.addItems(AUDIO_MODES)
        self._register_tooltip(self.audio_mode, "tooltip.audio_mode")
        self.match_timeline_to_audio = self._checkbox("check.match_music")
        self._register_tooltip(self.match_timeline_to_audio, "tooltip.match_timeline")
        self.match_timeline_mode = QComboBox()
        self.match_timeline_mode.addItems(MATCH_TIMELINE_MODES)
        self._register_tooltip(self.match_timeline_mode, "tooltip.match_timeline_mode")
        self.output_path = QLineEdit()

        self.video_start = QLineEdit("0:00")
        self.video_end = QLineEdit("auto")
        self.audio_start = QLineEdit("0:00")
        self.audio_end = QLineEdit("auto")
        self.audio_timeline_start = QLineEdit("0:00")
        self.audio_timeline_end = QLineEdit("auto")
        self._register_tooltip(self.audio_timeline_start, "tooltip.audio_timeline_start")
        self._register_tooltip(self.audio_timeline_end, "tooltip.audio_timeline_end")
        for field in (self.video_start, self.video_end, self.audio_start, self.audio_end, self.audio_timeline_start, self.audio_timeline_end):
            field.setPlaceholderText("0:00, 1:40, 100, 12.5, or auto")
        self.max_video_length = QLineEdit()
        self.max_video_length.setMinimumWidth(112)
        self._register_tooltip(self.max_video_length, "tooltip.max_video_length")
        self.random_clip_assembly = self._checkbox("check.random_clip_assembly")
        self._register_tooltip(self.random_clip_assembly, "tooltip.random_clip_assembly")

        self.preset = QComboBox()
        self.preset.addItems(preset_names())
        for index in range(self.preset.count()):
            description = preset_description(self.preset.itemText(index))
            self.preset.setItemData(index, description, Qt.ItemDataRole.ToolTipRole)
        self.preset_description = QLabel()
        self.preset_description.setObjectName("presetDescription")
        self.preset_description.setWordWrap(True)
        self.style_preview = QLabel()
        self.style_preview.setObjectName("stylePreview")
        self.style_preview.setTextFormat(Qt.TextFormat.RichText)
        self.style_preview.setWordWrap(True)
        self.chunky_blocks = self._checkbox("check.chunky_blocks")
        self._register_tooltip(self.chunky_blocks, "tooltip.chunky_blocks")
        self.effect_checks: dict[str, QCheckBox] = {}
        for key, label, tooltip in EFFECTS:
            checkbox = QCheckBox(label)
            checkbox.setToolTip(tooltip)
            checkbox.setChecked(key not in DEFAULT_OFF_EFFECTS)
            self.effect_checks[key] = checkbox

        self.width_slider, self.width_value = self._make_slider(24, 260, 120)
        self.fps_slider, self.fps_value = self._make_slider(1, 60, 24)
        self.intensity_slider, self.intensity_value = self._make_slider(0, 100, 65)
        self.resolution_slider, self.resolution_value = self._make_slider(0, len(RESOLUTIONS) - 1, 1)
        self.framing_x_slider, self.framing_x_value = self._make_slider(-100, 100, 0)
        self.framing_y_slider, self.framing_y_value = self._make_slider(-100, 100, 0)
        self.framing_zoom_slider, self.framing_zoom_value = self._make_slider(0, 100, 0)
        self.transition_intensity_slider, self.transition_intensity_value = self._make_slider(0, 100, 55)

        self.fit_mode = QComboBox()
        self.fit_mode.addItems(FIT_MODES)
        self._register_tooltip(self.fit_mode, "tooltip.fit_mode")
        self.anchor_mode = QComboBox()
        self.anchor_mode.addItems(ANCHORS)
        self._register_tooltip(self.anchor_mode, "tooltip.anchor_mode")
        self.letterbox_background = QComboBox()
        self.letterbox_background.addItems(LETTERBOX_BACKGROUNDS)
        self._register_tooltip(self.letterbox_background, "tooltip.letterbox_background")
        self.upper_bias = self._checkbox("check.upper_bias")
        self._register_tooltip(self.upper_bias, "tooltip.upper_bias")
        self.upper_bias.setChecked(True)
        self.dither_mode = QComboBox()
        self.dither_mode.addItems(DITHER_MODES)
        self._register_tooltip(self.dither_mode, "tooltip.dither_mode")
        self.transition_mode = QComboBox()
        self.transition_mode.addItems(TRANSITION_MODES)
        self._set_combo_text(self.transition_mode, DEFAULT_TRANSITION_MODE)
        self._register_tooltip(self.transition_mode, "tooltip.transition_mode")
        self.ending_mode = QComboBox()
        self.ending_mode.addItems(ENDING_MODES)
        self._set_combo_text(self.ending_mode, DEFAULT_ENDING_MODE)
        self._register_tooltip(self.ending_mode, "tooltip.ending_mode")
        self.loop_friendly = self._checkbox("check.loop_friendly")
        self._register_tooltip(self.loop_friendly, "tooltip.loop_friendly")
        self.reroll_weirdness_button = self._button("button.reroll_weirdness")
        self.reroll_weirdness_button.setObjectName("secondaryButton")
        self._register_tooltip(self.reroll_weirdness_button, "tooltip.reroll_weirdness")
        self.weird_seed_label = QLabel(self.tr("status.weird_seed", seed=self.weird_seed))
        self.weird_seed_label.setObjectName("estimate")

        self.output_size_preset = QComboBox()
        self.output_size_preset.addItems(list(OUTPUT_SIZE_PRESETS.keys()))
        for index in range(self.output_size_preset.count()):
            name = self.output_size_preset.itemText(index)
            self.output_size_preset.setItemData(
                index,
                OUTPUT_SIZE_PRESETS[name]["description"],
                Qt.ItemDataRole.ToolTipRole,
            )
        self.output_size_description = QLabel()
        self.output_size_description.setObjectName("presetDescription")
        self.output_size_description.setWordWrap(True)
        self.max_width_spin = QSpinBox()
        self.max_width_spin.setRange(240, 2560)
        self.max_width_spin.setSingleStep(20)
        self.max_width_spin.setSuffix(" px")
        self.output_fps_spin = QSpinBox()
        self.output_fps_spin.setRange(1, 60)
        self.output_fps_spin.setSuffix(" fps")
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(14, 40)
        self.audio_bitrate_spin = QSpinBox()
        self.audio_bitrate_spin.setRange(32, 320)
        self.audio_bitrate_spin.setSingleStep(16)
        self.audio_bitrate_spin.setSuffix(" kbps")
        self.target_size_enabled = self._checkbox("check.target_size")
        self.optimize_preset = QComboBox()
        self.optimize_preset.addItems(list(OPTIMIZE_PRESETS.keys()))
        for index in range(self.optimize_preset.count()):
            name = self.optimize_preset.itemText(index)
            self.optimize_preset.setItemData(
                index,
                OPTIMIZE_PRESETS[name]["description"],
                Qt.ItemDataRole.ToolTipRole,
            )
        self.optimize_description = QLabel()
        self.optimize_description.setObjectName("presetDescription")
        self.optimize_description.setWordWrap(True)
        self.target_size_mb = QDoubleSpinBox()
        self.target_size_mb.setRange(0.5, 500.0)
        self.target_size_mb.setDecimals(1)
        self.target_size_mb.setSingleStep(0.5)
        self.target_size_mb.setSuffix(" MB")
        self.target_size_mb.setValue(29.0)
        self.target_size_mb.setEnabled(False)
        self.estimated_size_label = self._label("status.estimated_add_source")
        self.estimated_size_label.setObjectName("estimate")
        self.optimize_estimate_label = self._label("status.optimize_disabled")
        self.optimize_estimate_label.setObjectName("estimate")
        self.final_size_label = self._label("status.final_size_empty")
        self.final_size_label.setObjectName("estimate")
        self.update_status_label = QLabel(self.tr("status.update_checking", version=APP_VERSION))
        self.update_status_label.setObjectName("estimate")
        self.check_update_button = self._button("button.check_update")
        self.check_update_button.setObjectName("secondaryButton")
        self._register_tooltip(self.check_update_button, "tooltip.check_update")
        self.download_update_button = self._button("button.download_update")
        self.download_update_button.setObjectName("secondaryButton")
        self._register_tooltip(self.download_update_button, "tooltip.download_update")
        self.download_update_button.setEnabled(False)
        self.download_update_button.hide()
        self._register_tooltip(self.max_width_spin, "tooltip.max_width")
        self._register_tooltip(self.output_fps_spin, "tooltip.output_fps")
        self._register_tooltip(self.crf_spin, "tooltip.crf")
        self._register_tooltip(self.audio_bitrate_spin, "tooltip.audio_bitrate")
        self._register_tooltip(self.target_size_mb, "tooltip.target_size")
        for spinbox in (
            self.max_width_spin,
            self.output_fps_spin,
            self.crf_spin,
            self.audio_bitrate_spin,
            self.target_size_mb,
        ):
            spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spinbox.setMinimumWidth(112)


        self.bypass_mode = QComboBox()
        self.bypass_mode.addItems(
            [BYPASS_FULL_ANSI, BYPASS_RANDOM, BYPASS_MANUAL, BYPASS_MANUAL_RANDOM]
        )
        self.random_percent = QSpinBox()
        self.random_percent.setRange(0, 100)
        self.random_percent.setValue(10)
        self.random_percent.setSuffix("%")
        self.reroll_button = self._button("button.reroll_random")
        self.reroll_button.setObjectName("secondaryButton")
        self.coverage_bar = QLabel(self.tr("status.coverage_full"))
        self.coverage_detail = QLabel(self.tr("status.coverage_detail", count=0))
        self.seed_label = QLabel(self.tr("status.seed", seed=self.random_seed))
        self.add_block_button = self._button("button.add_block")
        self.add_block_button.setObjectName("secondaryButton")
        self.manual_blocks_widget = QWidget()
        self.manual_blocks_layout = QVBoxLayout(self.manual_blocks_widget)
        self.manual_blocks_layout.setContentsMargins(0, 0, 0, 0)
        self.manual_blocks_layout.setSpacing(8)

        self.preview_label = self._label("status.no_video")
        self.preview_label.setObjectName("preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setFixedSize(184, 104)

        self.start_button = self._button("button.make_video")
        self.start_button.setObjectName("makeButton")
        self.preview_button = QPushButton()
        self.preview_button.setObjectName("secondaryButton")
        self.preview_duration = QComboBox()
        self.preview_duration.addItems(PREVIEW_DURATION_OPTIONS.keys())
        self._register_tooltip(self.preview_duration, "tooltip.preview_duration")
        self.preview_from = QComboBox()
        self.preview_from.addItems(["Start", "Middle", "Custom timestamp"])
        self.preview_custom = QLineEdit("0:00")
        self.preview_custom.setPlaceholderText("0:00, 1:40, or 12.5")
        self.preview_custom.setEnabled(False)
        self.open_preview_button = self._button("button.open_preview")
        self.open_preview_button.setObjectName("secondaryButton")
        self.open_preview_button.setEnabled(False)
        self.open_preview_button.hide()
        self.clear_preview_cache_button = self._button("button.clear_preview_cache")
        self.clear_preview_cache_button.setObjectName("secondaryButton")
        self._register_tooltip(self.clear_preview_cache_button, "tooltip.clear_preview_cache")
        self.save_project_button = self._button("button.export_recipe")
        self.save_project_button.setObjectName("secondaryButton")
        self._register_tooltip(self.save_project_button, "tooltip.export_recipe")
        self.load_project_button = self._button("button.import_recipe")
        self.load_project_button.setObjectName("secondaryButton")
        self._register_tooltip(self.load_project_button, "tooltip.import_recipe")
        self.reset_project_button = self._button("button.reset_project")
        self.reset_project_button.setObjectName("dangerButton")
        self._register_tooltip(self.reset_project_button, "tooltip.reset_project")
        self.open_output_button = self._button("button.open_output")
        self.open_output_button.setObjectName("secondaryButton")
        self.open_output_button.setEnabled(False)
        self.open_output_button.hide()
        self.copy_report_button = self._button("button.copy_report")
        self.copy_report_button.setObjectName("secondaryButton")
        self._register_tooltip(self.copy_report_button, "tooltip.copy_report")
        self.experimental_frame_pipe = self._checkbox("check.experimental_frame_pipe")
        self.experimental_frame_pipe.setObjectName("experimentalToggle")
        self._register_tooltip(self.experimental_frame_pipe, "tooltip.experimental_frame_pipe")
        self.batch_enabled = self._checkbox("check.batch")
        self.batch_checks: dict[str, QCheckBox] = {}
        for variant in BATCH_VARIANTS:
            checkbox = QCheckBox(variant)
            checkbox.setChecked(variant in {"29 MB Text Limit", "Chunkcore"})
            self.batch_checks[variant] = checkbox
        self.batch_button = self._button("button.make_batch")
        self.batch_button.setObjectName("makeButton")
        self.cancel_batch_button = self._button("button.cancel_batch")
        self.cancel_batch_button.setObjectName("dangerButton")
        self.cancel_batch_button.setEnabled(False)
        self.batch_status_label = self._label("status.batch_off")
        self.batch_status_label.setObjectName("estimate")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_output.setMinimumHeight(180)

        self._build_layout()
        self._connect_signals()
        self._apply_style()
        self._load_settings()
        self._refresh_slider_labels()
        self._apply_output_size_preset()
        self._apply_optimize_preset()
        self._update_preset_description()
        self._update_coverage_controls()
        self._after_timeline_changed(save=False)
        self._update_coverage_summary()
        self._start_signal_timer()
        QTimer.singleShot(250, self.check_media_tools)
        QTimer.singleShot(1400, lambda: self.check_for_updates(manual=False))
        QTimer.singleShot(1800, self.start_auto_preview_cache_cleanup)

    def active_language(self) -> str:
        return resolve_language(self.ui_language)

    def tr(self, key: str, **values: object) -> str:
        return translate(self.active_language(), key, **values)

    def _register_text(self, widget: object, key: str) -> object:
        self._i18n_text_widgets.append((widget, key))
        if hasattr(widget, "setText"):
            widget.setText(self.tr(key))
        return widget

    def _register_tooltip(self, widget: QWidget, key: str) -> None:
        self._i18n_tooltip_widgets.append((widget, key))
        widget.setToolTip(self.tr(key))

    def _label(self, key: str) -> QLabel:
        return self._register_text(QLabel(), key)  # type: ignore[return-value]

    def _button(self, key: str) -> QPushButton:
        return self._register_text(QPushButton(), key)  # type: ignore[return-value]

    def _checkbox(self, key: str) -> QCheckBox:
        return self._register_text(QCheckBox(), key)  # type: ignore[return-value]

    def _group_box(self, key: str) -> QGroupBox:
        group = QGroupBox()
        self._i18n_group_boxes.append((group, key))
        group.setTitle(self.tr(key))
        return group

    def _populate_language_combo(self) -> None:
        current = self.ui_language
        self._updating_language_combo = True
        self.language_combo.clear()
        active = self.active_language()
        for code, _name in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(language_label(code, active), code)
        index = self.language_combo.findData(current)
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)
        self._updating_language_combo = False

    def _language_changed(self) -> None:
        if self._updating_language_combo:
            return
        code = str(self.language_combo.currentData() or "system")
        if code == self.ui_language:
            return
        self.ui_language = code
        self._apply_translations()
        self._save_settings()
        self.append_log(self.tr("log.language_changed", selected_language=language_label(code, self.active_language())))

    def _apply_timeline_headers(self) -> None:
        self.timeline_table.setHorizontalHeaderLabels(
            [
                self.tr("table.file"),
                self.tr("table.type"),
                self.tr("table.duration"),
                self.tr("table.trim_start"),
                self.tr("table.end_hold"),
                self.tr("table.include_audio"),
            ]
        )

    def _apply_translations(self) -> None:
        self._populate_language_combo()
        for widget, key in self._i18n_text_widgets:
            if hasattr(widget, "setText"):
                widget.setText(self.tr(key))
        for widget, key in self._i18n_tooltip_widgets:
            widget.setToolTip(self.tr(key))
        for group, key in self._i18n_group_boxes:
            group.setTitle(self.tr(key))
        self._apply_timeline_headers()
        if hasattr(self, "main_tabs"):
            self.main_tabs.setTabText(0, self.tr("tab.source"))
            self.main_tabs.setTabText(1, self.tr("tab.style"))
            self.main_tabs.setTabText(2, self.tr("tab.output"))
        for row in self.block_rows:
            row.apply_i18n(lambda key: self.tr(key))
        self._update_preview_controls()
        self._update_timeline_duration_label()
        self._refresh_slider_labels()
        self._update_audio_controls()
        self._update_output_size_estimate()
        self._update_optimize_estimate()
        self._update_coverage_summary()
        self._refresh_timeline_table()
        self._refresh_signal_status()
        if self.update_worker is None:
            self.update_status_label.setText(self.tr("status.update_checking", version=APP_VERSION))

    def _start_signal_timer(self) -> None:
        self._rotate_signal_status()
        self.signal_timer = QTimer(self)
        self.signal_timer.setInterval(7200)
        self.signal_timer.timeout.connect(self._rotate_signal_status)
        self.signal_timer.start()

    def _rotate_signal_status(self) -> None:
        if self.signal_status_label is None:
            return
        message_key = self._signal_message_keys[self._signal_index % len(self._signal_message_keys)]
        self._signal_index += 1
        self._set_signal_status(message_key)

    def _refresh_signal_status(self) -> None:
        if self.signal_status_label is None:
            return
        index = max(0, self._signal_index - 1) % len(self._signal_message_keys)
        self._set_signal_status(self._signal_message_keys[index])

    def _set_signal_status(self, message_key: str) -> None:
        if self.signal_status_label is None:
            return
        # Tiny static texture on the status strip, kept away from editable controls.
        blocks = random.choice(("░▒▓", "▓▒░", "█░█", "▒▒//"))
        self.signal_status_label.setText(f"{self.tr(message_key)}  {blocks}")

    def _make_slider(self, minimum: int, maximum: int, value: int) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        label = QLabel(str(value))
        label.setMinimumWidth(72)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return slider, label

    def _build_layout(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        layout.addWidget(self._build_header())

        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("mainTabs")
        self.main_tabs.addTab(
            self._tab_scroll([
                self._build_file_group(),
                self._build_trim_group(),
                self._build_framing_group(),
            ]),
            self.tr("tab.source"),
        )
        self.main_tabs.addTab(
            self._tab_scroll([
                self._build_style_group(),
                self._build_slider_group(),
                self._build_coverage_group(),
                self._build_transition_group(),
                self._build_ending_group(),
            ]),
            self.tr("tab.style"),
        )
        output_tab = QWidget()
        output_tab.setObjectName("tabSurface")
        output_layout = QVBoxLayout(output_tab)
        output_layout.setContentsMargins(8, 12, 8, 8)
        output_layout.setSpacing(10)
        output_layout.addWidget(self._pixel_strip("░▒▓ //// OUTPUT DECK //// exports / batch / tape log //// ▓▒░"))
        output_layout.addWidget(self._artifact_strip("TC 00:00:00:00 //// EXPORT BUS //// dropout budget: LOW //// ░░ ▒ █"))
        output_layout.addWidget(self._build_output_size_group())
        output_layout.addWidget(self._build_optimize_group())
        output_layout.addWidget(self._build_batch_group())
        output_layout.addWidget(self._build_output_group())
        log_row = QHBoxLayout()
        log_label = self._label("label.session_log")
        log_label.setObjectName("subtitle")
        log_row.addWidget(log_label)
        log_row.addStretch(1)
        log_row.addWidget(self.copy_report_button)
        output_layout.addLayout(log_row)
        output_layout.addWidget(self.log_output, stretch=1)
        output_layout.addStretch(1)
        self.main_tabs.addTab(self._scroll_widget(output_tab), self.tr("tab.output"))

        layout.addWidget(self.main_tabs, stretch=1)
        self.setCentralWidget(root)

    def _tab_scroll(self, groups: list[QWidget]) -> QScrollArea:
        tab = QWidget()
        tab.setObjectName("tabSurface")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self._pixel_strip("░▒▓ //// CONTROL DECK //// signal / blocks / ghost frames //// ▓▒░"))
        layout.addWidget(self._artifact_strip("CH 03 //// TEXTMODE FEED //// tracking: locked //// ░  ░▒  ▓"))
        for group in groups:
            layout.addWidget(group)
        layout.addStretch(1)
        return self._scroll_widget(tab)

    def _pixel_strip(self, text: str) -> QLabel:
        strip = QLabel(text)
        strip.setObjectName("pixelStrip")
        strip.setWordWrap(False)
        return strip

    def _artifact_strip(self, text: str) -> QLabel:
        strip = QLabel(text)
        strip.setObjectName("artifactStrip")
        strip.setWordWrap(False)
        return strip

    def _dead_zone_strip(self, width: int = 220, height: int = 22) -> QLabel:
        strip = QLabel()
        strip.setObjectName("deadZoneStrip")
        strip.setFixedSize(width, height)
        return strip

    def _deck_footer(self, text: str) -> QLabel:
        footer = QLabel(text)
        footer.setObjectName("deckFooter")
        footer.setWordWrap(False)
        footer.setFixedHeight(24)
        return footer

    def _registration_cluster(self) -> QLabel:
        cluster = QLabel()
        cluster.setObjectName("cornerStatic")
        cluster.setFixedSize(180, 34)
        return cluster

    def _surface_wear_row(self, text: str, *, right_cluster: bool = True) -> QWidget:
        row = QWidget()
        row.setObjectName("decorRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._deck_footer(text), stretch=1)
        if right_cluster:
            layout.addWidget(self._registration_cluster())
        return row

    def _scroll_widget(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerPanel")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(6)

        ruler = QLabel("FRAME 00:00:00:00 //// CH-03 //// WZRD.VID CONTROL FEED //// ░░▒▒▓▓ //// NO DROPOUT")
        ruler.setObjectName("rulerStrip")
        ruler.setWordWrap(False)
        layout.addWidget(ruler)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)
        logo = QLabel("//wzrdVID")
        logo.setObjectName("logoImage")
        logo.setFixedHeight(74)
        if LOGO_HEADER_PATH.exists():
            pixmap = QPixmap(str(LOGO_HEADER_PATH)).scaledToHeight(70, Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
        badge = QLabel("worky.mode / wzrdgang")
        badge.setObjectName("headerBadge")
        badge.setFixedSize(220, 68)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        static_field = QLabel("//// VTR-B  TXT FEED  ////  SYNC 29.97  ////\n░░   ▒▒▓   ░  ▄▀  ░░    █░   EDGE BLEED")
        static_field.setObjectName("staticField")
        static_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        static_field.setFixedHeight(64)

        top_row.addWidget(logo)
        top_row.addWidget(static_field, stretch=1)
        top_row.addWidget(badge)
        layout.addLayout(top_row)

        header_wear = QHBoxLayout()
        header_wear.setContentsMargins(0, 0, 0, 0)
        header_wear.addStretch(1)
        header_wear.addWidget(self._dead_zone_strip(320, 24))
        layout.addLayout(header_wear)

        swoosh = QLabel()
        swoosh.setObjectName("swooshBand")
        swoosh.setFixedHeight(26)
        layout.addWidget(swoosh)

        subtitle = self._label("app.subtitle")
        subtitle.setObjectName("tagline")
        layout.addWidget(subtitle)

        lab_line = QLabel(f"{self.tr('signal.locked')}  ░▒▓")
        lab_line.setObjectName("terminalStrip")
        self.signal_status_label = lab_line
        layout.addWidget(lab_line)

        brand_blocks = QLabel("▓▓ // worky.mode / wzrdgang ▒▒ copy-of-copy deck ░░ lo-fi mp4 bus >> █░█░▒▓")
        brand_blocks.setObjectName("brandBlocks")
        layout.addWidget(brand_blocks)

        utility_row = QHBoxLayout()
        utility_row.setSpacing(8)
        language_label = self._label("language.label")
        language_label.setObjectName("muted")
        utility_row.addWidget(language_label)
        self.language_combo.setMinimumWidth(168)
        utility_row.addWidget(self.language_combo)
        utility_row.addStretch(1)
        self.update_status_label.setMinimumWidth(260)
        utility_row.addWidget(self.update_status_label, stretch=1)
        utility_row.addWidget(self.check_update_button)
        utility_row.addWidget(self.download_update_button)
        layout.addLayout(utility_row)
        return header

    def _build_file_group(self) -> QGroupBox:
        group = self._group_box("group.sources")
        group.setObjectName("sourcePanel")
        layout = QVBoxLayout(group)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        for button in (
            self.add_videos_button,
            self.add_photos_button,
            self.remove_source_button,
            self.move_source_up_button,
            self.move_source_down_button,
            self.shuffle_sources_button,
            self.clear_sources_button,
        ):
            top_row.addWidget(button)
        top_row.addStretch(1)
        top_row.addWidget(self.preview_source_button)
        layout.addLayout(top_row)

        source_row = QHBoxLayout()
        source_row.setSpacing(12)
        source_row.addWidget(self.timeline_table, stretch=1)
        source_row.addWidget(self.preview_label)
        layout.addLayout(source_row)

        timeline_note = self._label("note.timeline")
        timeline_note.setObjectName("muted")
        timeline_note.setWordWrap(True)
        layout.addWidget(timeline_note)
        layout.addWidget(self.video_duration)

        music_row = QGridLayout()
        music_button = self._button("button.select_music")
        music_button.setObjectName("secondaryButton")
        self._register_tooltip(music_button, "tooltip.select_music")
        clear_music_button = self._button("button.clear")
        clear_music_button.setObjectName("dangerButton")
        music_button.clicked.connect(self.select_audio)
        clear_music_button.clicked.connect(self.clear_audio)
        music_row.addWidget(music_button, 0, 0)
        music_row.addWidget(self.audio_path, 0, 1)
        music_row.addWidget(clear_music_button, 0, 2)
        music_row.addWidget(self.audio_duration, 1, 1, 1, 2)
        music_row.addWidget(self.worky_music_mode, 2, 1, 1, 2)
        music_row.setColumnStretch(1, 1)
        layout.addLayout(music_row)
        layout.addWidget(self._surface_wear_row("SOURCE BUS // VTR-A // tracking dust / audio pins / edge bleed", right_cluster=False))
        return group

    def _build_trim_group(self) -> QGroupBox:
        group = self._group_box("group.time")
        group.setObjectName("timePanel")
        grid = QGridLayout(group)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        grid.addWidget(self._label("label.timeline_start"), 0, 0)
        grid.addWidget(self.video_start, 0, 1)
        grid.addWidget(self._label("label.timeline_end"), 0, 2)
        grid.addWidget(self.video_end, 0, 3)

        grid.addWidget(self._label("label.music_trim_start"), 1, 0)
        grid.addWidget(self.audio_start, 1, 1)
        grid.addWidget(self._label("label.music_trim_end"), 1, 2)
        grid.addWidget(self.audio_end, 1, 3)

        grid.addWidget(self._label("label.music_start_video"), 2, 0)
        grid.addWidget(self.audio_timeline_start, 2, 1)
        grid.addWidget(self._label("label.music_end_video"), 2, 2)
        grid.addWidget(self.audio_timeline_end, 2, 3)

        grid.addWidget(self._label("label.audio_mix"), 3, 0)
        grid.addWidget(self.audio_mode, 3, 1)
        grid.addWidget(self.match_timeline_to_audio, 3, 2)
        grid.addWidget(self.match_timeline_mode, 3, 3)

        grid.addWidget(self._label("label.max_video_length"), 4, 0)
        grid.addWidget(self.max_video_length, 4, 1)
        grid.addWidget(self.random_clip_assembly, 4, 2, 1, 2)
        return group

    def _build_style_group(self) -> QGroupBox:
        group = self._group_box("group.style")
        group.setObjectName("stylePanel")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        style_row = QHBoxLayout()
        style_row.setSpacing(10)
        style_row.addWidget(self._label("label.text_mode"))
        style_row.addWidget(self.preset, stretch=1)
        layout.addLayout(style_row)
        layout.addWidget(self.style_preview)
        layout.addWidget(self.preset_description)
        dither_row = QHBoxLayout()
        dither_row.addWidget(self.chunky_blocks)
        dither_row.addStretch(1)
        dither_row.addWidget(self._label("label.dither"))
        dither_row.addWidget(self.dither_mode)
        layout.addLayout(dither_row)

        weird_row = QHBoxLayout()
        weird_row.addWidget(self.reroll_weirdness_button)
        weird_row.addWidget(self.weird_seed_label)
        weird_row.addStretch(1)
        layout.addLayout(weird_row)

        effects_grid = QGridLayout()
        effects_grid.setHorizontalSpacing(12)
        effects_grid.setVerticalSpacing(4)
        for index, (_key, _label, _tooltip) in enumerate(EFFECTS):
            row, col = divmod(index, 4)
            effects_grid.addWidget(self.effect_checks[_key], row, col)
        layout.addLayout(effects_grid)
        layout.addWidget(self._surface_wear_row("STYLE BANK // luma table // broken print pass 02", right_cluster=False))
        return group

    def _build_slider_group(self) -> QGroupBox:
        group = self._group_box("group.block_detail")
        group.setObjectName("blockDetailPanel")
        layout = QVBoxLayout(group)
        layout.addWidget(
            self._slider_row(
                "slider.character_width",
                self.width_slider,
                self.width_value,
                "tooltip.character_width",
            )
        )
        layout.addWidget(self._slider_row("slider.effect_intensity", self.intensity_slider, self.intensity_value))
        return group

    def _build_framing_group(self) -> QGroupBox:
        group = self._group_box("group.framing")
        group.setObjectName("framingPanel")
        layout = QVBoxLayout(group)
        grid = QGridLayout()
        grid.addWidget(self._label("label.fit_mode"), 0, 0)
        grid.addWidget(self.fit_mode, 0, 1)
        grid.addWidget(self._label("label.anchor"), 0, 2)
        grid.addWidget(self.anchor_mode, 0, 3)
        grid.addWidget(self._label("label.bars"), 1, 0)
        grid.addWidget(self.letterbox_background, 1, 1)
        grid.addWidget(self.upper_bias, 1, 2, 1, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)
        layout.addWidget(self._slider_row("slider.horizontal_offset", self.framing_x_slider, self.framing_x_value))
        layout.addWidget(self._slider_row("slider.vertical_offset", self.framing_y_slider, self.framing_y_value))
        layout.addWidget(self._slider_row("slider.zoom_crop", self.framing_zoom_slider, self.framing_zoom_value))
        note = self._label("note.framing")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(self._surface_wear_row("CANVAS BUS // crop deck // upper-frame registration", right_cluster=False))
        return group

    def _build_transition_group(self) -> QGroupBox:
        group = self._group_box("group.transitions")
        group.setObjectName("transitionPanel")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(self._label("label.mode"))
        row.addWidget(self.transition_mode, stretch=1)
        layout.addLayout(row)
        layout.addWidget(self._slider_row("slider.transition_intensity", self.transition_intensity_slider, self.transition_intensity_value))
        note = self._label("note.transitions")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _build_ending_group(self) -> QGroupBox:
        group = self._group_box("group.ending")
        group.setObjectName("endingPanel")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(self._label("label.ending_mode"))
        row.addWidget(self.ending_mode, stretch=1)
        row.addWidget(self.loop_friendly)
        layout.addLayout(row)
        note = self._label("note.ending")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _build_output_size_group(self) -> QGroupBox:
        group = self._group_box("group.output_size")
        group.setObjectName("outputSizePanel")
        layout = QVBoxLayout(group)

        preset_row = QHBoxLayout()
        preset_row.addWidget(self._label("label.preset"))
        preset_row.addWidget(self.output_size_preset, stretch=1)
        layout.addLayout(preset_row)
        layout.addWidget(self.output_size_description)

        custom_grid = QGridLayout()
        custom_grid.addWidget(self._label("label.max_width"), 0, 0)
        custom_grid.addWidget(self.max_width_spin, 0, 1)
        custom_grid.addWidget(self._label("label.output_fps"), 0, 2)
        custom_grid.addWidget(self.output_fps_spin, 0, 3)
        custom_grid.addWidget(self._label("label.crf"), 1, 0)
        custom_grid.addWidget(self.crf_spin, 1, 1)
        custom_grid.addWidget(self._label("label.audio"), 1, 2)
        custom_grid.addWidget(self.audio_bitrate_spin, 1, 3)
        custom_grid.setColumnStretch(1, 1)
        custom_grid.setColumnStretch(3, 1)
        layout.addLayout(custom_grid)

        estimate_row = QHBoxLayout()
        estimate_row.addWidget(self.estimated_size_label)
        estimate_row.addStretch(1)
        layout.addLayout(estimate_row)

        note = self._label("note.output_size")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(self._surface_wear_row("OUTPUT SIZE // share lane // bitrate counter wear", right_cluster=False))
        return group

    def _build_optimize_group(self) -> QGroupBox:
        group = self._group_box("group.optimize")
        group.setObjectName("optimizePanel")
        layout = QVBoxLayout(group)

        enable_row = QHBoxLayout()
        enable_row.addWidget(self.target_size_enabled)
        enable_row.addWidget(self._label("label.preset"))
        enable_row.addWidget(self.optimize_preset, stretch=1)
        enable_row.addWidget(self._label("label.max_size"))
        enable_row.addWidget(self.target_size_mb)
        layout.addLayout(enable_row)
        layout.addWidget(self.optimize_description)

        status_row = QHBoxLayout()
        status_row.addWidget(self.optimize_estimate_label)
        status_row.addStretch(1)
        status_row.addWidget(self.final_size_label)
        layout.addLayout(status_row)

        note = self._label("note.optimize")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _build_batch_group(self) -> QGroupBox:
        group = self._group_box("group.batch")
        group.setObjectName("batchPanel")
        layout = QVBoxLayout(group)
        top_row = QHBoxLayout()
        top_row.addWidget(self.batch_enabled)
        top_row.addStretch(1)
        top_row.addWidget(self.batch_status_label)
        layout.addLayout(top_row)

        variants_grid = QGridLayout()
        for index, variant in enumerate(BATCH_VARIANTS):
            row, col = divmod(index, 3)
            variants_grid.addWidget(self.batch_checks[variant], row, col)
        layout.addLayout(variants_grid)

        action_row = QHBoxLayout()
        action_row.addWidget(self.batch_button)
        action_row.addWidget(self.cancel_batch_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        note = self._label("note.batch")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(self._surface_wear_row("VARIANT DECK // pass queue // duplicate tape marks", right_cluster=False))
        return group

    def _slider_row(
        self,
        label_text: str,
        slider: QSlider,
        value_label: QLabel,
        tooltip: str | None = None,
    ) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = self._label(label_text)
        label.setMinimumWidth(170)
        if tooltip:
            self._register_tooltip(row, tooltip)
            self._register_tooltip(label, tooltip)
            self._register_tooltip(slider, tooltip)
            self._register_tooltip(value_label, tooltip)
        layout.addWidget(label)
        layout.addWidget(slider, stretch=1)
        layout.addWidget(value_label)
        return row

    def _build_coverage_group(self) -> QGroupBox:
        group = self._group_box("group.coverage")
        group.setObjectName("coveragePanel")
        layout = QVBoxLayout(group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self._label("label.mode"))
        mode_row.addWidget(self.bypass_mode, stretch=1)
        mode_row.addWidget(self._label("label.random_normal"))
        mode_row.addWidget(self.random_percent)
        mode_row.addWidget(self.reroll_button)
        layout.addLayout(mode_row)

        summary_row = QHBoxLayout()
        summary_row.addWidget(self.coverage_bar, stretch=1)
        summary_row.addWidget(self.coverage_detail)
        summary_row.addWidget(self.seed_label)
        layout.addLayout(summary_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        manual_header = QHBoxLayout()
        manual_header.addWidget(self._label("label.manual_blocks"))
        manual_header.addStretch(1)
        manual_header.addWidget(self.add_block_button)
        layout.addLayout(manual_header)
        layout.addWidget(self.manual_blocks_widget)
        layout.addWidget(self._surface_wear_row("COVERAGE MAP // normal-video islands // reroll marks", right_cluster=False))
        return group

    def _build_output_group(self) -> QGroupBox:
        group = self._group_box("group.output")
        group.setObjectName("outputPanel")
        layout = QVBoxLayout(group)
        output_row = QHBoxLayout()
        choose_button = self._button("button.choose_output")
        choose_button.setObjectName("secondaryButton")
        choose_button.clicked.connect(self.select_output)
        output_row.addWidget(choose_button)
        output_row.addWidget(self.output_path, stretch=1)

        preview_row = QHBoxLayout()
        preview_row.addWidget(self.preview_button)
        preview_row.addWidget(self._label("label.length"))
        preview_row.addWidget(self.preview_duration)
        preview_row.addWidget(self._label("label.preview_from"))
        preview_row.addWidget(self.preview_from)
        preview_row.addWidget(self.preview_custom)
        preview_row.addWidget(self.open_preview_button)
        preview_row.addWidget(self.clear_preview_cache_button)
        preview_row.addStretch(1)

        project_row = QHBoxLayout()
        project_row.addWidget(self.save_project_button)
        project_row.addWidget(self.load_project_button)
        project_row.addWidget(self.reset_project_button)
        project_row.addStretch(1)
        project_row.addWidget(self.experimental_frame_pipe)
        project_row.addWidget(self.open_output_button)

        action_row = QHBoxLayout()
        self.start_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.progress, stretch=1)

        layout.addLayout(output_row)
        layout.addLayout(preview_row)
        layout.addLayout(project_row)
        layout.addLayout(action_row)
        layout.addWidget(self._surface_wear_row("EXPORT HARDWARE // deck ready // write gate armed", right_cluster=True))
        return group

    def _connect_signals(self) -> None:
        self.add_videos_button.clicked.connect(self.add_videos)
        self.add_photos_button.clicked.connect(self.add_photos)
        self.remove_source_button.clicked.connect(self.remove_selected_source)
        self.move_source_up_button.clicked.connect(lambda: self.move_selected_source(-1))
        self.move_source_down_button.clicked.connect(lambda: self.move_selected_source(1))
        self.clear_sources_button.clicked.connect(self.clear_sources)
        self.shuffle_sources_button.clicked.connect(self.shuffle_timeline)
        self.preview_source_button.clicked.connect(self.preview_selected_source)
        self.timeline_table.itemChanged.connect(self._timeline_table_item_changed)
        self.timeline_table.itemSelectionChanged.connect(self.preview_selected_source)
        self.timeline_table.files_dropped.connect(self.add_dropped_timeline_files)
        self.audio_path.files_dropped.connect(self.set_dropped_audio_file)
        self.start_button.clicked.connect(self.start_render)
        self.preview_button.clicked.connect(self.start_preview_render)
        self.batch_button.clicked.connect(self.start_batch_render)
        self.cancel_batch_button.clicked.connect(self.cancel_batch_render)
        self.batch_enabled.toggled.connect(self._save_settings)
        self.preview_duration.currentTextChanged.connect(self._update_preview_controls)
        self.preview_duration.currentTextChanged.connect(lambda _text: self._save_settings())
        self.preview_from.currentTextChanged.connect(self._update_preview_controls)
        self.open_preview_button.clicked.connect(self.open_preview)
        self.clear_preview_cache_button.clicked.connect(self.confirm_clear_preview_cache)
        self.save_project_button.clicked.connect(self.save_project_preset)
        self.load_project_button.clicked.connect(self.load_project_preset)
        self.reset_project_button.clicked.connect(self.reset_project)
        self.open_output_button.clicked.connect(self.open_output_folder)
        self.copy_report_button.clicked.connect(self.copy_report)
        self.experimental_frame_pipe.toggled.connect(lambda _checked: self._save_settings())
        self.check_update_button.clicked.connect(lambda: self.check_for_updates(manual=True))
        self.download_update_button.clicked.connect(self.open_update_download)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.preset.currentTextChanged.connect(self._update_preset_description)
        self.chunky_blocks.toggled.connect(self._save_settings)
        self.output_size_preset.currentTextChanged.connect(self._apply_output_size_preset)
        self.optimize_preset.currentTextChanged.connect(self._apply_optimize_preset)
        self.target_size_enabled.toggled.connect(self._update_optimize_controls)
        for checkbox in self.batch_checks.values():
            checkbox.toggled.connect(self._save_settings)
        for checkbox in self.effect_checks.values():
            checkbox.toggled.connect(self._save_settings)
        for widget in (
            self.max_width_spin,
            self.output_fps_spin,
            self.crf_spin,
            self.audio_bitrate_spin,
            self.target_size_mb,
        ):
            widget.valueChanged.connect(self._update_output_size_estimate)
            widget.valueChanged.connect(self._update_optimize_estimate)
        for widget in (
            self.fit_mode,
            self.anchor_mode,
            self.letterbox_background,
            self.dither_mode,
            self.transition_mode,
            self.ending_mode,
        ):
            widget.currentTextChanged.connect(lambda _text: self._save_settings())
            widget.currentTextChanged.connect(lambda _text: self.preview_selected_source())
        self.upper_bias.toggled.connect(lambda _checked: self._save_settings())
        self.upper_bias.toggled.connect(lambda _checked: self.preview_selected_source())
        self.loop_friendly.toggled.connect(lambda _checked: self._save_settings())
        for slider in (self.framing_x_slider, self.framing_y_slider, self.framing_zoom_slider):
            slider.valueChanged.connect(self._refresh_slider_labels)
            slider.valueChanged.connect(lambda _value: self.preview_selected_source())
            slider.valueChanged.connect(lambda _value: self._save_settings())
        self.transition_intensity_slider.valueChanged.connect(self._refresh_slider_labels)
        self.transition_intensity_slider.valueChanged.connect(lambda _value: self._save_settings())

        self.bypass_mode.currentTextChanged.connect(self._update_coverage_controls)
        self.bypass_mode.currentTextChanged.connect(self._update_coverage_summary)
        self.random_percent.valueChanged.connect(self._update_coverage_summary)
        self.reroll_button.clicked.connect(self.reroll_random_sections)
        self.reroll_weirdness_button.clicked.connect(self.reroll_weirdness)
        self.add_block_button.clicked.connect(lambda: self.add_manual_block())
        self.video_start.textChanged.connect(self._update_coverage_summary)
        self.video_end.textChanged.connect(self._update_coverage_summary)
        self.video_start.textChanged.connect(self._update_output_size_estimate)
        self.video_end.textChanged.connect(self._update_output_size_estimate)
        self.audio_path.textChanged.connect(lambda _text: self._update_audio_controls())
        self.audio_path.textChanged.connect(self._update_output_size_estimate)
        self.worky_music_mode.toggled.connect(lambda _checked: self._update_audio_controls())
        self.worky_music_mode.toggled.connect(lambda _checked: self._update_output_size_estimate())
        self.worky_music_mode.toggled.connect(lambda _checked: self._update_optimize_estimate())
        self.worky_music_mode.toggled.connect(lambda _checked: self._save_settings())
        self.audio_start.textChanged.connect(self._update_output_size_estimate)
        self.audio_end.textChanged.connect(self._update_output_size_estimate)
        self.audio_timeline_start.textChanged.connect(self._update_output_size_estimate)
        self.audio_timeline_end.textChanged.connect(self._update_output_size_estimate)
        self.audio_start.textChanged.connect(self._update_coverage_summary)
        self.audio_end.textChanged.connect(self._update_coverage_summary)
        self.audio_timeline_start.textChanged.connect(self._update_coverage_summary)
        self.audio_timeline_end.textChanged.connect(self._update_coverage_summary)
        self.audio_timeline_start.textChanged.connect(lambda _text: self._save_settings())
        self.audio_timeline_end.textChanged.connect(lambda _text: self._save_settings())
        self.max_video_length.textChanged.connect(self._update_coverage_summary)
        self.max_video_length.textChanged.connect(self._update_output_size_estimate)
        self.max_video_length.textChanged.connect(self._update_optimize_estimate)
        self.max_video_length.textChanged.connect(lambda _text: self._save_settings())
        self.random_clip_assembly.toggled.connect(lambda _checked: self._update_coverage_summary())
        self.random_clip_assembly.toggled.connect(lambda _checked: self._update_output_size_estimate())
        self.random_clip_assembly.toggled.connect(lambda _checked: self._update_optimize_estimate())
        self.random_clip_assembly.toggled.connect(lambda _checked: self._save_settings())
        self.video_start.textChanged.connect(self._update_optimize_estimate)
        self.video_end.textChanged.connect(self._update_optimize_estimate)
        self.audio_path.textChanged.connect(self._update_optimize_estimate)
        self.audio_mode.currentTextChanged.connect(lambda _text: self._update_audio_controls())
        self.audio_mode.currentTextChanged.connect(lambda _text: self._save_settings())
        self.audio_mode.currentTextChanged.connect(lambda _text: self._update_output_size_estimate())
        self.audio_mode.currentTextChanged.connect(lambda _text: self._update_optimize_estimate())
        self.match_timeline_to_audio.toggled.connect(lambda _checked: self._update_audio_controls())
        self.match_timeline_to_audio.toggled.connect(lambda _checked: self._update_coverage_summary())
        self.match_timeline_to_audio.toggled.connect(lambda _checked: self._update_output_size_estimate())
        self.match_timeline_to_audio.toggled.connect(lambda _checked: self._update_optimize_estimate())
        self.match_timeline_to_audio.toggled.connect(lambda _checked: self._save_settings())
        self.match_timeline_mode.currentTextChanged.connect(lambda _text: self._update_coverage_summary())
        self.match_timeline_mode.currentTextChanged.connect(lambda _text: self._update_output_size_estimate())
        self.match_timeline_mode.currentTextChanged.connect(lambda _text: self._update_optimize_estimate())
        self.match_timeline_mode.currentTextChanged.connect(lambda _text: self._save_settings())

        for slider in (self.width_slider, self.intensity_slider):
            slider.valueChanged.connect(self._refresh_slider_labels)
            slider.valueChanged.connect(lambda _value: self._save_settings())

    def _apply_style(self) -> None:
        self.setStyleSheet(app_stylesheet())

    def add_videos(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("file.add_video_title"),
            str(Path.home()),
            (
                "Media files (*.mp4 *.mov *.m4v *.mts *.m2ts *.avi *.mkv *.webm "
                "*.jpg *.jpeg *.png *.webp *.avif *.gif *.bmp *.tif *.tiff *.heic *.heif);;"
                "Video files (*.mp4 *.mov *.m4v *.mts *.m2ts *.avi *.mkv *.webm);;"
                "Photo files (*.jpg *.jpeg *.png *.webp *.avif *.gif *.bmp *.tif *.tiff *.heic *.heif)"
            ),
        )
        self._add_timeline_paths(paths)

    def add_photos(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.tr("file.add_photo_title"),
            str(Path.home()),
            "Photo files (*.jpg *.jpeg *.png *.webp *.avif *.gif *.bmp *.tif *.tiff *.heic *.heif)",
        )
        self._add_timeline_paths(paths, forced_kind="photo")

    def add_dropped_timeline_files(self, paths: list[str]) -> None:
        self._add_timeline_paths(paths)

    def _add_timeline_paths(self, paths: list[str], forced_kind: str | None = None) -> None:
        if not paths:
            return
        started = time.perf_counter()
        start_index = len(self.timeline_items)
        added = 0
        skipped: list[str] = []
        heic_count = 0
        for path in paths:
            kind = forced_kind or media_kind(path)
            if kind not in {"video", "photo"}:
                skipped.append(Path(path).name or path)
                continue
            if Path(path).suffix.lower() in HEIC_EXTENSIONS:
                heic_count += 1
            if self._append_timeline_item(path, kind):
                added += 1
        if added:
            self._refresh_timeline_table()
            self.timeline_table.selectRow(start_index)
            self._after_timeline_changed()
            heic_note = f", {heic_count} HEIC/HEIF" if heic_count else ""
            self.append_log(
                f"Media import: added {added} source(s){heic_note} in {time.perf_counter() - started:.2f}s."
            )
        if skipped:
            self.append_log(
                "Rejected unsupported timeline file(s): "
                + ", ".join(skipped[:8])
                + (" ..." if len(skipped) > 8 else "")
            )
            QMessageBox.warning(
                self,
                APP_NAME,
                self.tr("dialog.unsupported_timeline_drop", files="\n".join(skipped[:8])),
            )

    def _append_timeline_item(self, path: str, kind: str) -> bool:
        source = Path(path)
        if not source.exists():
            self.append_log(f"Rejected missing source file: {path}")
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.source_missing", path=path))
            return False
        requested_kind = kind if kind in {"video", "photo"} else self._guess_source_kind(path, kind)
        detected_kind = media_kind(path)
        if requested_kind == "video" and detected_kind != "video":
            self.append_log(f"Rejected non-video source: {source.name}")
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.add_video_only", path=path))
            return False
        if requested_kind == "photo" and detected_kind != "photo":
            self.append_log(f"Rejected non-photo source: {source.name}")
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.add_photo_only", path=path))
            return False
        kind = requested_kind
        duration = 0.0
        has_audio = False
        include_audio = False
        if kind == "video":
            if not is_video_file(path):
                QMessageBox.warning(self, APP_NAME, self.tr("dialog.add_video_only", path=path))
                return False
            try:
                duration = ffmpeg_utils.get_duration(path)
                has_audio = has_audio_stream(path)
                include_audio = has_audio
                audio_note = "audio on" if has_audio else "no audio"
                self.append_log(
                    f"Added video: {source.name} ({ffmpeg_utils.format_duration(duration)}, {audio_note})"
                )
            except Exception as exc:  # noqa: BLE001
                self.append_log(f"Could not probe video source {source.name}: {exc}")
                QMessageBox.warning(self, APP_NAME, self.tr("dialog.probe_video_failed", error=exc))
                return False
        else:
            if not is_image_file(path):
                QMessageBox.warning(self, APP_NAME, self.tr("dialog.add_photo_only", path=path))
                return False
            try:
                self._validate_photo_source(path)
            except ValueError as exc:
                self.append_log(f"Could not add photo {source.name}: {exc}")
                QMessageBox.warning(self, APP_NAME, str(exc))
                return False
            duration = 3.0
            if source.suffix.lower() in HEIC_EXTENSIONS:
                self.append_log(
                    f"Added HEIC/HEIF photo: {source.name} "
                    "(3.0s subtle motion loop, silent; decode cached on first preview/render)"
                )
            else:
                self.append_log(f"Added photo: {source.name} (3.0s hold, silent)")
        self.timeline_items.append(
            {
                "path": str(source),
                "kind": kind,
                "duration": float(duration),
                "trim_start": "0:00",
                "trim_end": "auto",
                "photo_hold_duration": "3.0",
                "has_audio": bool(has_audio),
                "include_audio": bool(include_audio),
            }
        )
        if include_audio and not self.audio_path.text().strip() and self.audio_mode.currentText() == AUDIO_SILENT:
            self._set_combo_text(self.audio_mode, AUDIO_SOURCE)
        return True

    def _guess_source_kind(self, path: str, fallback: str = "video") -> str:
        kind = media_kind(path)
        if kind in {"photo", "video"}:
            return kind
        return fallback if fallback in {"video", "photo"} else "video"

    def _validate_photo_source(self, path: str) -> None:
        suffix = Path(path).suffix.lower()
        if suffix in HEIC_EXTENSIONS:
            return
        try:
            self._load_photo_image(path).load()
        except Exception as exc:  # noqa: BLE001 - Pillow codec support varies locally.
            raise ValueError(f"Could not read photo file:\n{path}\n\n{exc}") from exc

    def _load_photo_image(self, path: str) -> Image.Image:
        try:
            return still_cache.load_still_image(path, max_dimension=1024, log=self.append_log).image
        except Exception as exc:  # noqa: BLE001 - Pillow/ffmpeg HEIC support varies locally.
            if Path(path).suffix.lower() in HEIC_EXTENSIONS:
                raise ValueError(
                    "HEIC/HEIF image support is not available in this install. "
                    "Install or update ffmpeg, or convert the photo to PNG/JPEG and add it again."
                ) from exc
            raise

    def _refresh_timeline_table(self) -> None:
        self._timeline_table_updating = True
        try:
            self.timeline_table.setRowCount(len(self.timeline_items))
            for row, item in enumerate(self.timeline_items):
                path = str(item.get("path", ""))
                kind = str(item.get("kind", "video"))
                file_item = self._table_item(Path(path).name or path, editable=False)
                file_item.setToolTip(path)
                self.timeline_table.setItem(row, 0, file_item)
                self.timeline_table.setItem(row, 1, self._table_item(self.tr(f"kind.{kind}"), editable=False))
                self.timeline_table.setItem(row, 2, self._table_item(self._timeline_duration_text(item), editable=False))
                if kind == "photo":
                    self.timeline_table.setItem(row, 3, self._table_item("", editable=False))
                    self.timeline_table.setItem(
                        row,
                        4,
                        self._table_item(str(item.get("photo_hold_duration", "3.0")), editable=True),
                    )
                    self.timeline_table.setItem(row, 5, self._audio_table_item(False, False, False))
                else:
                    has_audio = bool(item.get("has_audio", False))
                    include_audio = bool(item.get("include_audio", has_audio)) and has_audio
                    item["include_audio"] = include_audio
                    self.timeline_table.setItem(
                        row,
                        3,
                        self._table_item(str(item.get("trim_start", "0:00")), editable=True),
                    )
                    self.timeline_table.setItem(
                        row,
                        4,
                        self._table_item(str(item.get("trim_end", "auto")), editable=True),
                    )
                    self.timeline_table.setItem(row, 5, self._audio_table_item(True, has_audio, include_audio))
            header = self.timeline_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for col in range(1, 6):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.timeline_table.setColumnWidth(1, 74)
            self.timeline_table.setColumnWidth(2, 86)
            self.timeline_table.setColumnWidth(3, 96)
            self.timeline_table.setColumnWidth(4, 104)
            self.timeline_table.setColumnWidth(5, 112)
        finally:
            self._timeline_table_updating = False

    def _table_item(self, text: str, editable: bool) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        flags = item.flags()
        if editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        else:
            flags &= ~Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        return item

    def _audio_table_item(self, is_video: bool, has_audio: bool, include_audio: bool) -> QTableWidgetItem:
        item = QTableWidgetItem("")
        flags = item.flags()
        flags &= ~Qt.ItemFlag.ItemIsEditable
        flags |= Qt.ItemFlag.ItemIsUserCheckable
        if is_video and has_audio:
            flags |= Qt.ItemFlag.ItemIsEnabled
            item.setToolTip(self.tr("tooltip.timeline_audio_on"))
        else:
            flags &= ~Qt.ItemFlag.ItemIsEnabled
            item.setToolTip(self.tr("tooltip.timeline_audio_off"))
        item.setFlags(flags)
        item.setCheckState(Qt.CheckState.Checked if include_audio and has_audio else Qt.CheckState.Unchecked)
        return item

    def _timeline_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._timeline_table_updating:
            return
        self._sync_timeline_from_table()
        row = item.row()
        if 0 <= row < len(self.timeline_items):
            self._timeline_table_updating = True
            try:
                duration_item = self.timeline_table.item(row, 2)
                if duration_item is not None:
                    duration_item.setText(self._timeline_duration_text(self.timeline_items[row]))
            finally:
                self._timeline_table_updating = False
        self._after_timeline_changed(save=True)

    def _sync_timeline_from_table(self) -> None:
        for row, item in enumerate(self.timeline_items):
            kind = str(item.get("kind", "video"))
            if kind == "photo":
                hold_item = self.timeline_table.item(row, 4)
                item["photo_hold_duration"] = hold_item.text().strip() if hold_item else "3.0"
                item["has_audio"] = False
                item["include_audio"] = False
            else:
                start_item = self.timeline_table.item(row, 3)
                end_item = self.timeline_table.item(row, 4)
                audio_item = self.timeline_table.item(row, 5)
                has_audio = bool(item.get("has_audio", False))
                item["trim_start"] = start_item.text().strip() if start_item else "0:00"
                item["trim_end"] = end_item.text().strip() if end_item else "auto"
                item["include_audio"] = bool(
                    has_audio
                    and audio_item is not None
                    and audio_item.checkState() == Qt.CheckState.Checked
                )

    def _after_timeline_changed(self, save: bool = True) -> None:
        self._sync_legacy_video_path()
        self._update_timeline_duration_label()
        self._update_coverage_summary()
        self._update_audio_controls()
        self._update_output_size_estimate()
        self._update_optimize_estimate()
        self.preview_selected_source()
        self.open_output_button.hide()
        self.open_output_button.setEnabled(False)
        if self.timeline_items and not self.output_path.text().strip():
            self._set_default_output_from_sources()
        if save:
            self._save_settings()

    def _sync_legacy_video_path(self) -> None:
        first_video = next((item for item in self.timeline_items if item.get("kind") == "video"), None)
        first_source = first_video or (self.timeline_items[0] if self.timeline_items else None)
        self.video_path.setText(str(first_source.get("path", "")) if first_source else "")
        self.video_duration_seconds = self._timeline_total_duration(strict=False)

    def _set_default_output_from_sources(self) -> None:
        first = self.timeline_items[0]
        source = Path(str(first.get("path", "wzrd")))
        self.output_path.setText(str(source.with_name(f"{source.stem}_wzrd.mp4")))

    def _selected_timeline_index(self) -> int | None:
        rows = self.timeline_table.selectionModel().selectedRows() if self.timeline_table.selectionModel() else []
        if not rows:
            return 0 if self.timeline_items else None
        index = rows[0].row()
        return index if 0 <= index < len(self.timeline_items) else None

    def remove_selected_source(self) -> None:
        index = self._selected_timeline_index()
        if index is None:
            return
        removed = self.timeline_items.pop(index)
        self._refresh_timeline_table()
        if self.timeline_items:
            self.timeline_table.selectRow(min(index, len(self.timeline_items) - 1))
        self.append_log(f"Removed source: {Path(str(removed.get('path', ''))).name}")
        self._after_timeline_changed()

    def move_selected_source(self, direction: int) -> None:
        index = self._selected_timeline_index()
        if index is None:
            return
        target = index + direction
        if target < 0 or target >= len(self.timeline_items):
            return
        self.timeline_items[index], self.timeline_items[target] = self.timeline_items[target], self.timeline_items[index]
        self._refresh_timeline_table()
        self.timeline_table.selectRow(target)
        self._after_timeline_changed()

    def clear_sources(self) -> None:
        self.timeline_items.clear()
        self._refresh_timeline_table()
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(self.tr("status.no_source"))
        self._after_timeline_changed()

    def shuffle_timeline(self) -> None:
        if len(self.timeline_items) < 2:
            return
        random.shuffle(self.timeline_items)
        self._refresh_timeline_table()
        self.timeline_table.selectRow(0)
        self.append_log("Shuffled timeline sources.")
        self._after_timeline_changed()

    def preview_selected_source(self) -> None:
        index = self._selected_timeline_index()
        if index is None:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(self.tr("status.no_source"))
            return
        item = self.timeline_items[index]
        path = str(item.get("path", ""))
        kind = str(item.get("kind", "video"))
        if kind == "photo":
            self._load_photo_preview(path)
        else:
            trim_start = ffmpeg_utils.parse_timecode(str(item.get("trim_start", "0:00"))) or 0.0
            self._load_video_preview(path, start_seconds=trim_start)

    def _framing_kwargs(self) -> dict[str, object]:
        return {
            "fit_mode": self.fit_mode.currentText(),
            "anchor": self.anchor_mode.currentText(),
            "offset_x": self.framing_x_slider.value(),
            "offset_y": self.framing_y_slider.value(),
            "zoom_amount": self.framing_zoom_slider.value() / 100.0,
            "letterbox_background": self.letterbox_background.currentText(),
            "upper_bias": self.upper_bias.isChecked(),
        }

    def _image_to_preview_pixmap(self, image: Image.Image) -> QPixmap:
        image = image.convert("RGB")
        width, height = image.size
        qimage = QImage(
            image.tobytes(),
            width,
            height,
            width * 3,
            QImage.Format.Format_RGB888,
        ).copy()
        return QPixmap.fromImage(qimage).scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _load_photo_preview(self, path: str) -> None:
        try:
            frame_rgb = self._load_photo_image(path)
            framed = fit_frame_to_output(
                frame_rgb,
                (640, 360),
                **self._framing_kwargs(),
            )
            pixmap = self._image_to_preview_pixmap(framed)
        except Exception:  # noqa: BLE001 - preview should fail softly.
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(self.tr("status.photo_preview_unavailable"))
            return
        self.preview_label.setText("")
        self.preview_label.setPixmap(pixmap)


    def _timeline_duration_text(self, item: dict[str, object]) -> str:
        try:
            return ffmpeg_utils.format_duration(self._timeline_item_duration(item, strict=False) or 0.0)
        except Exception:  # noqa: BLE001
            return "check trim"

    def _timeline_item_duration(self, item: dict[str, object], strict: bool) -> float | None:
        kind = str(item.get("kind", "video"))
        if kind == "photo":
            try:
                hold = ffmpeg_utils.parse_timecode(str(item.get("photo_hold_duration", "3.0")))
                if hold is None:
                    hold = 3.0
                if hold <= 0:
                    raise ValueError("photo hold must be greater than 0")
                return hold
            except Exception:
                if strict:
                    raise
                return None
        duration = float(item.get("duration", 0.0) or 0.0)
        try:
            start = ffmpeg_utils.parse_timecode(str(item.get("trim_start", "0:00"))) or 0.0
            end = ffmpeg_utils.parse_timecode(str(item.get("trim_end", "auto")))
            resolved_end = duration if end is None else end
            if resolved_end <= start:
                raise ValueError("trim end must be after trim start")
            return max(0.0, min(resolved_end, duration) - max(0.0, start))
        except Exception:
            if strict:
                raise
            return None

    def _timeline_total_duration(self, strict: bool) -> float | None:
        if not self.timeline_items:
            return None
        total = 0.0
        for item in self.timeline_items:
            duration = self._timeline_item_duration(item, strict=strict)
            if duration is None:
                return None
            total += duration
        return total

    def _update_timeline_duration_label(self) -> None:
        total = self._timeline_total_duration(strict=False)
        if total is None:
            self.video_duration.setText(self.tr("status.timeline_none"))
            self.video_duration_seconds = None
            return
        source_word = self.tr("word.source" if len(self.timeline_items) == 1 else "word.sources")
        self.video_duration_seconds = total
        self.video_duration.setText(
            self.tr(
                "status.timeline_across",
                duration=ffmpeg_utils.format_duration(total),
                count=len(self.timeline_items),
                source_word=source_word,
            )
        )

    def _timeline_items_for_render(self, strict: bool) -> list[TimelineItem]:
        self._sync_timeline_from_table()
        items: list[TimelineItem] = []
        if not self.timeline_items:
            if strict:
                raise ValueError("Add at least one video or photo source.")
            return items
        for index, item in enumerate(self.timeline_items, start=1):
            path = str(item.get("path", ""))
            if not Path(path).exists():
                raise FileNotFoundError(f"Timeline source {index} does not exist:\n{path}")
            kind = str(item.get("kind", "video"))
            if kind == "photo":
                hold = ffmpeg_utils.parse_timecode(str(item.get("photo_hold_duration", "3.0")))
                if hold is None:
                    hold = 3.0
                if hold <= 0:
                    raise ValueError(f"Photo source {index} hold duration must be greater than 0.")
                items.append(
                    TimelineItem(
                        path=path,
                        kind="photo",
                        duration=float(hold),
                        photo_hold_duration=float(hold),
                        has_audio=False,
                        include_audio=False,
                    )
                )
                continue
            duration = float(item.get("duration", 0.0) or 0.0)
            if duration <= 0:
                duration = ffmpeg_utils.get_duration(path)
                item["duration"] = duration
            trim_start = ffmpeg_utils.parse_timecode(str(item.get("trim_start", "0:00"))) or 0.0
            trim_end = ffmpeg_utils.parse_timecode(str(item.get("trim_end", "auto")))
            has_audio = bool(item.get("has_audio", False))
            if not has_audio and "has_audio" not in item:
                try:
                    has_audio = has_audio_stream(path)
                    item["has_audio"] = has_audio
                except Exception:  # noqa: BLE001 - render validation will handle broken media.
                    has_audio = False
            include_audio = bool(item.get("include_audio", has_audio)) and has_audio
            items.append(
                TimelineItem(
                    path=path,
                    kind="video",
                    duration=duration,
                    trim_start=trim_start,
                    trim_end=trim_end,
                    has_audio=has_audio,
                    include_audio=include_audio,
                )
            )
        return items

    def select_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select video file",
            str(Path.home()),
            "Video files (*.mp4 *.mov *.m4v *.mts *.m2ts *.avi *.mkv *.webm)",
        )
        if not path:
            return
        self.timeline_items.clear()
        self._append_timeline_item(path, "video")
        self._refresh_timeline_table()
        self.timeline_table.selectRow(0)
        if not self.output_path.text().strip():
            source = Path(path)
            self.output_path.setText(str(source.with_name(f"{source.stem}_wzrd.mp4")))
        self._after_timeline_changed()


    def _update_preview_controls(self) -> None:
        seconds = int(self._selected_preview_seconds())
        self.preview_button.setText(self.tr("button.preview_seconds", seconds=seconds))
        self.preview_custom.setEnabled(self.preview_from.currentText() == "Custom timestamp")

    def _selected_preview_seconds(self) -> float:
        return PREVIEW_DURATION_OPTIONS.get(self.preview_duration.currentText(), PREVIEW_SECONDS)

    def select_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("file.select_audio_title"),
            str(Path.home()),
            "Audio or video-with-audio (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.aiff *.aif *.mp4 *.mov *.m4v *.mts *.m2ts *.avi *.mkv *.webm)",
        )
        if path:
            self._set_external_audio_path(path, from_drop=False)

    def set_dropped_audio_file(self, paths: list[str]) -> None:
        skipped: list[str] = []
        attempted = 0
        for path in paths:
            if media_kind(path) in {"audio", "video"}:
                attempted += 1
                if self._set_external_audio_path(path, from_drop=True):
                    if skipped:
                        self.append_log(
                            "Ignored unsupported dropped audio file(s): "
                            + ", ".join(skipped[:8])
                            + (" ..." if len(skipped) > 8 else "")
                        )
                    return
            else:
                skipped.append(Path(path).name or path)
        if skipped:
            self.append_log(
                "Rejected unsupported audio drop file(s): "
                + ", ".join(skipped[:8])
                + (" ..." if len(skipped) > 8 else "")
            )
        if attempted:
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.no_audio_drop_used"))
        else:
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.drop_audio_prompt"))

    def _set_external_audio_path(self, path: str, *, from_drop: bool) -> bool:
        if not is_audio_container_file(path):
            self.append_log(f"Rejected unsupported music/audio file type: {Path(path).name or path}")
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.unsupported_audio_type", path=path))
            return False
        try:
            if not has_audio_stream(path):
                raise ValueError(self.tr("dialog.selected_audio_no_track"))
        except ValueError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            self.append_log(str(exc))
            return False
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.inspect_audio_failed", error=exc))
            self.append_log(f"Could not inspect selected music file: {exc}")
            return False
        self.audio_path.setText(path)
        self._set_combo_text(self.audio_mode, AUDIO_EXTERNAL)
        self._probe_duration(path, self.audio_duration, "audio")
        verb = "Dropped" if from_drop else "Selected"
        if is_video_file(path):
            self.append_log(f"{verb} video container as music source; using audio track only.")
        else:
            self.append_log(f"{verb} audio source: {Path(path).name}")
        self._update_audio_controls()
        self._save_settings()
        return True


    def clear_audio(self) -> None:
        self.audio_path.clear()
        self.audio_duration_seconds = None
        self.audio_duration.setText(self.tr("status.duration_empty"))
        self.audio_start.setText("0:00")
        self.audio_end.setText("auto")
        self.audio_timeline_start.setText("0:00")
        self.audio_timeline_end.setText("auto")
        self._set_combo_text(self.audio_mode, AUDIO_SOURCE if self._source_has_audio() else AUDIO_SILENT)
        self._update_audio_controls()
        self._update_output_size_estimate()
        self._update_optimize_estimate()
        self._save_settings()

    def select_output(self) -> None:
        starting_path = self.output_path.text().strip() or str(Path.home() / "final_wzrd.mp4")
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("file.output_title"),
            starting_path,
            "MP4 video (*.mp4)",
        )
        if not path:
            return
        if Path(path).suffix.lower() != ".mp4":
            path = f"{path}.mp4"
        self.output_path.setText(path)
        self.open_output_button.hide()
        self.open_output_button.setEnabled(False)
        self._save_settings()

    def check_media_tools(self) -> None:
        missing: list[str] = []
        for name in ("ffmpeg", "ffprobe"):
            try:
                ffmpeg_utils.require_binary(name)
            except ffmpeg_utils.FFmpegError:
                missing.append(name)
        if not missing:
            self.append_log("ffmpeg and ffprobe are available.")
            return

        missing_text = ", ".join(missing)
        guidance = ffmpeg_utils.install_guidance()
        QMessageBox.warning(
            self,
            APP_NAME,
            self.tr("dialog.missing_tools", tools=missing_text, guidance=guidance),
        )
        self.append_log(f"Missing media tools: {missing_text}. {guidance}")

    def _load_video_preview(self, path: str, start_seconds: float | None = None) -> None:
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            self.preview_label.setText(self.tr("status.preview_unavailable"))
            self.preview_label.setPixmap(QPixmap())
            return
        try:
            if start_seconds is None:
                start_seconds = ffmpeg_utils.parse_timecode(self.video_start.text()) or 0.0
            if start_seconds > 0:
                capture.set(cv2.CAP_PROP_POS_MSEC, start_seconds * 1000.0)
            ok, frame_bgr = capture.read()
        finally:
            capture.release()
        if not ok:
            self.preview_label.setText(self.tr("status.preview_unavailable"))
            self.preview_label.setPixmap(QPixmap())
            return

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        framed = fit_frame_to_output(
            frame_rgb,
            (640, 360),
            **self._framing_kwargs(),
        )
        pixmap = self._image_to_preview_pixmap(framed)
        self.preview_label.setText("")
        self.preview_label.setPixmap(pixmap)

    def _probe_duration(self, path: str, label: QLabel, media_label: str) -> None:
        try:
            duration = (
                ffmpeg_utils.get_audio_duration(path)
                if media_label == "audio"
                else ffmpeg_utils.get_duration(path)
            )
        except Exception as exc:  # noqa: BLE001 - present a clear GUI error.
            label.setText(self.tr("status.duration_unknown"))
            if media_label == "video":
                self.video_duration_seconds = None
            else:
                self.audio_duration_seconds = None
            self.append_log(f"Could not probe {media_label}: {exc}")
            QMessageBox.warning(
                self,
                APP_NAME,
                self.tr("dialog.probe_duration_failed", media_label=media_label, error=exc),
            )
            return
        if media_label == "video":
            self.video_duration_seconds = duration
        else:
            self.audio_duration_seconds = duration
        label.setText(self.tr("status.duration", duration=ffmpeg_utils.format_duration(duration)))
        self.append_log(f"Detected {media_label} duration: {ffmpeg_utils.format_duration(duration)}")
        self._update_output_size_estimate()
        self._update_optimize_estimate()

    def reroll_random_sections(self) -> None:
        self.random_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.seed_label.setText(self.tr("status.seed", seed=self.random_seed))
        self._update_coverage_summary()
        self._save_settings()

    def reroll_weirdness(self) -> None:
        self.random_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.weird_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.seed_label.setText(self.tr("status.seed", seed=self.random_seed))
        self.weird_seed_label.setText(self.tr("status.weird_seed", seed=self.weird_seed))
        self._update_coverage_summary()
        self.append_log("Rerolled weirdness seeds for cuts, glitches, holds, transitions, and collapse hits.")
        self._save_settings()

    def add_manual_block(self, start: str = "0:12", end: str = "0:18") -> None:
        row = ManualBlockRow(start, end, translator=lambda key: self.tr(key))
        row.remove_requested.connect(self.remove_manual_block)
        row.changed.connect(self._update_coverage_summary)
        self.block_rows.append(row)
        self.manual_blocks_layout.addWidget(row)
        self._update_coverage_controls()
        self._update_coverage_summary()

    def remove_manual_block(self, row: ManualBlockRow) -> None:
        if row in self.block_rows:
            self.block_rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._update_coverage_summary()

    def _source_has_audio(self) -> bool:
        for item in self.timeline_items:
            if str(item.get("kind", "video")) != "video":
                continue
            if bool(item.get("has_audio", False)):
                return True
            path = str(item.get("path", ""))
            if not path or not Path(path).exists():
                continue
            try:
                has_audio = has_audio_stream(path)
                item["has_audio"] = has_audio
                if has_audio:
                    item.setdefault("include_audio", True)
                    return True
            except Exception:  # noqa: BLE001 - source audio availability should fail soft in UI.
                continue
        return False

    def _source_audio_selected(self) -> bool:
        for item in self.timeline_items:
            if str(item.get("kind", "video")) != "video":
                continue
            if bool(item.get("has_audio", False)) and bool(item.get("include_audio", False)):
                return True
        return False

    def _update_audio_controls(self) -> None:
        has_external = bool(self.audio_path.text().strip())
        current_mode = self.audio_mode.currentText()
        if has_external and current_mode not in {AUDIO_EXTERNAL, AUDIO_MIX, AUDIO_SOURCE, AUDIO_SILENT}:
            self._set_combo_text(self.audio_mode, AUDIO_EXTERNAL)
        elif not has_external and current_mode in {AUDIO_EXTERNAL, AUDIO_MIX}:
            self._set_combo_text(self.audio_mode, AUDIO_SOURCE if self._source_has_audio() else AUDIO_SILENT)

        mode = self.audio_mode.currentText()
        external_active = mode in {AUDIO_EXTERNAL, AUDIO_MIX} and has_external
        self.match_timeline_to_audio.setEnabled(external_active)
        self.match_timeline_mode.setEnabled(external_active and self.match_timeline_to_audio.isChecked())
        self.audio_start.setEnabled(external_active)
        self.audio_end.setEnabled(external_active)
        self.audio_timeline_start.setEnabled(external_active)
        self.audio_timeline_end.setEnabled(external_active)
        self.worky_music_mode.setEnabled(external_active)
        if not external_active and self.match_timeline_to_audio.isChecked():
            was_blocked = self.match_timeline_to_audio.blockSignals(True)
            self.match_timeline_to_audio.setChecked(False)
            self.match_timeline_to_audio.blockSignals(was_blocked)
        if mode == AUDIO_MIX and self.match_timeline_to_audio.isChecked():
            self.audio_duration.setToolTip(self.tr("tooltip.audio_match_external_only"))
        elif mode == AUDIO_MIX:
            if self.worky_music_mode.isChecked():
                self.audio_duration.setToolTip(self.tr("tooltip.audio_mix_worky"))
            else:
                self.audio_duration.setToolTip(self.tr("tooltip.audio_mix_external"))
        elif external_active:
            if self.worky_music_mode.isChecked():
                self.audio_duration.setToolTip(self.tr("tooltip.audio_external_worky"))
            else:
                self.audio_duration.setToolTip(self.tr("tooltip.audio_external"))
        elif mode == AUDIO_SOURCE:
            self.audio_duration.setToolTip(self.tr("tooltip.audio_source_only"))
        else:
            self.audio_duration.setToolTip(self.tr("tooltip.audio_silent"))

    def _selected_audio_duration(self, strict: bool) -> float | None:
        audio_path = self.audio_path.text().strip()
        if not audio_path:
            return None
        try:
            duration = ffmpeg_utils.get_audio_duration(audio_path)
            start = ffmpeg_utils.parse_timecode(self.audio_start.text()) or 0.0
            end = ffmpeg_utils.parse_timecode(self.audio_end.text())
            start, end = ffmpeg_utils.validate_time_range(start, end, duration, "Audio")
            clip_duration = end - start
            offset = ffmpeg_utils.parse_timecode(self.audio_timeline_start.text()) or 0.0
            output_end = ffmpeg_utils.parse_timecode(self.audio_timeline_end.text())
            if offset < 0:
                raise ValueError("Music start in video cannot be negative.")
            if output_end is not None and output_end <= offset:
                raise ValueError("Music end in video must be after music start in video.")
            active_duration = clip_duration if output_end is None else min(clip_duration, output_end - offset)
            return offset + max(0.0, active_duration)
        except Exception:
            if strict:
                raise
            return None

    def _selected_max_video_length(self, strict: bool) -> float | None:
        raw = self.max_video_length.text().strip()
        if not raw:
            return None
        try:
            seconds = ffmpeg_utils.parse_timecode(raw)
            if seconds is None or seconds <= 0:
                raise ValueError(self.tr("dialog.max_video_length_invalid"))
            return seconds
        except Exception as exc:  # noqa: BLE001
            if strict:
                if isinstance(exc, ValueError) and str(exc) == self.tr("dialog.max_video_length_invalid"):
                    raise
                raise ValueError(self.tr("dialog.max_video_length_invalid")) from exc
            return None

    def _update_coverage_controls(self) -> None:
        mode = self.bypass_mode.currentText()
        random_enabled = "Random" in mode
        manual_enabled = "Manual" in mode
        self.random_percent.setEnabled(random_enabled)
        self.reroll_button.setEnabled(random_enabled)
        self.add_block_button.setEnabled(manual_enabled)
        self.manual_blocks_widget.setEnabled(manual_enabled)

    def _update_coverage_summary(self) -> None:
        duration = self._current_render_duration(strict=False)
        if duration is None or duration <= 0:
            self.coverage_bar.setText(self.tr("status.coverage_full"))
            self.coverage_detail.setText(self.tr("status.coverage_add_source"))
            self.seed_label.setText(self.tr("status.seed", seed=self.random_seed))
            return
        try:
            intervals = build_bypass_intervals(
                duration=duration,
                mode=self.bypass_mode.currentText(),
                manual_blocks=self._manual_blocks(strict=False),
                random_percent=self.random_percent.value(),
                min_len=0.5,
                max_len=3.0,
                seed=self.random_seed,
            )
        except Exception as exc:  # noqa: BLE001
            self.coverage_bar.setText(self.tr("status.coverage_unavailable"))
            self.coverage_detail.setText(str(exc))
            return

        normal_seconds = sum(end - start for start, end in intervals)
        normal_pct = min(100.0, max(0.0, (normal_seconds / duration) * 100.0))
        ansi_pct = 100.0 - normal_pct
        filled = int(round(20 * (ansi_pct / 100.0)))
        bar = "█" * filled + "░" * (20 - filled)
        self.coverage_bar.setText(self.tr("status.coverage_bar", bar=bar, ansi_pct=ansi_pct, normal_pct=normal_pct))
        self.coverage_detail.setText(self.tr("status.coverage_detail", count=len(intervals)))
        self.seed_label.setText(self.tr("status.seed", seed=self.random_seed))

    def _refresh_slider_labels(self) -> None:
        self.width_value.setText(f"{self.width_slider.value()} chars")
        self.intensity_value.setText(f"{self.intensity_slider.value()}%")
        self.framing_x_value.setText(f"{self.framing_x_slider.value():+d}")
        self.framing_y_value.setText(f"{self.framing_y_slider.value():+d}")
        self.framing_zoom_value.setText(f"{self.framing_zoom_slider.value()}%")
        self.transition_intensity_value.setText(f"{self.transition_intensity_slider.value()}%")

    def _apply_output_size_preset(self) -> None:
        preset_name = self.output_size_preset.currentText()
        preset = OUTPUT_SIZE_PRESETS.get(preset_name, OUTPUT_SIZE_PRESETS["Full Quality"])
        is_custom = preset_name == "Custom"
        self.output_size_description.setText(str(preset["description"]))
        self.output_size_preset.setToolTip(str(preset["description"]))

        if not is_custom:
            spin_values = (
                (self.max_width_spin, int(preset["max_width"])),
                (self.output_fps_spin, int(preset["fps"])),
                (self.crf_spin, int(preset["crf"])),
                (self.audio_bitrate_spin, int(preset["audio_kbps"])),
            )
            for spin, value in spin_values:
                was_blocked = spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(was_blocked)

        for widget in (
            self.max_width_spin,
            self.output_fps_spin,
            self.crf_spin,
            self.audio_bitrate_spin,
        ):
            widget.setEnabled(is_custom)
        self._update_output_size_estimate()
        self._update_optimize_estimate()

    def _apply_optimize_preset(self) -> None:
        preset_name = self.optimize_preset.currentText()
        preset = OPTIMIZE_PRESETS.get(preset_name, OPTIMIZE_PRESETS["29 MB Text Limit"])
        is_custom = preset_name == "Custom"
        self.optimize_description.setText(str(preset["description"]))
        self.optimize_preset.setToolTip(str(preset["description"]))

        if not is_custom:
            was_blocked = self.target_size_mb.blockSignals(True)
            self.target_size_mb.setValue(float(preset["target_mb"]))
            self.target_size_mb.blockSignals(was_blocked)
        if self.target_size_enabled.isChecked() and not is_custom:
            self._set_combo_text(self.output_size_preset, "Custom")
            self.max_width_spin.setValue(int(preset["max_width"]))
            self.output_fps_spin.setValue(int(preset["fps"]))
            self.crf_spin.setValue(int(preset["crf"]))
            self.audio_bitrate_spin.setValue(int(preset["audio_kbps"]))
        self.optimize_preset.setEnabled(self.target_size_enabled.isChecked())
        self.target_size_mb.setEnabled(self.target_size_enabled.isChecked())
        self._update_output_size_estimate()
        self._update_optimize_estimate()

    def _update_optimize_controls(self) -> None:
        self.optimize_preset.setEnabled(self.target_size_enabled.isChecked())
        self.target_size_mb.setEnabled(self.target_size_enabled.isChecked())
        if self.target_size_enabled.isChecked():
            self._apply_optimize_preset()
            return
        self._update_optimize_estimate()
        self._update_output_size_estimate()

    def _output_size_values(self) -> dict[str, float | int | str | None]:
        preset_name = self.output_size_preset.currentText()
        preset = OUTPUT_SIZE_PRESETS.get(preset_name, OUTPUT_SIZE_PRESETS["Full Quality"])
        if preset_name == "Custom":
            max_width = int(self.max_width_spin.value())
            fps = int(self.output_fps_spin.value())
            crf = int(self.crf_spin.value())
            audio_kbps = int(self.audio_bitrate_spin.value())
            video_kbps_hint = self._custom_video_kbps_hint(max_width, fps, crf)
        else:
            max_width = int(preset["max_width"])
            fps = int(preset["fps"])
            crf = int(preset["crf"])
            audio_kbps = int(preset["audio_kbps"])
            video_kbps_hint = int(preset["video_kbps_hint"])
        return {
            "preset": preset_name,
            "max_width": max_width,
            "fps": fps,
            "crf": crf,
            "audio_kbps": audio_kbps,
            "video_kbps_hint": video_kbps_hint,
            "target_mb": None,
        }

    def _optimize_values(self) -> dict[str, float | str | bool]:
        return {
            "enabled": self.target_size_enabled.isChecked(),
            "preset": self.optimize_preset.currentText(),
            "target_mb": float(self.target_size_mb.value()),
        }

    def _custom_video_kbps_hint(self, max_width: int, fps: int, crf: int) -> int:
        pixel_scale = (max_width / 540.0) ** 2
        fps_scale = fps / 18.0
        crf_scale = 2 ** ((32 - crf) / 6.0)
        return max(140, min(12_000, int(620 * pixel_scale * fps_scale * crf_scale)))

    def _current_audio_mode_has_output(self) -> bool:
        mode = self.audio_mode.currentText()
        if mode == AUDIO_SILENT:
            return False
        if mode == AUDIO_EXTERNAL:
            return bool(self.audio_path.text().strip())
        if mode == AUDIO_SOURCE:
            return self._source_audio_selected()
        if mode == AUDIO_MIX:
            return bool(self.audio_path.text().strip()) or self._source_audio_selected()
        return False

    def _output_dimensions(self, max_width: int) -> tuple[int, int]:
        width = max(240, min(2560, int(max_width)))
        if width % 2:
            width -= 1
        height = max(2, int(round(width * 9 / 16)))
        if height % 2:
            height += 1
        return width, height

    def _update_output_size_estimate(self) -> None:
        duration = self._current_render_duration(strict=False)
        if duration is None or duration <= 0:
            self.estimated_size_label.setText(self.tr("status.estimated_add_source"))
            return

        values = self._output_size_values()
        has_audio_output = self._current_audio_mode_has_output()
        audio_kbps = int(values["audio_kbps"]) if has_audio_output else 0
        total_kbps = int(values["video_kbps_hint"]) + audio_kbps
        estimate_mb = (total_kbps * duration) / 8192.0
        low = max(0.1, estimate_mb * 0.75)
        high = max(low + 0.1, estimate_mb * 1.45)
        self.estimated_size_label.setText(
            self.tr("status.estimated_final", low=low, high=high)
        )

    def _update_optimize_estimate(self) -> None:
        values = self._optimize_values()
        if not values["enabled"]:
            self.optimize_estimate_label.setText(self.tr("status.optimize_disabled"))
            return
        duration = self._current_render_duration(strict=False)
        if duration is None or duration <= 0:
            self.optimize_estimate_label.setText(
                self.tr("status.optimize_target", target=float(values["target_mb"]))
            )
            return
        has_audio_output = self._current_audio_mode_has_output()
        audio_bps = int(self.audio_bitrate_spin.value()) * 1000 if has_audio_output else 0
        effective_mb = float(values["target_mb"]) * 0.93
        video_bitrate = max(
            int(((effective_mb * 8 * 1024 * 1024) - (audio_bps * duration)) / duration),
            150_000,
        )
        self.optimize_estimate_label.setText(
            self.tr(
                "status.optimize_video",
                target=float(values["target_mb"]),
                kbps=video_bitrate / 1000,
            )
        )

    def _update_preset_description(self) -> None:
        preset_name = self.preset.currentText()
        description = preset_description(preset_name)
        self.preset_description.setText(description)
        self.preset.setToolTip(description)
        try:
            preset = get_preset(preset_name)
        except KeyError:
            preset = {"background": (9, 8, 7), "tint": (186, 244, 200), "render_mode": ""}
        is_chunky = preset.get("render_mode") == "chunky_blocks"
        self._update_style_preview(preset_name, preset)
        if is_chunky and not self.chunky_blocks.isChecked():
            was_blocked = self.chunky_blocks.blockSignals(True)
            self.chunky_blocks.setChecked(True)
            self.chunky_blocks.blockSignals(was_blocked)
            self._chunky_auto = True
        elif is_chunky:
            self._chunky_auto = True
        elif not is_chunky and self._chunky_auto:
            was_blocked = self.chunky_blocks.blockSignals(True)
            self.chunky_blocks.setChecked(False)
            self.chunky_blocks.blockSignals(was_blocked)
            self._chunky_auto = False
        if is_chunky:
            if self.width_slider.value() > 110:
                self.width_slider.setValue(90)
            if self.output_size_preset.currentText() == "Full Quality":
                self._set_combo_text(self.output_size_preset, "Social Share")
            self.effect_checks["boost"].setChecked(True)

    def _update_style_preview(self, preset_name: str, preset: dict) -> None:
        bg = tuple(preset.get("background", (9, 8, 7)))
        tint = preset.get("tint") or (186, 244, 200)
        fg = tuple(tint)
        blocks = "██ ▓▓ ▒▒ ░░  WZRD.VID  ░░ ▒▒ ▓▓ ██"
        if preset.get("render_mode") != "chunky_blocks":
            blocks = "@#%*+=-.  WZRD.VID  .-=+*%#@"
        self.style_preview.setText(
            "<div style='"
            f"background: rgb({bg[0]}, {bg[1]}, {bg[2]}); "
            f"color: rgb({fg[0]}, {fg[1]}, {fg[2]}); "
            f"font-family: {MONO_FONT_STACK}; "
            "font-size: 18px; font-weight: 900; "
            "padding: 8px; border-radius: 8px;'>"
            f"{html.escape(blocks)}"
            "</div>"
            f"<div style='color: {PALETTE['black']}; font-size: 11px; padding-top: 6px;'>"
            f"{html.escape(preset_name.upper())}"
            "</div>"
        )

    def start_batch_render(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        try:
            variants = self._collect_batch_variants()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        if not variants:
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.batch_empty"))
            return

        self._save_settings()
        self.progress.setValue(0)
        self._set_render_controls_enabled(False)
        self.cancel_batch_button.setEnabled(True)
        self.active_task = "batch"
        self.last_render_error = ""
        self.append_log(f"Batch render started with {len(variants)} variant(s).")

        worker = BatchRenderThread(variants)
        self.worker = worker
        worker.progress_changed.connect(self.progress.setValue)
        worker.log_message.connect(self.append_log)
        worker.variant_changed.connect(self.batch_variant_changed)
        worker.render_finished.connect(self.render_finished)
        worker.render_failed.connect(self.render_failed)
        worker.finished.connect(self.thread_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def cancel_batch_render(self) -> None:
        if isinstance(self.worker, BatchRenderThread) and self.worker.isRunning():
            self.worker.request_cancel()
            self.cancel_batch_button.setEnabled(False)
            self.append_log("Cancel requested. Current variant will stop at the next progress update.")

    def _collect_batch_variants(self) -> list[tuple[str, RenderSettings]]:
        selected = [name for name, checkbox in self.batch_checks.items() if checkbox.isChecked()]
        if not selected:
            return []
        base_settings = self._collect_settings()
        output_dir, source_stem = self._batch_output_base(base_settings)
        variants: list[tuple[str, RenderSettings]] = []
        for name in selected:
            variant_settings = self._settings_for_batch_variant(name, base_settings)
            suffix = BATCH_SUFFIXES.get(name, self._safe_slug(name))
            output_path = self._unique_output_path(output_dir / f"{source_stem}_{suffix}.mp4")
            variants.append((name, replace(variant_settings, output_path=str(output_path))))
        return variants

    def _settings_for_batch_variant(self, name: str, base: RenderSettings) -> RenderSettings:
        if name == "Custom Current Settings":
            return base
        if name == "29 MB Text Limit":
            return replace(
                base,
                output_size=self._output_dimensions(540),
                fps=18,
                video_crf=32,
                audio_bitrate="64k",
                optimize_enabled=True,
                optimize_target_mb=29.0,
            )
        if name == "32 MB Sweet Spot":
            return replace(
                base,
                output_size=self._output_dimensions(720),
                fps=24,
                video_crf=26,
                audio_bitrate="96k",
                optimize_enabled=True,
                optimize_target_mb=32.0,
            )
        if name in {"Classic ANSI", "Dial-Up Neon"}:
            return replace(base, preset_name=name, chunky_blocks=False)
        if name in {"Chunkcore", "WZRD Blocks"}:
            return replace(base, preset_name=name, chunky_blocks=True, width_chars=min(base.width_chars, 100))
        return base

    def _batch_output_base(self, settings: RenderSettings) -> tuple[Path, str]:
        first = Path(settings.timeline_items[0].path)
        output_text = self.output_path.text().strip()
        output_dir = Path(output_text).expanduser().parent if output_text else first.parent
        return output_dir, self._safe_slug(first.stem) or "wzrd"

    def _safe_slug(self, value: str) -> str:
        slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug or "wzrd"

    def _unique_output_path(self, path: Path) -> Path:
        path = path.expanduser()
        candidate = path
        counter = 1
        while candidate.exists():
            candidate = path.with_name(f"{path.stem}_{counter:03d}{path.suffix}")
            counter += 1
        return candidate

    def batch_variant_changed(self, name: str, index: int, total: int) -> None:
        self.batch_status_label.setText(self.tr("status.batch_progress", index=index, total=total, name=name))

    def start_render(self) -> None:
        if self.batch_enabled.isChecked():
            self.start_batch_render()
            return
        if self.worker and self.worker.isRunning():
            return

        try:
            settings = self._collect_settings()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, str(exc))
            return

        self._save_settings()
        self.progress.setValue(0)
        self._set_render_controls_enabled(False)
        self.active_task = "render"
        self.last_render_error = ""
        self.append_log("Render queue started.")

        worker = RenderThread(settings)
        self.worker = worker
        worker.progress_changed.connect(self.progress.setValue)
        worker.log_message.connect(self.append_log)
        worker.render_finished.connect(self.render_finished)
        worker.render_failed.connect(self.render_failed)
        worker.finished.connect(self.thread_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def start_preview_render(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        try:
            settings = self._collect_preview_settings()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, str(exc))
            return

        self._save_settings()
        self.progress.setValue(0)
        self._set_render_controls_enabled(False)
        self.active_task = "preview"
        self.last_render_error = ""
        self.open_preview_button.hide()
        self.open_preview_button.setEnabled(False)
        self.append_log("Preview render started.")

        worker = RenderThread(settings)
        self.worker = worker
        worker.progress_changed.connect(self.progress.setValue)
        worker.log_message.connect(self.append_log)
        worker.render_finished.connect(self.render_finished)
        worker.render_failed.connect(self.render_failed)
        worker.finished.connect(self.thread_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _set_render_controls_enabled(self, enabled: bool) -> None:
        self.start_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.batch_button.setEnabled(enabled)
        self.experimental_frame_pipe.setEnabled(enabled)
        cleanup_running = bool(self.cache_cleanup_worker and self.cache_cleanup_worker.isRunning())
        self.clear_preview_cache_button.setEnabled(enabled and not cleanup_running)
        if enabled:
            self.cancel_batch_button.setEnabled(False)

    def _preview_cache_confirmation_text(self, summary: CacheCleanupSummary) -> str:
        return self.tr(
            "dialog.clear_preview_cache_confirm",
            size=format_cache_size(summary.bytes),
            count=summary.files,
            dirs=summary.dirs,
        )

    def confirm_clear_preview_cache(self) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr("dialog.render_running"),
            )
            return
        if self.cache_cleanup_worker and self.cache_cleanup_worker.isRunning():
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr("dialog.clear_preview_cache_running"),
            )
            return

        summary = preview_cache_usage()
        if summary.items == 0:
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr("dialog.clear_preview_cache_empty"),
            )
            return
        response = QMessageBox.question(
            self,
            APP_NAME,
            self._preview_cache_confirmation_text(summary),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if response != QMessageBox.StandardButton.Yes:
            return
        self._start_preview_cache_cleanup(manual=True, preview_age_seconds=0)

    def start_auto_preview_cache_cleanup(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        if self.cache_cleanup_worker and self.cache_cleanup_worker.isRunning():
            return
        self._start_preview_cache_cleanup(
            manual=False,
            preview_age_seconds=CACHE_CLEANUP_MAX_AGE_SECONDS,
        )

    def _start_preview_cache_cleanup(self, *, manual: bool, preview_age_seconds: int) -> None:
        self.clear_preview_cache_button.setEnabled(False)
        worker = CacheCleanupThread(
            manual=manual,
            preview_age_seconds=preview_age_seconds,
            parent=self,
        )
        self.cache_cleanup_worker = worker
        worker.cleanup_finished.connect(self._preview_cache_cleanup_finished)
        worker.finished.connect(self._preview_cache_cleanup_thread_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _preview_cache_cleanup_finished(self, summary: CacheCleanupSummary, manual: bool) -> None:
        if summary.items:
            key = "log.preview_cache_cleanup_deleted" if manual else "log.preview_cache_auto_deleted"
            self.append_log(
                self.tr(
                    key,
                    count=summary.files,
                    dirs=summary.dirs,
                    size=format_cache_size(summary.bytes),
                )
            )
        elif manual:
            self.append_log(self.tr("dialog.clear_preview_cache_empty"))

        if summary.errors:
            self.append_log(
                self.tr(
                    "log.preview_cache_cleanup_errors",
                    error_count=len(summary.errors),
                    first_error=summary.errors[0],
                )
            )

        if manual:
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr(
                    "dialog.clear_preview_cache_complete",
                    count=summary.files,
                    dirs=summary.dirs,
                    size=format_cache_size(summary.bytes),
                ),
            )

    def _preview_cache_cleanup_thread_finished(self) -> None:
        self.cache_cleanup_worker = None
        render_running = bool(self.worker and self.worker.isRunning())
        self.clear_preview_cache_button.setEnabled(not render_running)

    def _collect_settings(
        self,
        output_path_override: str | None = None,
        require_output: bool = True,
    ) -> RenderSettings:
        timeline_items = self._timeline_items_for_render(strict=True)
        if not timeline_items:
            raise ValueError("Add at least one video or photo source.")
        primary_path = timeline_items[0].path

        audio_path = self.audio_path.text().strip() or None
        audio_mode = self.audio_mode.currentText()
        if audio_path and not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file does not exist:\n{audio_path}")
        if audio_path:
            if not is_audio_container_file(audio_path):
                raise ValueError(f"Unsupported music/audio file type:\n{audio_path}")
            if not has_audio_stream(audio_path):
                raise ValueError("Selected music file has no audio track.")
        if audio_mode in {AUDIO_EXTERNAL, AUDIO_MIX} and not audio_path:
            if self.match_timeline_to_audio.isChecked():
                raise ValueError("Match video length to music requires a selected music/audio file.")
            audio_mode = AUDIO_SOURCE if self._source_audio_selected() else AUDIO_SILENT
        if self.match_timeline_to_audio.isChecked() and audio_mode not in {AUDIO_EXTERNAL, AUDIO_MIX}:
            raise ValueError("Match video length to music only works with External only or External + selected source audio modes.")
        if self.match_timeline_to_audio.isChecked() and audio_mode == AUDIO_MIX:
            self.append_log("Source audio mixing is disabled when matching timeline length to music; using external audio only for this render.")

        output_path = output_path_override or self.output_path.text().strip()
        if not output_path and require_output:
            raise ValueError("Choose an output filename.")
        if not output_path:
            output_path = str(self._new_preview_path())
        if Path(output_path).suffix.lower() != ".mp4":
            output_path = f"{output_path}.mp4"
            if output_path_override is None:
                self.output_path.setText(output_path)
        output_resolved = Path(output_path).expanduser().resolve(strict=False)
        for item in timeline_items:
            if output_resolved == Path(item.path).expanduser().resolve(strict=False):
                raise ValueError("Choose an output filename that is different from the timeline sources.")
        if audio_path and output_resolved == Path(audio_path).expanduser().resolve(strict=False):
            raise ValueError("Choose an output filename that is different from the source audio.")

        video_start = ffmpeg_utils.parse_timecode(self.video_start.text()) or 0.0
        video_end = ffmpeg_utils.parse_timecode(self.video_end.text())
        audio_start = ffmpeg_utils.parse_timecode(self.audio_start.text()) or 0.0
        audio_end = ffmpeg_utils.parse_timecode(self.audio_end.text())
        audio_timeline_start = ffmpeg_utils.parse_timecode(self.audio_timeline_start.text()) or 0.0
        audio_timeline_end = ffmpeg_utils.parse_timecode(self.audio_timeline_end.text())
        if audio_timeline_start < 0:
            raise ValueError("Music start in video cannot be negative.")
        if audio_timeline_end is not None and audio_timeline_end <= audio_timeline_start:
            raise ValueError("Music end in video must be after music start in video.")
        max_video_length = self._selected_max_video_length(strict=True)
        random_clip_assembly = self.random_clip_assembly.isChecked()
        if random_clip_assembly and max_video_length is None:
            raise ValueError(self.tr("dialog.random_requires_max"))
        if random_clip_assembly and self.match_timeline_to_audio.isChecked():
            raise ValueError(self.tr("dialog.random_conflicts_match_music"))
        output_values = self._output_size_values()
        optimize_values = self._optimize_values()
        output_size = self._output_dimensions(int(output_values["max_width"]))

        return RenderSettings(
            video_path=primary_path,
            audio_path=audio_path,
            output_path=output_path,
            video_start=video_start,
            video_end=video_end,
            audio_start=audio_start,
            audio_end=audio_end,
            preset_name=self.preset.currentText(),
            fps=int(output_values["fps"]),
            width_chars=int(self.width_slider.value()),
            output_size=output_size,
            video_crf=int(output_values["crf"]),
            audio_bitrate=f"{int(output_values['audio_kbps'])}k",
            audio_timeline_start=audio_timeline_start,
            audio_timeline_end=audio_timeline_end,
            max_video_length=max_video_length,
            random_clip_assembly=random_clip_assembly,
            audio_mode=audio_mode,
            worky_music_mode=self.worky_music_mode.isChecked(),
            match_timeline_to_audio=self.match_timeline_to_audio.isChecked(),
            match_timeline_mode=self.match_timeline_mode.currentText(),
            target_size_mb=None,
            optimize_enabled=bool(optimize_values["enabled"]),
            optimize_target_mb=float(optimize_values["target_mb"]),
            chunky_blocks=self.chunky_blocks.isChecked(),
            effects={key: checkbox.isChecked() for key, checkbox in self.effect_checks.items()},
            effect_intensity=self.intensity_slider.value() / 50.0,
            bypass_mode=self.bypass_mode.currentText(),
            manual_blocks=self._manual_blocks(strict=True),
            random_percent=float(self.random_percent.value()),
            random_seed=self.random_seed,
            random_min_len=0.5,
            random_max_len=3.0,
            weird_seed=self.weird_seed,
            framing_fit_mode=self.fit_mode.currentText(),
            framing_anchor=self.anchor_mode.currentText(),
            framing_offset_x=self.framing_x_slider.value(),
            framing_offset_y=self.framing_y_slider.value(),
            framing_zoom=self.framing_zoom_slider.value() / 100.0,
            letterbox_background=self.letterbox_background.currentText(),
            preserve_upper_bias=self.upper_bias.isChecked(),
            dither_mode=self.dither_mode.currentText(),
            transition_mode=self.transition_mode.currentText(),
            transition_intensity=self.transition_intensity_slider.value() / 50.0,
            ending_mode=self.ending_mode.currentText(),
            loop_friendly=self.loop_friendly.isChecked(),
            timeline_items=timeline_items,
            experimental_frame_pipe=self.experimental_frame_pipe.isChecked(),
        )

    def _collect_preview_settings(self) -> RenderSettings:
        preview_path = self._new_preview_path()
        settings = self._collect_settings(str(preview_path), require_output=False)
        timeline_duration = self._timeline_total_duration(strict=True)
        if timeline_duration is None:
            raise ValueError("Add at least one source before previewing.")
        video_start, video_end = ffmpeg_utils.validate_time_range(
            settings.video_start,
            settings.video_end,
            timeline_duration,
            "Timeline",
        )
        source_duration = video_end - video_start
        render_duration = self._current_render_duration(strict=True)
        if render_duration is None or render_duration <= 0:
            raise ValueError("Timeline trim range is empty.")

        preview_seconds = self._selected_preview_seconds()
        preview_offset = self._preview_offset(render_duration, preview_seconds)
        preview_length = min(preview_seconds, render_duration - preview_offset)
        if preview_length <= 0.05:
            raise ValueError("Preview start is outside the selected timeline trim range.")

        shifted_blocks = self._preview_bypass_blocks(settings, render_duration, preview_offset, preview_length)

        audio_path = settings.audio_path
        audio_start = settings.audio_start
        audio_end = settings.audio_end
        audio_timeline_start = settings.audio_timeline_start
        audio_timeline_end = settings.audio_timeline_end
        if settings.audio_mode in {AUDIO_EXTERNAL, AUDIO_MIX} and settings.audio_path:
            audio_duration = ffmpeg_utils.get_audio_duration(settings.audio_path)
            selected_audio_start, selected_audio_end = ffmpeg_utils.validate_time_range(
                settings.audio_start,
                settings.audio_end,
                audio_duration,
                "Audio",
            )
            selected_clip_duration = selected_audio_end - selected_audio_start
            original_audio_start = max(0.0, float(settings.audio_timeline_start or 0.0))
            original_audio_end = original_audio_start + selected_clip_duration
            if settings.audio_timeline_end is not None:
                original_audio_end = min(original_audio_end, float(settings.audio_timeline_end))
            original_audio_end = min(render_duration, original_audio_end)
            preview_end = preview_offset + preview_length
            overlap_start = max(preview_offset, original_audio_start)
            overlap_end = min(preview_end, original_audio_end)
            if overlap_end <= overlap_start:
                audio_path = None
                audio_start = 0.0
                audio_end = None
                audio_timeline_start = 0.0
                audio_timeline_end = None
                self.append_log("Preview segment is outside the selected music placement; rendering preview silent.")
            else:
                audio_start = selected_audio_start + max(0.0, overlap_start - original_audio_start)
                audio_end = min(selected_audio_end, audio_start + (overlap_end - overlap_start))
                audio_timeline_start = max(0.0, original_audio_start - preview_offset)
                audio_timeline_end = audio_timeline_start + max(0.0, audio_end - audio_start)

        source_offset = preview_offset
        source_length = preview_length
        if settings.match_timeline_to_audio and settings.audio_mode in {AUDIO_EXTERNAL, AUDIO_MIX} and source_duration > 0:
            mode = settings.match_timeline_mode
            if mode == MATCH_SPEED:
                speed_factor = source_duration / max(0.001, render_duration)
                source_offset = preview_offset * speed_factor
                source_length = preview_length * speed_factor
            elif mode == MATCH_LOOP:
                source_offset = preview_offset % source_duration
                source_length = min(source_duration, max(preview_length, min(preview_length, source_duration - source_offset)))
            else:
                source_offset = preview_offset
                source_length = preview_length

        preview_video_start = min(video_end - 0.001, video_start + source_offset)
        preview_video_end = min(video_end, preview_video_start + max(0.05, source_length))
        if preview_video_end <= preview_video_start:
            preview_video_end = min(video_end, preview_video_start + 0.05)

        self.append_log(
            f"Preview segment: {ffmpeg_utils.format_duration(preview_offset)} to "
            f"{ffmpeg_utils.format_duration(preview_offset + preview_length)} "
            "inside the selected output timeline."
        )
        return replace(
            settings,
            audio_path=audio_path,
            output_path=str(preview_path),
            video_start=preview_video_start,
            video_end=preview_video_end,
            audio_start=audio_start,
            audio_end=audio_end,
            audio_timeline_start=audio_timeline_start,
            audio_timeline_end=audio_timeline_end,
            max_video_length=preview_length,
            target_size_mb=None,
            optimize_enabled=False,
            bypass_mode=BYPASS_MANUAL if shifted_blocks else BYPASS_FULL_ANSI,
            manual_blocks=shifted_blocks,
            random_percent=0.0,
        )


    def _preview_offset(self, render_duration: float, preview_seconds: float | None = None) -> float:
        preview_seconds = PREVIEW_SECONDS if preview_seconds is None else preview_seconds
        mode = self.preview_from.currentText()
        if mode == "Start":
            return 0.0
        if mode == "Middle":
            return max(0.0, (render_duration - min(preview_seconds, render_duration)) / 2.0)
        custom = ffmpeg_utils.parse_timecode(self.preview_custom.text())
        return 0.0 if custom is None else max(0.0, custom)

    def _preview_bypass_blocks(
        self,
        settings: RenderSettings,
        render_duration: float,
        preview_offset: float,
        preview_length: float,
    ) -> list[tuple[float, float]]:
        full_intervals = build_bypass_intervals(
            duration=render_duration,
            mode=settings.bypass_mode,
            manual_blocks=settings.manual_blocks,
            random_percent=settings.random_percent,
            min_len=settings.random_min_len,
            max_len=settings.random_max_len,
            seed=settings.random_seed,
        )
        preview_end = preview_offset + preview_length
        shifted: list[tuple[float, float]] = []
        for start, end in full_intervals:
            overlap_start = max(start, preview_offset)
            overlap_end = min(end, preview_end)
            if overlap_end > overlap_start:
                shifted.append((overlap_start - preview_offset, overlap_end - preview_offset))
        return shifted

    def _new_preview_path(self) -> Path:
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return PREVIEW_DIR / f"preview_{timestamp}.mp4"

    def _manual_blocks(self, strict: bool) -> list[tuple[float, float]]:
        blocks: list[tuple[float, float]] = []
        if "Manual" not in self.bypass_mode.currentText():
            return blocks
        for index, row in enumerate(self.block_rows, start=1):
            raw_start, raw_end = row.values()
            try:
                start = ffmpeg_utils.parse_timecode(raw_start)
                end = ffmpeg_utils.parse_timecode(raw_end)
                if start is None or end is None:
                    raise ValueError("manual block times cannot be auto")
                if end <= start:
                    raise ValueError("end must be after start")
            except Exception as exc:  # noqa: BLE001
                if strict:
                    raise ValueError(f"Manual block {index} is invalid: {exc}") from exc
                continue
            blocks.append((start, end))
        return blocks

    def _current_render_duration(self, strict: bool) -> float | None:
        total_duration = self._timeline_total_duration(strict=strict)
        if total_duration is None:
            return None
        try:
            start = ffmpeg_utils.parse_timecode(self.video_start.text()) or 0.0
            end = ffmpeg_utils.parse_timecode(self.video_end.text())
            resolved_end = total_duration if end is None else end
            if resolved_end <= start:
                raise ValueError("timeline end must be after timeline start")
            timeline_duration = max(0.0, min(resolved_end, total_duration) - start)
            if (
                self.match_timeline_to_audio.isChecked()
                and self.audio_mode.currentText() in {AUDIO_EXTERNAL, AUDIO_MIX}
                and self.audio_path.text().strip()
            ):
                audio_duration = self._selected_audio_duration(strict=strict)
                if audio_duration and audio_duration > 0:
                    if self.match_timeline_mode.currentText() == MATCH_TRIM:
                        timeline_duration = min(timeline_duration, audio_duration)
                    else:
                        timeline_duration = audio_duration
            max_video_length = self._selected_max_video_length(strict=strict)
            if max_video_length is not None:
                if self.random_clip_assembly.isChecked():
                    return max_video_length
                return min(timeline_duration, max_video_length)
            return timeline_duration
        except Exception as exc:  # noqa: BLE001
            if strict:
                raise
            self.coverage_detail.setText(str(exc))
            return None


    def render_finished(self, output_path: str) -> None:
        self._set_render_controls_enabled(True)
        self.progress.setValue(100)
        if self.active_task == "preview":
            self.last_preview_path = output_path
            self.open_preview_button.setEnabled(True)
            self.open_preview_button.show()
            self.append_log(f"Finished preview: {output_path}")
            self.open_preview()
        elif self.active_task == "batch":
            outputs = [line for line in output_path.splitlines() if line.strip()]
            self.last_output_path = outputs[-1] if outputs else None
            self.open_output_button.setEnabled(bool(outputs))
            self.open_output_button.setVisible(bool(outputs))
            self.batch_status_label.setText(self.tr("status.batch_complete", count=len(outputs)))
            if outputs:
                size_lines = [f"{Path(path).name}: {self._file_size_text(path)}" for path in outputs]
                self.final_size_label.setText(self.tr("status.final_size", size=self._file_size_text(outputs[-1])))
                self.append_log("Finished batch render:")
                for path in outputs:
                    self.append_log(f"  {path} ({self._file_size_text(path)})")
                QMessageBox.information(
                    self,
                    APP_NAME,
                    self.tr("dialog.batch_complete", details="\n".join(size_lines)),
                )
            else:
                self.append_log("Batch finished without output files.")
        else:
            self.last_output_path = output_path
            self.open_output_button.setEnabled(True)
            self.open_output_button.show()
            size_text = self._file_size_text(output_path)
            self.final_size_label.setText(self.tr("status.final_size", size=size_text))
            self.append_log(f"Finished render: {output_path}")
            self.append_log(f"Final output size: {size_text}")
            QMessageBox.information(self, APP_NAME, self.tr("dialog.render_complete", path=output_path))


    def render_failed(self, message: str) -> None:
        self._set_render_controls_enabled(True)
        task_key = "task.preview" if self.active_task == "preview" else ("task.batch" if self.active_task == "batch" else "task.render")
        label = self.tr(task_key)
        self.append_log(f"{label} failed: {message}")
        self.last_render_error = message
        QMessageBox.critical(self, APP_NAME, self.tr("dialog.task_failed", task=label, message=message))

    def thread_finished(self) -> None:
        self.worker = None

    def append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def copy_report(self) -> None:
        QApplication.clipboard().setText(self._support_report_text())
        self.append_log("Report copied to clipboard.")

    def _support_report_text(self) -> str:
        output_values = self._output_size_values()
        optimize_values = self._optimize_values()
        timeline_names = [
            Path(str(item.get("path", ""))).name or "(unnamed)"
            for item in self.timeline_items[:12]
        ]
        if len(self.timeline_items) > len(timeline_names):
            timeline_names.append(f"... {len(self.timeline_items) - len(timeline_names)} more")
        lines = [
            f"{APP_NAME} support report",
            f"Version: v{APP_VERSION}",
            f"Platform: {platform.platform()}",
            f"Python: {platform.python_version()}",
            f"ffmpeg: {self._binary_status('ffmpeg')}",
            f"ffprobe: {self._binary_status('ffprobe')}",
            f"Timeline items: {len(self.timeline_items)}",
            f"Timeline filenames: {', '.join(timeline_names) if timeline_names else '(none)'}",
            f"Audio mode: {self.audio_mode.currentText()}",
            f"worky music mode: {'on' if self.worky_music_mode.isChecked() else 'off'}",
            f"External audio: {self._display_path(self.audio_path.text().strip()) if self.audio_path.text().strip() else '(none)'}",
            f"Style preset: {self.preset.currentText()}",
            f"Chunky blocks: {'on' if self.chunky_blocks.isChecked() else 'off'}",
            (
                "Output settings: "
                f"{output_values['preset']}, max {output_values['max_width']} px, "
                f"{output_values['fps']} fps, CRF {output_values['crf']}, "
                f"audio {output_values['audio_kbps']} kbps"
            ),
            (
                "Optimize: "
                f"{'on' if optimize_values['enabled'] else 'off'}, "
                f"{optimize_values['preset']}, target {optimize_values['target_mb']} MB"
            ),
            f"Last output: {self._display_path(self.last_output_path or self.output_path.text().strip())}",
            f"Last render error: {self._sanitize_text(self.last_render_error) if self.last_render_error else '(none)'}",
            "",
            "Log:",
            self._sanitize_text(self.log_output.toPlainText().strip() or "(empty)"),
        ]
        return "\n".join(lines).strip() + "\n"

    def _binary_status(self, name: str) -> str:
        try:
            return self._display_path(ffmpeg_utils.require_binary(name))
        except ffmpeg_utils.FFmpegError:
            return "missing"

    def _display_path(self, raw_path: str | None) -> str:
        if not raw_path:
            return "(none)"
        return self._sanitize_text(str(raw_path))

    def _sanitize_text(self, value: str) -> str:
        home_candidates = {str(Path.home())}
        username = os.environ.get("USER") or os.environ.get("USERNAME")
        if username:
            home_candidates.add(str(Path("/Users") / username))
        for home in sorted((path for path in home_candidates if path), key=len, reverse=True):
            value = value.replace(home, "~")
        return value

    def check_for_updates(self, manual: bool = False) -> None:
        if self.update_worker and self.update_worker.isRunning():
            if manual:
                self.append_log("Update check already running.")
            return
        self.update_status_label.setText(self.tr("status.update_checking", version=APP_VERSION))
        self.check_update_button.setEnabled(False)
        self.download_update_button.setText(self.tr("button.download_update"))
        self.download_update_button.setEnabled(False)
        self.download_update_button.hide()
        self.latest_release_url = RELEASES_LATEST_URL
        self.update_worker = UpdateCheckThread(APP_VERSION, self)
        self.update_worker.update_checked.connect(self.update_check_finished)
        self.update_worker.update_failed.connect(self.update_check_failed)
        self.update_worker.finished.connect(self.update_check_thread_finished)
        self.update_worker.start()

    def update_check_finished(self, latest_tag: str, is_newer: bool, release_url: str, detail: str = "") -> None:
        latest_display = latest_tag if latest_tag.startswith("v") else f"v{latest_tag}"
        self.latest_release_url = release_url or RELEASES_LATEST_URL
        if is_newer:
            self.update_status_label.setText(
                self.tr("status.update_available", version=APP_VERSION, latest=latest_display)
            )
            self.download_update_button.setText(self.tr("button.download_update"))
            self.download_update_button.setEnabled(True)
            self.download_update_button.show()
            self.append_log(f"Update available: {latest_display}")
        else:
            self.update_status_label.setText(self.tr("status.update_current", version=APP_VERSION))
            self.download_update_button.setEnabled(False)
            self.download_update_button.hide()
            self.append_log(f"Update check complete: current release is {latest_display}.")
        if detail and "fallback" in detail.lower():
            self.append_log(f"Update check used fallback: {detail}")
        self.check_update_button.setEnabled(True)

    def update_check_failed(self, message: str) -> None:
        self.update_status_label.setText(self.tr("status.update_failed", version=APP_VERSION))
        self.latest_release_url = RELEASES_LATEST_URL
        self.download_update_button.setText(self.tr("button.check_manually"))
        self.download_update_button.setEnabled(True)
        self.download_update_button.show()
        self.check_update_button.setEnabled(True)
        self.append_log(f"Update check unavailable - network/API error: {message}")

    def update_check_thread_finished(self) -> None:
        self.update_worker = None

    def open_update_download(self) -> None:
        QDesktopServices.openUrl(QUrl(self.latest_release_url or RELEASES_LATEST_URL))

    def _file_size_text(self, path: str) -> str:
        try:
            size_mb = Path(path).expanduser().stat().st_size / (1024 * 1024)
        except OSError:
            return "unknown"
        return f"{size_mb:.2f} MB"

    def _has_resettable_project_state(self) -> bool:
        if self.timeline_items or self.block_rows:
            return True
        text_defaults = (
            (self.audio_path.text(), ""),
            (self.output_path.text(), ""),
            (self.video_start.text(), "0:00"),
            (self.video_end.text(), "auto"),
            (self.audio_start.text(), "0:00"),
            (self.audio_end.text(), "auto"),
            (self.audio_timeline_start.text(), "0:00"),
            (self.audio_timeline_end.text(), "auto"),
            (self.max_video_length.text(), ""),
        )
        if any(value.strip() != default for value, default in text_defaults):
            return True
        if self.last_output_path or self.last_preview_path or self.last_render_error:
            return True
        if (
            self.audio_mode.currentText() != AUDIO_SILENT
            or self.match_timeline_to_audio.isChecked()
            or self.worky_music_mode.isChecked()
            or self.random_clip_assembly.isChecked()
        ):
            return True
        if self.match_timeline_mode.currentText() != MATCH_SPEED:
            return True
        if self.preview_duration.currentText() != "5s":
            return True
        if self.preset.currentText() != "Classic ANSI" or self.chunky_blocks.isChecked():
            return True
        if self.width_slider.value() != 120 or self.intensity_slider.value() != 65:
            return True
        if (
            self.fit_mode.currentText() != "Fill/Crop"
            or self.anchor_mode.currentText() != "Center"
            or self.letterbox_background.currentText() != "Black"
            or not self.upper_bias.isChecked()
            or self.framing_x_slider.value() != 0
            or self.framing_y_slider.value() != 0
            or self.framing_zoom_slider.value() != 0
        ):
            return True
        if (
            self.dither_mode.currentText() != "None"
            or self.transition_mode.currentText() != DEFAULT_TRANSITION_MODE
            or self.transition_intensity_slider.value() != 55
            or self.ending_mode.currentText() != DEFAULT_ENDING_MODE
            or self.loop_friendly.isChecked()
        ):
            return True
        for key, checkbox in self.effect_checks.items():
            if checkbox.isChecked() != (key not in DEFAULT_OFF_EFFECTS):
                return True
        if self.bypass_mode.currentText() != BYPASS_FULL_ANSI or self.random_percent.value() != 10:
            return True
        if (
            self.output_size_preset.currentText() != "Full Quality"
            or self.target_size_enabled.isChecked()
            or self.optimize_preset.currentText() != "29 MB Text Limit"
            or abs(self.target_size_mb.value() - 29.0) > 0.01
        ):
            return True
        default_batch = {"29 MB Text Limit", "Chunkcore"}
        if self.batch_enabled.isChecked():
            return True
        return any(checkbox.isChecked() != (name in default_batch) for name, checkbox in self.batch_checks.items())

    def reset_project(self) -> None:
        if self._has_resettable_project_state():
            response = QMessageBox.question(
                self,
                APP_NAME,
                self.tr("dialog.reset"),
                QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if response != QMessageBox.StandardButton.Reset:
                return

        self.timeline_items.clear()
        self._refresh_timeline_table()
        self.video_path.clear()
        self.audio_path.clear()
        self.output_path.clear()
        self.audio_duration_seconds = None
        self.audio_duration.setText(self.tr("status.duration_empty"))
        self.video_duration_seconds = None
        self.video_duration.setText(self.tr("status.timeline_none"))
        self.video_start.setText("0:00")
        self.video_end.setText("auto")
        self.audio_start.setText("0:00")
        self.audio_end.setText("auto")
        self.audio_timeline_start.setText("0:00")
        self.audio_timeline_end.setText("auto")
        self.max_video_length.clear()
        self._set_combo_text(self.audio_mode, AUDIO_SILENT)
        self.worky_music_mode.setChecked(False)
        self.match_timeline_to_audio.setChecked(False)
        self.random_clip_assembly.setChecked(False)
        self._set_combo_text(self.match_timeline_mode, MATCH_SPEED)

        self._set_combo_text(self.preset, "Classic ANSI")
        self.chunky_blocks.setChecked(False)
        for key, checkbox in self.effect_checks.items():
            checkbox.setChecked(key not in DEFAULT_OFF_EFFECTS)
        self.width_slider.setValue(120)
        self.intensity_slider.setValue(65)

        self._set_combo_text(self.fit_mode, "Fill/Crop")
        self._set_combo_text(self.anchor_mode, "Center")
        self._set_combo_text(self.letterbox_background, "Black")
        self.upper_bias.setChecked(True)
        self.framing_x_slider.setValue(0)
        self.framing_y_slider.setValue(0)
        self.framing_zoom_slider.setValue(0)

        self._set_combo_text(self.dither_mode, "None")
        self._set_combo_text(self.transition_mode, DEFAULT_TRANSITION_MODE)
        self.transition_intensity_slider.setValue(55)
        self._set_combo_text(self.ending_mode, DEFAULT_ENDING_MODE)
        self.loop_friendly.setChecked(False)

        self._set_combo_text(self.bypass_mode, BYPASS_FULL_ANSI)
        self.random_percent.setValue(10)
        self.random_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.weird_seed = random.SystemRandom().randint(1, 2_147_483_647)
        self.weird_seed_label.setText(self.tr("status.weird_seed", seed=self.weird_seed))
        for row in list(self.block_rows):
            self.remove_manual_block(row)

        self._set_combo_text(self.output_size_preset, "Full Quality")
        self.target_size_enabled.setChecked(False)
        self._set_combo_text(self.optimize_preset, "29 MB Text Limit")
        self.target_size_mb.setValue(29.0)
        self.batch_enabled.setChecked(False)
        for name, checkbox in self.batch_checks.items():
            checkbox.setChecked(name in {"29 MB Text Limit", "Chunkcore"})
        self.batch_status_label.setText(self.tr("status.batch_off"))

        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText(self.tr("status.no_source"))
        self.progress.setValue(0)
        self.last_output_path = None
        self.last_preview_path = None
        self.last_render_error = ""
        self.open_output_button.hide()
        self.open_output_button.setEnabled(False)
        self.open_preview_button.hide()
        self.open_preview_button.setEnabled(False)
        self.final_size_label.setText(self.tr("status.final_size_empty"))
        self._set_combo_text(self.preview_duration, "5s")
        self.log_output.clear()
        self.append_log(self.tr("log.project_reset"))
        self._refresh_slider_labels()
        self._apply_output_size_preset()
        self._apply_optimize_preset()
        self._update_audio_controls()
        self._update_coverage_controls()
        self._update_coverage_summary()
        self._update_preset_description()
        self._save_settings()

    def save_project_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("file.export_recipe_title"),
            str(Path.home() / "wzrdvid-recipe.json"),
            "WZRD.VID recipe (*.json)",
        )
        if not path:
            return
        if Path(path).suffix.lower() != ".json":
            path = f"{path}.json"
        try:
            Path(path).write_text(json.dumps(self._project_state(), indent=2))
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.export_recipe_failed", error=exc))
            return
        self.append_log(f"Exported recipe: {path}")

    def load_project_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("file.import_recipe_title"),
            str(Path.home()),
            "WZRD.VID recipe or legacy project preset (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.import_recipe_failed", error=exc))
            return
        if not isinstance(data, dict):
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.recipe_invalid"))
            return
        self._apply_project_state(data)
        if self.audio_path.text().strip() and Path(self.audio_path.text().strip()).exists():
            self._probe_duration(self.audio_path.text().strip(), self.audio_duration, "audio")
        self._after_timeline_changed(save=False)
        self._save_settings()
        self.append_log(f"Imported recipe: {path}")

    def open_output_folder(self) -> None:
        raw_path = self.last_output_path or self.output_path.text().strip()
        if not raw_path:
            QMessageBox.information(self, APP_NAME, self.tr("dialog.no_output"))
            return
        folder = Path(raw_path).expanduser().parent
        if not folder.exists():
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.output_folder_missing", folder=folder))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def open_preview(self) -> None:
        if not self.last_preview_path:
            QMessageBox.information(self, APP_NAME, self.tr("dialog.no_preview"))
            return
        preview_path = Path(self.last_preview_path).expanduser()
        if not preview_path.exists():
            QMessageBox.warning(self, APP_NAME, self.tr("dialog.preview_file_missing", path=preview_path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(preview_path)))

    def _load_settings(self) -> None:
        if not SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(SETTINGS_PATH.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            self.append_log(f"Could not load settings: {exc}")
            return

        self._apply_project_state(data)

        if self.audio_path.text().strip() and Path(self.audio_path.text().strip()).exists():
            self._probe_duration(self.audio_path.text().strip(), self.audio_duration, "audio")
        self._after_timeline_changed(save=False)

    def _save_settings(self) -> None:
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = self._project_state()
            data["experimental_frame_pipe"] = self.experimental_frame_pipe.isChecked()
            SETTINGS_PATH.write_text(json.dumps(data, indent=2))
        except OSError as exc:
            self.append_log(f"Could not save settings: {exc}")

    def _project_state(self) -> dict:
        self._sync_timeline_from_table()
        output_values = self._output_size_values()
        return {
            "app": APP_NAME,
            "schema_version": 4,
            "ui_language": self.ui_language,
            "timeline_items": self.timeline_items,
            "video_path": self.video_path.text().strip(),
            "audio_path": self.audio_path.text().strip(),
            "output_path": self.output_path.text().strip(),
            "video_start": self.video_start.text().strip(),
            "video_end": self.video_end.text().strip(),
            "audio_start": self.audio_start.text().strip(),
            "audio_end": self.audio_end.text().strip(),
            "audio_timeline_start": self.audio_timeline_start.text().strip(),
            "audio_timeline_end": self.audio_timeline_end.text().strip(),
            "max_video_length": self.max_video_length.text().strip(),
            "random_clip_assembly": self.random_clip_assembly.isChecked(),
            "audio_mode": self.audio_mode.currentText(),
            "worky_music_mode": self.worky_music_mode.isChecked(),
            "match_timeline_to_audio": self.match_timeline_to_audio.isChecked(),
            "match_timeline_mode": self.match_timeline_mode.currentText(),
            "preset": self.preset.currentText(),
            "chunky_blocks": self.chunky_blocks.isChecked(),
            "width_chars": self.width_slider.value(),
            "fps": int(output_values["fps"]),
            "effect_intensity": self.intensity_slider.value(),
            "resolution_index": self.resolution_slider.value(),
            "output_size_preset": self.output_size_preset.currentText(),
            "custom_max_width": self.max_width_spin.value(),
            "custom_fps": self.output_fps_spin.value(),
            "custom_crf": self.crf_spin.value(),
            "custom_audio_kbps": self.audio_bitrate_spin.value(),
            "target_size_enabled": self.target_size_enabled.isChecked(),
            "target_size_mb": self.target_size_mb.value(),
            "optimize_preset": self.optimize_preset.currentText(),
            "effects": {key: checkbox.isChecked() for key, checkbox in self.effect_checks.items()},
            "bypass_mode": self.bypass_mode.currentText(),
            "random_percent": self.random_percent.value(),
            "random_seed": self.random_seed,
            "weird_seed": self.weird_seed,
            "framing_fit_mode": self.fit_mode.currentText(),
            "framing_anchor": self.anchor_mode.currentText(),
            "framing_offset_x": self.framing_x_slider.value(),
            "framing_offset_y": self.framing_y_slider.value(),
            "framing_zoom": self.framing_zoom_slider.value(),
            "letterbox_background": self.letterbox_background.currentText(),
            "preserve_upper_bias": self.upper_bias.isChecked(),
            "dither_mode": self.dither_mode.currentText(),
            "transition_mode": self.transition_mode.currentText(),
            "transition_intensity": self.transition_intensity_slider.value(),
            "ending_mode": self.ending_mode.currentText(),
            "loop_friendly": self.loop_friendly.isChecked(),
            "preview_from": self.preview_from.currentText(),
            "preview_duration": self.preview_duration.currentText(),
            "preview_custom": self.preview_custom.text().strip(),
            "manual_blocks": [
                {"start": start, "end": end} for start, end in (row.values() for row in self.block_rows)
            ],
            "batch_enabled": self.batch_enabled.isChecked(),
            "batch_variants": [
                name for name, checkbox in self.batch_checks.items() if checkbox.isChecked()
            ],
        }

    def _apply_project_state(self, data: dict) -> None:
        language = str(data.get("ui_language", self.ui_language or "system"))
        self.ui_language = language if language in {code for code, _name in SUPPORTED_LANGUAGES} else "system"
        self.video_path.setText(str(data.get("video_path", "")))
        self.audio_path.setText(str(data.get("audio_path", "")))
        self.output_path.setText(str(data.get("output_path", "")))
        self.timeline_items = self._state_timeline_items(data)
        self._refresh_timeline_table()
        self.video_start.setText(str(data.get("video_start", "0:00")))
        self.video_end.setText(str(data.get("video_end", "auto")))
        self.audio_start.setText(str(data.get("audio_start", "0:00")))
        self.audio_end.setText(str(data.get("audio_end", "auto")))
        self.audio_timeline_start.setText(str(data.get("audio_timeline_start", "0:00")))
        self.audio_timeline_end.setText(str(data.get("audio_timeline_end", "auto")))
        self.max_video_length.setText(str(data.get("max_video_length", "")))
        self.random_clip_assembly.setChecked(bool(data.get("random_clip_assembly", False)))
        if "experimental_frame_pipe" in data:
            self.experimental_frame_pipe.setChecked(bool(data.get("experimental_frame_pipe", False)))
        loaded_audio_mode = self._canonical_audio_mode(
            str(data.get("audio_mode", AUDIO_EXTERNAL if self.audio_path.text().strip() else AUDIO_SOURCE))
        )
        self._set_combo_text(self.audio_mode, loaded_audio_mode)
        self.worky_music_mode.setChecked(bool(data.get("worky_music_mode", False)))
        self.match_timeline_to_audio.setChecked(bool(data.get("match_timeline_to_audio", False)))
        self._set_combo_text(self.match_timeline_mode, str(data.get("match_timeline_mode", MATCH_SPEED)))
        self._set_combo_text(self.preset, str(data.get("preset", "Classic ANSI")))
        self._set_combo_text(self.bypass_mode, str(data.get("bypass_mode", BYPASS_FULL_ANSI)))
        self.chunky_blocks.setChecked(bool(data.get("chunky_blocks", False)))

        self.width_slider.setValue(int(data.get("width_chars", 120)))
        self.fps_slider.setValue(int(data.get("fps", 24)))
        self.intensity_slider.setValue(int(data.get("effect_intensity", 65)))
        self.resolution_slider.setValue(int(data.get("resolution_index", 1)))
        legacy_resolution_index = max(
            0,
            min(len(RESOLUTIONS) - 1, int(data.get("resolution_index", 1))),
        )
        legacy_max_width = RESOLUTIONS[legacy_resolution_index][1][0]
        self._set_combo_text(
            self.output_size_preset,
            str(data.get("output_size_preset", "Full Quality")),
        )
        self.max_width_spin.setValue(int(data.get("custom_max_width", legacy_max_width)))
        self.output_fps_spin.setValue(int(data.get("custom_fps", data.get("fps", 24))))
        self.crf_spin.setValue(int(data.get("custom_crf", 32)))
        self.audio_bitrate_spin.setValue(int(data.get("custom_audio_kbps", 64)))
        self.target_size_enabled.setChecked(bool(data.get("target_size_enabled", False)))
        self._set_combo_text(
            self.optimize_preset,
            str(data.get("optimize_preset", "29 MB Text Limit")),
        )
        self.target_size_mb.setValue(float(data.get("target_size_mb", 29.0)))
        self.random_percent.setValue(int(data.get("random_percent", 10)))
        self.random_seed = int(data.get("random_seed", self.random_seed))
        self.weird_seed = int(data.get("weird_seed", self.weird_seed))
        self.weird_seed_label.setText(self.tr("status.weird_seed", seed=self.weird_seed))
        self._set_combo_text(self.fit_mode, str(data.get("framing_fit_mode", "Fill/Crop")))
        self._set_combo_text(self.anchor_mode, str(data.get("framing_anchor", "Center")))
        self.framing_x_slider.setValue(int(data.get("framing_offset_x", 0)))
        self.framing_y_slider.setValue(int(data.get("framing_offset_y", 0)))
        self.framing_zoom_slider.setValue(int(data.get("framing_zoom", 0)))
        self._set_combo_text(self.letterbox_background, str(data.get("letterbox_background", "Black")))
        self.upper_bias.setChecked(bool(data.get("preserve_upper_bias", True)))
        self._set_combo_text(self.dither_mode, str(data.get("dither_mode", "None")))
        self._set_combo_text(self.transition_mode, str(data.get("transition_mode", DEFAULT_TRANSITION_MODE)))
        self.transition_intensity_slider.setValue(int(data.get("transition_intensity", 55)))
        self._set_combo_text(self.ending_mode, str(data.get("ending_mode", DEFAULT_ENDING_MODE)))
        self.loop_friendly.setChecked(bool(data.get("loop_friendly", False)))
        self._set_combo_text(self.preview_from, str(data.get("preview_from", "Start")))
        self._set_combo_text(self.preview_duration, str(data.get("preview_duration", "5s")))
        self.preview_custom.setText(str(data.get("preview_custom", "0:00")))
        self.batch_enabled.setChecked(bool(data.get("batch_enabled", False)))
        selected_variants = data.get("batch_variants", ["29 MB Text Limit", "Chunkcore"])
        if not isinstance(selected_variants, list):
            selected_variants = []
        for name, checkbox in self.batch_checks.items():
            checkbox.setChecked(name in selected_variants)

        effects = data.get("effects", {})
        if isinstance(effects, dict):
            for key, checkbox in self.effect_checks.items():
                checkbox.setChecked(bool(effects.get(key, True)))

        for row in list(self.block_rows):
            self.remove_manual_block(row)
        for block in data.get("manual_blocks", []):
            if isinstance(block, dict):
                self.add_manual_block(str(block.get("start", "0:12")), str(block.get("end", "0:18")))

        self.last_output_path = None
        self.last_preview_path = None
        self.open_output_button.hide()
        self.open_output_button.setEnabled(False)
        self.open_preview_button.hide()
        self.open_preview_button.setEnabled(False)
        self._refresh_slider_labels()
        self._apply_output_size_preset()
        self._apply_optimize_preset()
        self._update_preview_controls()
        self._update_audio_controls()
        self._update_preset_description()
        self._update_coverage_controls()
        self._update_coverage_summary()
        self._apply_translations()

    def _state_timeline_items(self, data: dict) -> list[dict[str, object]]:
        raw_items = data.get("timeline_items", [])
        items: list[dict[str, object]] = []
        if isinstance(raw_items, list):
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                path = str(raw.get("path", ""))
                if not path:
                    continue
                kind = self._guess_source_kind(path, str(raw.get("kind", "video")))
                duration = float(raw.get("duration", 0.0) or 0.0)
                if duration <= 0 and kind == "video" and Path(path).exists():
                    try:
                        duration = ffmpeg_utils.get_duration(path)
                    except Exception:  # noqa: BLE001
                        duration = 0.0
                if kind == "photo" and duration <= 0:
                    parsed_hold = ffmpeg_utils.parse_timecode(str(raw.get("photo_hold_duration", "3.0")))
                    duration = 3.0 if parsed_hold is None else parsed_hold
                has_audio = False
                include_audio = False
                if kind == "video" and Path(path).exists():
                    if "has_audio" in raw:
                        has_audio = bool(raw.get("has_audio", False))
                    else:
                        try:
                            has_audio = has_audio_stream(path)
                        except Exception:  # noqa: BLE001
                            has_audio = False
                    include_audio = bool(raw.get("include_audio", has_audio)) and has_audio
                items.append(
                    {
                        "path": path,
                        "kind": kind,
                        "duration": duration,
                        "trim_start": str(raw.get("trim_start", "0:00")),
                        "trim_end": str(raw.get("trim_end", "auto")),
                        "photo_hold_duration": str(raw.get("photo_hold_duration", "3.0")),
                        "has_audio": bool(has_audio),
                        "include_audio": bool(include_audio),
                    }
                )
        if items:
            return items

        legacy_video = str(data.get("video_path", ""))
        if legacy_video:
            duration = 0.0
            has_audio = False
            if Path(legacy_video).exists():
                try:
                    duration = ffmpeg_utils.get_duration(legacy_video)
                    has_audio = has_audio_stream(legacy_video)
                except Exception:  # noqa: BLE001
                    duration = 0.0
                    has_audio = False
            return [
                {
                    "path": legacy_video,
                    "kind": "video",
                    "duration": duration,
                    "trim_start": "0:00",
                    "trim_end": "auto",
                    "photo_hold_duration": "3.0",
                    "has_audio": has_audio,
                    "include_audio": has_audio,
                }
            ]
        return []

    def _canonical_audio_mode(self, value: str) -> str:
        aliases = {
            "External Music/Audio": AUDIO_EXTERNAL,
            "Keep source audio": AUDIO_SOURCE,
            "Source audio": AUDIO_SOURCE,
            "External + source audio": AUDIO_MIX,
        }
        return aliases.get(value, value)

    def _set_combo_text(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def closeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature.
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self,
                APP_NAME,
                self.tr("dialog.render_running"),
            )
            event.ignore()
            return
        if self.cache_cleanup_worker and self.cache_cleanup_worker.isRunning():
            self.cache_cleanup_worker.wait(500)
        self._save_settings()
        event.accept()


def main() -> int:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, False)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setFont(_default_app_font())
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
