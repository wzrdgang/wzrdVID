"""Video-to-ANSI-art renderer for WZRD.VID."""

from __future__ import annotations

import colorsys
import math
import random
import subprocess
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import ffmpeg_utils
from presets import get_preset


ProgressCallback = Callable[[int], None] | None
LogCallback = Callable[[str], None] | None
Interval = tuple[float, float]


OUTPUT_SIZE = (1280, 720)
RANDOM_CHUNK_MIN = 0.5
RANDOM_CHUNK_MAX = 3.0
BYPASS_FULL_ANSI = "Full ANSI"
BYPASS_RANDOM = "Random normal sections"
BYPASS_MANUAL = "Manual normal time blocks"
BYPASS_MANUAL_RANDOM = "Manual + random"
AUDIO_SILENT = "Silent"
AUDIO_EXTERNAL = "External only"
AUDIO_SOURCE = "Source audio only"
AUDIO_MIX = "External + selected source audio"
MATCH_SPEED = "Speed up/down timeline"
MATCH_TRIM = "Trim timeline to music"
MATCH_LOOP = "Loop timeline to music"
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
HEIC_EXTENSIONS = {".heic", ".heif"}

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/Library/Fonts/Menlo.ttc",
    "/Library/Fonts/Andale Mono.ttf",
]


@dataclass(frozen=True)
class TimelineItem:
    path: str
    kind: str = "video"
    duration: float = 0.0
    trim_start: float = 0.0
    trim_end: float | None = None
    photo_hold_duration: float = 3.0
    has_audio: bool = False
    include_audio: bool = False


@dataclass(frozen=True)
class TimelineSegment:
    path: str
    kind: str
    timeline_start: float
    duration: float
    source_start: float = 0.0
    source_end: float | None = None
    has_audio: bool = False
    include_audio: bool = False

    @property
    def timeline_end(self) -> float:
        return self.timeline_start + self.duration


@dataclass(frozen=True)
class RenderSettings:
    video_path: str
    output_path: str
    audio_path: str | None
    video_start: float
    video_end: float | None
    audio_start: float
    audio_end: float | None
    preset_name: str
    fps: int
    width_chars: int
    output_size: tuple[int, int] = OUTPUT_SIZE
    video_crf: int = 22
    audio_bitrate: str = "128k"
    audio_timeline_start: float = 0.0
    audio_timeline_end: float | None = None
    audio_mode: str = AUDIO_EXTERNAL
    worky_music_mode: bool = False
    match_timeline_to_audio: bool = False
    match_timeline_mode: str = MATCH_SPEED
    target_size_mb: float | None = None
    optimize_enabled: bool = False
    optimize_target_mb: float = 29.0
    chunky_blocks: bool = False
    effects: dict[str, bool] = field(default_factory=dict)
    effect_intensity: float = 1.0
    bypass_mode: str = BYPASS_FULL_ANSI
    manual_blocks: list[Interval] = field(default_factory=list)
    random_percent: float = 0.0
    random_seed: int | None = None
    random_min_len: float = RANDOM_CHUNK_MIN
    random_max_len: float = RANDOM_CHUNK_MAX
    weird_seed: int | None = None
    framing_fit_mode: str = "Fill/Crop"
    framing_anchor: str = "Center"
    framing_offset_x: int = 0
    framing_offset_y: int = 0
    framing_zoom: float = 0.0
    letterbox_background: str = "Black"
    preserve_upper_bias: bool = True
    dither_mode: str = "None"
    transition_mode: str = "CRT Flash"
    transition_intensity: float = 1.0
    ending_mode: str = "Fade Out"
    loop_friendly: bool = False
    timeline_items: list[TimelineItem] = field(default_factory=list)


@dataclass(frozen=True)
class PlaybackPlan:
    timeline_start: float
    timeline_end: float
    source_duration: float
    output_duration: float
    speed_factor: float = 1.0
    loop_timeline: bool = False


@dataclass(frozen=True)
class TextLayout:
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    cols: int
    rows: int
    char_width: int
    line_height: int
    x_offset: int
    y_offset: int


class RenderError(RuntimeError):
    """Raised when the ANSI render cannot be completed."""


def build_bypass_intervals(
    duration: float,
    mode: str,
    manual_blocks: list[Any],
    random_percent: float,
    min_len: float,
    max_len: float,
    seed: int | None,
) -> list[Interval]:
    """Build sorted, clamped, non-overlapping normal-video intervals."""
    if duration <= 0:
        return []

    normalized = (mode or BYPASS_FULL_ANSI).strip().lower()
    use_manual = "manual" in normalized
    use_random = "random" in normalized
    if not use_manual and not use_random:
        return []

    intervals: list[Interval] = []
    if use_manual:
        for block in manual_blocks or []:
            start, end = _coerce_block(block)
            intervals.append((start, end))
    intervals = _merge_intervals(intervals, duration)

    if use_random:
        random_percent = max(0.0, min(100.0, float(random_percent)))
        target_random = duration * (random_percent / 100.0)
        intervals = _add_random_intervals(
            intervals=intervals,
            duration=duration,
            target_seconds=target_random,
            min_len=max(0.05, float(min_len)),
            max_len=max(float(min_len), float(max_len)),
            seed=seed,
        )

    return _merge_intervals(intervals, duration)


def is_bypass_time(t: float, intervals: list[Interval]) -> bool:
    """Return True when the output timestamp should remain normal video."""
    return any(start <= t < end for start, end in intervals)


def render_project(
    settings: RenderSettings,
    progress: ProgressCallback = None,
    log: LogCallback = None,
) -> str:
    """Render the selected video as ANSI-style video and write an MP4."""
    settings = _expanded_settings(settings)
    _validate_settings(settings)
    ffmpeg_utils.require_binary("ffmpeg")
    ffmpeg_utils.require_binary("ffprobe")

    output_path = Path(settings.output_path).expanduser()
    if output_path.suffix.lower() != ".mp4":
        output_path = output_path.with_suffix(".mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _emit(log, "Probing selected media.")
    timeline_segments, timeline_duration = _build_timeline(settings)
    audio_mode = _audio_mode(settings)
    external_audio = _uses_external_audio(settings)

    audio_start = settings.audio_start
    audio_end = settings.audio_end
    selected_audio_duration: float | None = None
    selected_audio_clip_duration: float | None = None
    if external_audio:
        audio_duration = ffmpeg_utils.get_audio_duration(settings.audio_path)
        audio_start, audio_end = ffmpeg_utils.validate_time_range(
            audio_start,
            audio_end,
            audio_duration,
            "Audio",
        )
        selected_audio_clip_duration = audio_end - audio_start
        selected_audio_duration = (
            _external_audio_match_duration(settings, selected_audio_clip_duration)
            if settings.match_timeline_to_audio
            else selected_audio_clip_duration
        )

    playback = _playback_plan(
        settings,
        timeline_duration,
        selected_audio_duration=selected_audio_duration,
    )
    render_duration = playback.output_duration
    source_count = len({segment.path for segment in timeline_segments})
    _emit(
        log,
        f"Timeline: {len(timeline_segments)} segment(s), {source_count} source file(s), "
        f"{ffmpeg_utils.format_duration(playback.source_duration)} selected.",
    )
    source_audio = _uses_source_audio(settings)
    if settings.match_timeline_to_audio and audio_mode == AUDIO_MIX:
        _emit(log, "Source audio mixing is disabled when matching timeline length to music. Using external audio only.")
        source_audio = False
    if audio_mode == AUDIO_MIX and external_audio and source_audio:
        _emit(log, f"Audio: mixing external track ({ffmpeg_utils.format_duration(selected_audio_clip_duration)}) with selected source audio.")
    elif external_audio:
        _emit(log, f"Audio: external track, {ffmpeg_utils.format_duration(selected_audio_clip_duration)} selected.")
    elif source_audio:
        _emit(log, "Audio: keeping selected source timeline audio when available.")
    else:
        _emit(log, "Audio: silent output.")
    if external_audio and settings.audio_timeline_start > 0:
        _emit(log, f"External audio starts in video at {ffmpeg_utils.format_duration(settings.audio_timeline_start)}.")
    if external_audio and settings.audio_timeline_end is not None:
        _emit(log, f"External audio stops in video at {ffmpeg_utils.format_duration(settings.audio_timeline_end)}.")
    if external_audio and settings.worky_music_mode:
        _emit(log, "worky_music_profile_v1: external audio becomes tiny mono broadcast texture.")
    if settings.match_timeline_to_audio and external_audio:
        if playback.loop_timeline:
            _emit(log, f"Match to music: looping visual timeline to {ffmpeg_utils.format_duration(render_duration)}.")
        elif settings.match_timeline_mode == MATCH_TRIM:
            _emit(log, f"Match to music: trimming visual timeline to {ffmpeg_utils.format_duration(render_duration)}.")
        else:
            _emit(log, f"Match to music: visual speed factor {playback.speed_factor:.3f}x for {ffmpeg_utils.format_duration(render_duration)} output.")

    planned_audio = external_audio or source_audio
    target_bitrate = ffmpeg_utils.target_video_bitrate(
        settings.target_size_mb,
        render_duration,
        settings.audio_bitrate if planned_audio else None,
    )
    if target_bitrate is not None:
        _emit(
            log,
            f"Encoding target: {settings.target_size_mb:.1f} MB total, "
            f"video bitrate about {target_bitrate / 1000:.0f} kbps.",
        )
    else:
        audio_note = f", audio {settings.audio_bitrate}" if planned_audio else ""
        _emit(log, f"Encoding target: H.264 CRF {settings.video_crf}{audio_note}.")

    bypass_intervals = build_bypass_intervals(
        duration=render_duration,
        mode=settings.bypass_mode,
        manual_blocks=settings.manual_blocks,
        random_percent=settings.random_percent,
        min_len=settings.random_min_len,
        max_len=settings.random_max_len,
        seed=settings.random_seed,
    )
    bypass_seconds = _interval_total(bypass_intervals)
    if bypass_intervals:
        _emit(
            log,
            f"Bypass ANSI: {len(bypass_intervals)} normal section(s), "
            f"{bypass_seconds / render_duration * 100:.1f}% of output.",
        )
    else:
        _emit(log, "Bypass ANSI: full ANSI render.")

    preset = get_preset(settings.preset_name)
    if preset.get("profile") == "public_access_v1":
        _emit(log, "PUBLIC ACCESS renderer: camcorder dub, RF noise, tracking wear; ANSI coverage controls still apply.")
    chunky_blocks = settings.chunky_blocks or preset.get("render_mode") == "chunky_blocks"
    layout = make_text_layout(settings.width_chars, settings.output_size, chunky_blocks=chunky_blocks)
    frame_count = max(1, math.ceil(render_duration * settings.fps))
    _emit(
        log,
        f"Rendering {frame_count} frames at {settings.fps} fps "
        f"({settings.width_chars} columns, {layout.rows} rows, "
        f"{settings.output_size[0]}x{settings.output_size[1]}).",
    )
    if chunky_blocks:
        _emit(log, "Chunky block mode: using large shaded block glyphs.")
    _emit(log, f"Framing: {settings.framing_fit_mode}, anchor {settings.framing_anchor}, offset {settings.framing_offset_x:+d}/{settings.framing_offset_y:+d}.")
    if settings.dither_mode != "None":
        _emit(log, f"Dither mode: {settings.dither_mode}.")
    if settings.transition_mode != "Hard Cut":
        _emit(log, f"Transitions: {settings.transition_mode}.")
    if settings.ending_mode != "Hard Cut" or settings.loop_friendly:
        _emit(log, f"Ending: {settings.ending_mode}{' + loop-friendly' if settings.loop_friendly else ''}.")
    if any(Path(segment.path).suffix.lower() in HEIC_EXTENSIONS for segment in timeline_segments if segment.kind == "photo"):
        _emit(log, "HEIC/HEIF stills: applying subtle 3-second automatic motion loop.")
    _emit_progress(progress, 5)

    with tempfile.TemporaryDirectory(prefix="wzrd_vid_render_") as temp_root:
        temp_root_path = Path(temp_root)
        frames_dir = temp_root_path / "frames"
        frames_dir.mkdir()
        silent_video = temp_root_path / "silent.mp4"

        _render_frames(
            settings=settings,
            preset=preset,
            layout=layout,
            timeline_segments=timeline_segments,
            playback=playback,
            frame_count=frame_count,
            bypass_intervals=bypass_intervals,
            frames_dir=frames_dir,
            progress=progress,
            log=log,
        )

        _emit(log, "Encoding rendered frames to MP4.")
        _emit_progress(progress, 90)
        ffmpeg_utils.encode_frames_to_mp4(
            frames_dir / "frame_%06d.png",
            settings.fps,
            silent_video,
            log=log,
            crf=settings.video_crf,
            video_bitrate=target_bitrate,
        )

        source_audio_path: Path | None = None
        if source_audio:
            _emit(log, "Building selected source timeline audio.")
            source_audio_path = ffmpeg_utils.build_timeline_audio(
                timeline_segments,
                playback.timeline_start,
                render_duration,
                temp_root_path / "source_audio.m4a",
                temp_root_path / "source_audio_parts",
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=_audio_fade_duration(settings, render_duration),
                log=log,
            )

        if external_audio and source_audio_path is not None and audio_mode == AUDIO_MIX and not settings.match_timeline_to_audio:
            _emit(log, "Mixing external audio with selected source audio.")
            _emit_progress(progress, 95)
            mixed_audio = ffmpeg_utils.mix_external_and_source_audio(
                settings.audio_path,
                source_audio_path,
                temp_root_path / "mixed_audio.m4a",
                audio_start,
                audio_end,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                worky_music_mode=settings.worky_music_mode,
                external_offset=settings.audio_timeline_start,
                external_output_end=settings.audio_timeline_end,
                log=log,
            )
            ffmpeg_utils.mux_audio(
                silent_video,
                mixed_audio,
                output_path,
                0.0,
                None,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=0.0,
                log=log,
            )
        elif external_audio:
            _emit(log, "Muxing selected external audio into final MP4.")
            _emit_progress(progress, 95)
            ffmpeg_utils.mux_audio(
                silent_video,
                settings.audio_path,
                output_path,
                audio_start,
                audio_end,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=_audio_fade_duration(settings, render_duration),
                audio_offset=settings.audio_timeline_start,
                audio_output_end=settings.audio_timeline_end,
                worky_music_mode=settings.worky_music_mode,
                log=log,
            )
        elif source_audio_path is not None:
            _emit(log, "Muxing selected source timeline audio into final MP4.")
            _emit_progress(progress, 95)
            ffmpeg_utils.mux_audio(
                silent_video,
                source_audio_path,
                output_path,
                0.0,
                None,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=0.0,
                log=log,
            )
        else:
            if source_audio:
                _emit(log, "No selected source audio found. Writing silent MP4.")
            else:
                _emit(log, "Writing silent MP4.")
            _emit_progress(progress, 95)
            ffmpeg_utils.write_silent_output(silent_video, output_path, log=log)

        final_output_path = output_path
        if settings.optimize_enabled:
            optimized_path = _optimized_output_path(output_path, settings.optimize_target_mb)
            _emit(log, f"Optimizing final video to <= {settings.optimize_target_mb:.1f} MB.")
            _emit(log, f"Keeping unoptimized intermediate: {output_path}")
            _emit_progress(progress, 97)
            result = ffmpeg_utils.optimize_mp4_to_target(
                output_path,
                optimized_path,
                settings.optimize_target_mb,
                settings.audio_bitrate,
                log=log,
            )
            final_output_path = Path(str(result["output_path"]))
            _emit(
                log,
                f"Optimization complete: {result['size_mb']:.2f} MB "
                f"({'under' if result['within_target'] else 'over'} target).",
            )
        else:
            final_size_mb = ffmpeg_utils.file_size_mb(output_path)
            _emit(log, f"Final file size: {final_size_mb:.2f} MB.")

    _emit_progress(progress, 100)
    _emit(log, f"Done: {final_output_path}")
    return str(final_output_path)


def _validate_settings(settings: RenderSettings) -> None:
    output_path = Path(settings.output_path)
    source_paths = [Path(item.path) for item in settings.timeline_items] or [Path(settings.video_path)]
    if not source_paths:
        raise ValueError("Add at least one video or photo source.")
    for source_path in source_paths:
        if not source_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {source_path}")
        if output_path.resolve(strict=False) == source_path.resolve(strict=False):
            raise ValueError("Output path must be different from selected source files.")
    if _uses_external_audio(settings):
        audio_path = Path(settings.audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {settings.audio_path}")
        if output_path.resolve(strict=False) == audio_path.resolve(strict=False):
            raise ValueError("Output path must be different from the selected audio file.")
    if settings.match_timeline_to_audio and not _uses_external_audio(settings):
        raise ValueError("Match video length to music requires External only or External + selected source audio mode with a selected audio track.")
    if settings.audio_timeline_start < 0:
        raise ValueError("Music start in video cannot be negative.")
    if settings.audio_timeline_end is not None and settings.audio_timeline_end <= settings.audio_timeline_start:
        raise ValueError("Music end in video must be after music start in video.")
    if settings.fps < 1 or settings.fps > 60:
        raise ValueError("FPS must be between 1 and 60.")
    if settings.width_chars < 24 or settings.width_chars > 260:
        raise ValueError("Character width must be between 24 and 260.")
    if settings.output_size[0] % 2 or settings.output_size[1] % 2:
        raise ValueError("Output resolution must use even pixel dimensions.")
    if settings.video_crf < 14 or settings.video_crf > 40:
        raise ValueError("CRF must be between 14 and 40.")
    audio_bps = ffmpeg_utils.parse_bitrate_bits_per_second(settings.audio_bitrate)
    if _audio_mode(settings) != AUDIO_SILENT and audio_bps <= 0:
        raise ValueError("Audio bitrate must be greater than 0 when audio output is enabled.")
    if settings.target_size_mb is not None and settings.target_size_mb <= 0:
        raise ValueError("Target file size must be greater than 0 MB.")
    if settings.optimize_enabled and settings.optimize_target_mb <= 0:
        raise ValueError("Optimize max size must be greater than 0 MB.")


def _expanded_settings(settings: RenderSettings) -> RenderSettings:
    timeline_items = [
        replace(item, path=str(Path(item.path).expanduser()))
        for item in settings.timeline_items
    ]
    return replace(
        settings,
        video_path=str(Path(settings.video_path).expanduser()) if settings.video_path else "",
        audio_path=str(Path(settings.audio_path).expanduser()) if settings.audio_path else None,
        output_path=str(Path(settings.output_path).expanduser()),
        timeline_items=timeline_items,
    )

def _optimized_output_path(output_path: Path, target_mb: float) -> Path:
    label = f"{target_mb:g}".replace(".", "p")
    if label.endswith("p0"):
        label = label[:-2]
    return output_path.with_name(f"{output_path.stem}_optimized_{label}mb.mp4")


def _audio_mode(settings: RenderSettings) -> str:
    mode = (settings.audio_mode or AUDIO_EXTERNAL).strip()
    aliases = {
        "External Music/Audio": AUDIO_EXTERNAL,
        "Keep source audio": AUDIO_SOURCE,
        "Source audio": AUDIO_SOURCE,
        "External + source audio": AUDIO_MIX,
    }
    mode = aliases.get(mode, mode)
    if mode not in {AUDIO_EXTERNAL, AUDIO_SOURCE, AUDIO_SILENT, AUDIO_MIX}:
        return AUDIO_EXTERNAL if settings.audio_path else AUDIO_SILENT
    return mode


def _uses_external_audio(settings: RenderSettings) -> bool:
    return _audio_mode(settings) in {AUDIO_EXTERNAL, AUDIO_MIX} and bool(settings.audio_path)


def _uses_source_audio(settings: RenderSettings) -> bool:
    return _audio_mode(settings) in {AUDIO_SOURCE, AUDIO_MIX}


def _external_audio_active_duration(settings: RenderSettings, selected_clip_duration: float) -> float:
    start = max(0.0, float(settings.audio_timeline_start or 0.0))
    if settings.audio_timeline_end is None:
        return max(0.0, float(selected_clip_duration))
    end = float(settings.audio_timeline_end)
    if end <= start:
        raise ValueError("Music end in video must be after music start in video.")
    return max(0.0, min(float(selected_clip_duration), end - start))


def _external_audio_match_duration(settings: RenderSettings, selected_clip_duration: float) -> float:
    start = max(0.0, float(settings.audio_timeline_start or 0.0))
    return start + _external_audio_active_duration(settings, selected_clip_duration)


def _playback_plan(
    settings: RenderSettings,
    timeline_duration: float,
    *,
    selected_audio_duration: float | None,
) -> PlaybackPlan:
    timeline_start, timeline_end = ffmpeg_utils.validate_time_range(
        settings.video_start,
        settings.video_end,
        timeline_duration,
        "Timeline",
    )
    source_duration = timeline_end - timeline_start
    if source_duration <= 0:
        raise ValueError("Timeline trim range is empty.")

    output_duration = source_duration
    speed_factor = 1.0
    loop_timeline = False
    if settings.match_timeline_to_audio:
        if not _uses_external_audio(settings) or selected_audio_duration is None:
            raise ValueError("Match video length to music requires External only or External + selected source audio mode with a selected audio track.")
        if selected_audio_duration <= 0:
            raise ValueError("Selected music/audio duration is empty.")
        mode = settings.match_timeline_mode or MATCH_SPEED
        if mode == MATCH_TRIM:
            output_duration = min(source_duration, selected_audio_duration)
            speed_factor = 1.0
        elif mode == MATCH_LOOP:
            output_duration = selected_audio_duration
            speed_factor = 1.0
            loop_timeline = True
        else:
            output_duration = selected_audio_duration
            speed_factor = source_duration / selected_audio_duration

    return PlaybackPlan(
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        source_duration=source_duration,
        output_duration=output_duration,
        speed_factor=max(0.0001, speed_factor),
        loop_timeline=loop_timeline,
    )


def _source_time_for_output(playback: PlaybackPlan, output_t: float) -> float:
    if playback.loop_timeline:
        local_t = output_t % max(0.001, playback.source_duration)
        return playback.timeline_start + local_t
    source_t = playback.timeline_start + output_t * playback.speed_factor
    return min(max(playback.timeline_start, source_t), max(playback.timeline_start, playback.timeline_end - 0.001))


def _build_timeline(settings: RenderSettings) -> tuple[list[TimelineSegment], float]:
    raw_items = list(settings.timeline_items)
    if not raw_items:
        raw_items = [TimelineItem(path=settings.video_path, kind="video")]

    segments: list[TimelineSegment] = []
    timeline_cursor = 0.0
    for index, item in enumerate(raw_items, start=1):
        path = str(Path(item.path).expanduser())
        kind = (item.kind or "video").strip().lower()
        if kind not in {"video", "photo"}:
            suffix = Path(path).suffix.lower()
            kind = "photo" if suffix in PHOTO_EXTENSIONS else "video"

        if kind == "photo":
            hold = float(item.photo_hold_duration or item.duration or 3.0)
            if hold <= 0:
                raise ValueError(f"Photo source {index} must have a positive hold duration.")
            _check_photo_readable(path)
            segments.append(
                TimelineSegment(
                    path=path,
                    kind="photo",
                    timeline_start=timeline_cursor,
                    duration=hold,
                    source_start=0.0,
                    source_end=hold,
                    has_audio=False,
                    include_audio=False,
                )
            )
            timeline_cursor += hold
            continue

        duration = ffmpeg_utils.get_duration(path)
        trim_start = max(0.0, float(item.trim_start or 0.0))
        trim_end = duration if item.trim_end is None else float(item.trim_end)
        trim_start, trim_end = ffmpeg_utils.validate_time_range(trim_start, trim_end, duration, f"Video source {index}")
        segment_duration = trim_end - trim_start
        if segment_duration <= 0:
            raise ValueError(f"Video source {index} trim range is empty.")
        segments.append(
            TimelineSegment(
                path=path,
                kind="video",
                timeline_start=timeline_cursor,
                duration=segment_duration,
                source_start=trim_start,
                source_end=trim_end,
                has_audio=bool(item.has_audio),
                include_audio=bool(item.include_audio and item.has_audio),
            )
        )
        timeline_cursor += segment_duration

    if timeline_cursor <= 0:
        raise ValueError("Timeline duration is empty.")
    return segments, timeline_cursor


def _check_photo_readable(path: str) -> None:
    try:
        _load_photo_image(path).load()
    except Exception as exc:  # noqa: BLE001 - Pillow support varies by local install.
        if Path(path).suffix.lower() in HEIC_EXTENSIONS:
            raise RenderError("HEIC/HEIF image support is not available in this install. Install or update ffmpeg, or convert the photo to PNG/JPEG and add it again.") from exc
        raise RenderError(f"Could not read photo source {path}: {exc}") from exc


def _load_photo_image(path: str) -> Image.Image:
    try:
        with Image.open(path) as image:
            return ImageOps.exif_transpose(image).convert("RGB")
    except Exception:
        if Path(path).suffix.lower() not in HEIC_EXTENSIONS:
            raise
    with tempfile.TemporaryDirectory(prefix="wzrd_heic_decode_") as temp_dir:
        decoded = Path(temp_dir) / "decoded.png"
        ffmpeg_utils.extract_still_frame(path, decoded)
        with Image.open(decoded) as image:
            return ImageOps.exif_transpose(image).convert("RGB")


class _TimelineFrameSource:
    def __init__(self, segments: list[TimelineSegment]) -> None:
        self.segments = segments
        self.captures: dict[str, cv2.VideoCapture] = {}
        self.photo_cache: dict[str, np.ndarray] = {}
        self.last_frames: dict[str, np.ndarray] = {}

    def frame_at(self, timeline_t: float) -> np.ndarray:
        segment = self._segment_at(timeline_t)
        local_t = max(0.0, min(segment.duration, timeline_t - segment.timeline_start))
        if segment.kind == "photo":
            return self._photo_frame(segment.path, local_t, segment.duration)
        return self._video_frame(segment, local_t)

    def close(self) -> None:
        for capture in self.captures.values():
            capture.release()
        self.captures.clear()

    def _segment_at(self, timeline_t: float) -> TimelineSegment:
        if timeline_t <= 0:
            return self.segments[0]
        for segment in self.segments:
            if segment.timeline_start <= timeline_t < segment.timeline_end:
                return segment
        return self.segments[-1]

    def _video_frame(self, segment: TimelineSegment, local_t: float) -> np.ndarray:
        capture = self.captures.get(segment.path)
        if capture is None:
            capture = cv2.VideoCapture(segment.path)
            if not capture.isOpened():
                raise RenderError(f"OpenCV could not open video: {segment.path}")
            self.captures[segment.path] = capture

        source_t = segment.source_start + local_t
        if segment.source_end is not None:
            source_t = min(source_t, max(segment.source_start, segment.source_end - 0.001))
        capture.set(cv2.CAP_PROP_POS_MSEC, source_t * 1000.0)
        ok, frame_bgr = capture.read()
        if not ok:
            last_frame = self.last_frames.get(segment.path)
            if last_frame is None:
                raise RenderError(f"Could not read {segment.path} at {source_t:.3f}s.")
            frame_bgr = last_frame
        else:
            self.last_frames[segment.path] = frame_bgr
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    def _photo_frame(self, path: str, local_t: float = 0.0, duration: float = 3.0) -> np.ndarray:
        cached = self.photo_cache.get(path)
        if cached is None:
            try:
                cached = np.asarray(_load_photo_image(path))
            except Exception as exc:  # noqa: BLE001
                if Path(path).suffix.lower() in HEIC_EXTENSIONS:
                    raise RenderError("HEIC/HEIF image support is not available in this install. Install or update ffmpeg, or convert the photo to PNG/JPEG and add it again.") from exc
                raise RenderError(f"Could not load photo source {path}: {exc}") from exc
            self.photo_cache[path] = cached
        if Path(path).suffix.lower() in HEIC_EXTENSIONS:
            return _heic_motion_loop_frame(cached, local_t, duration)
        return cached


def _heic_motion_loop_frame(frame_rgb: np.ndarray, local_t: float, duration: float) -> np.ndarray:
    """Apply restrained automatic motion to HEIC/HEIF stills."""
    image = Image.fromarray(frame_rgb).convert("RGB")
    loop_duration = max(0.75, min(3.0, float(duration or 3.0)))
    phase = (float(local_t or 0.0) % loop_duration) / loop_duration
    wave = math.sin(phase * math.tau)
    zoom = 1.018 + 0.016 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2.0))
    center_x = 0.5 + 0.018 * wave
    center_y = 0.5 + 0.012 * math.cos(phase * math.tau)
    moved = _zoom_crop(image, zoom=zoom, center_x=center_x, center_y=center_y)
    shimmer = 1.0 + 0.018 * math.sin(phase * math.tau * 2.0)
    moved = ImageEnhance.Contrast(moved).enhance(shimmer)
    return np.asarray(moved)


def _render_frames(
    settings: RenderSettings,
    preset: dict[str, Any],
    layout: TextLayout,
    timeline_segments: list[TimelineSegment],
    playback: PlaybackPlan,
    frame_count: int,
    bypass_intervals: list[Interval],
    frames_dir: Path,
    progress: ProgressCallback,
    log: LogCallback,
) -> None:
    source = _TimelineFrameSource(timeline_segments)
    render_duration = playback.output_duration
    transition_boundaries = _transition_boundaries(timeline_segments, playback)
    audio_hits = _audio_hit_levels(settings, render_duration, frame_count, log)
    held_frame: np.ndarray | None = None
    hold_until = -1
    previous_output: Image.Image | None = None
    first_output: Image.Image | None = None
    last_source_t = _source_time_for_output(playback, max(0.0, render_duration - (1.0 / max(1, settings.fps))))

    try:
        for index in range(frame_count):
            output_t = min(index / settings.fps, max(0.0, render_duration - 0.0001))
            timeline_t = _source_time_for_output(playback, output_t)
            frame_effects = dict(settings.effects)
            hit_level = audio_hits[index] if index < len(audio_hits) else 0.0
            if hit_level > 0.01:
                frame_effects["_reactive_hit"] = True
                frame_effects["_hit_level"] = hit_level

            if _ending_freezes_source(settings, render_duration, output_t):
                frame_rgb = source.frame_at(last_source_t)
            elif _effect_on(frame_effects, "stutter_hold") and held_frame is not None and index < hold_until:
                frame_rgb = held_frame.copy()
            else:
                frame_rgb = source.frame_at(timeline_t)
                if _effect_on(frame_effects, "stutter_hold") and _starts_stutter_hold(index, settings):
                    held_frame = frame_rgb.copy()
                    hold_until = index + _stutter_hold_length(index, settings)

            public_source: Image.Image | None = None
            if preset.get("profile") == "public_access_v1":
                public_source = prepare_public_access_source(
                    frame_rgb,
                    output_size=settings.output_size,
                    preset=preset,
                    effects=frame_effects,
                    intensity=settings.effect_intensity,
                    frame_index=index,
                    fps=settings.fps,
                    framing=_frame_framing_kwargs(settings),
                    seed=settings.weird_seed or settings.random_seed,
                )

            if is_bypass_time(output_t, bypass_intervals):
                if public_source is not None:
                    output_frame = public_source
                else:
                    output_frame = render_normal_frame(
                        frame_rgb,
                        output_size=settings.output_size,
                        effects=frame_effects,
                        intensity=settings.effect_intensity,
                        frame_index=index,
                        fps=settings.fps,
                        framing=_frame_framing_kwargs(settings),
                    )
            else:
                if public_source is not None:
                    ansi_source = public_source
                else:
                    ansi_source = prepare_ansi_source(
                        frame_rgb,
                        output_size=settings.output_size,
                        effects=frame_effects,
                        intensity=settings.effect_intensity,
                        frame_index=index,
                        fps=settings.fps,
                        framing=_frame_framing_kwargs(settings),
                    )
                output_frame = render_text_art_frame(
                    np.asarray(ansi_source),
                    preset=preset,
                    layout=layout,
                    frame_index=index,
                    output_size=settings.output_size,
                    effects=frame_effects,
                    intensity=settings.effect_intensity,
                    fps=settings.fps,
                    chunky_blocks=settings.chunky_blocks
                    or preset.get("render_mode") == "chunky_blocks",
                    dither_mode=settings.dither_mode,
                )

            if first_output is None:
                first_output = output_frame.copy()

            output_frame = _apply_transition_effect(
                output_frame,
                previous_output,
                output_t,
                transition_boundaries,
                settings,
                index,
            )
            output_frame = _apply_global_artifact_effects(
                output_frame,
                previous_output,
                frame_effects,
                settings.effect_intensity,
                index,
                settings.fps,
                settings.weird_seed,
            )
            output_frame = _apply_ending_effect(
                output_frame,
                first_output,
                render_duration,
                output_t,
                settings,
                index,
            )
            if settings.loop_friendly and first_output is not None:
                output_frame = _apply_loop_friendly(output_frame, first_output, render_duration, output_t)

            output_frame.save(frames_dir / f"frame_{index:06d}.png", optimize=False)
            previous_output = output_frame.copy()

            if index % max(1, settings.fps) == 0 or index == frame_count - 1:
                _emit(log, f"Rendered frame {index + 1}/{frame_count}.")
            frame_progress = 5 + int(((index + 1) / frame_count) * 84)
            _emit_progress(progress, min(frame_progress, 89))
    finally:
        source.close()


def _frame_framing_kwargs(settings: RenderSettings) -> dict[str, Any]:
    return {
        "fit_mode": settings.framing_fit_mode,
        "anchor": settings.framing_anchor,
        "offset_x": settings.framing_offset_x,
        "offset_y": settings.framing_offset_y,
        "zoom_amount": settings.framing_zoom,
        "letterbox_background": settings.letterbox_background,
        "upper_bias": settings.preserve_upper_bias,
    }


def _transition_boundaries(segments: list[TimelineSegment], playback: PlaybackPlan) -> list[float]:
    boundaries: list[float] = []
    source_boundaries = [
        segment.timeline_start - playback.timeline_start
        for segment in segments[1:]
        if 0.0 < segment.timeline_start - playback.timeline_start < playback.source_duration
    ]
    if playback.loop_timeline:
        loop = max(0.001, playback.source_duration)
        cycle = 0
        while cycle * loop < playback.output_duration:
            if cycle > 0:
                boundaries.append(cycle * loop)
            for boundary in source_boundaries:
                output_boundary = cycle * loop + boundary
                if 0.0 < output_boundary < playback.output_duration:
                    boundaries.append(output_boundary)
            cycle += 1
        return sorted(set(round(value, 6) for value in boundaries))

    for boundary in source_boundaries:
        output_boundary = boundary / max(0.0001, playback.speed_factor)
        if 0.0 < output_boundary < playback.output_duration:
            boundaries.append(output_boundary)
    return boundaries


def _active_transition(output_t: float, boundaries: list[float], duration: float) -> tuple[float, int] | None:
    if duration <= 0:
        return None
    for index, boundary in enumerate(boundaries):
        if boundary <= output_t < boundary + duration:
            return (output_t - boundary) / duration, index
    return None


def _transition_name(settings: RenderSettings, index: int) -> str:
    mode = settings.transition_mode or "Hard Cut"
    if mode != "Random":
        return mode
    choices = [
        "CRT Flash",
        "Frame Burn",
        "Block Dissolve",
        "VHS Roll",
        "Terminal Wipe",
        "RGB Burst",
        "Buffer Underrun",
        "Corrupted Carryover",
    ]
    seed = (settings.weird_seed or settings.random_seed or 0) + index * 1009
    return random.Random(seed).choice(choices)


def _apply_transition_effect(
    image: Image.Image,
    previous: Image.Image | None,
    output_t: float,
    boundaries: list[float],
    settings: RenderSettings,
    frame_index: int,
) -> Image.Image:
    if settings.transition_mode == "Hard Cut" or not boundaries:
        return image
    duration = 0.10 + 0.34 * max(0.0, min(2.0, settings.transition_intensity))
    active = _active_transition(output_t, boundaries, duration)
    if active is None:
        return image
    progress, transition_index = active
    mode = _transition_name(settings, transition_index)
    intensity = max(0.0, min(2.0, settings.transition_intensity))
    rng = random.Random((settings.weird_seed or 0) + transition_index * 9176 + frame_index)
    arr = np.array(image, dtype=np.uint8)

    if mode == "CRT Flash":
        flash = 1.0 - progress
        arr = np.clip(arr.astype(np.float32) + 220 * flash * intensity, 0, 255).astype(np.uint8)
    elif mode == "Frame Burn":
        burn = np.array([255, 160, 80], dtype=np.float32)
        mix = (1.0 - progress) * min(0.85, 0.45 * intensity)
        arr = np.clip(arr.astype(np.float32) * (1 - mix) + burn * mix, 0, 255).astype(np.uint8)
    elif mode == "Block Dissolve":
        block = max(6, int(42 * (1.0 - progress) * intensity))
        small = Image.fromarray(arr).resize((max(2, arr.shape[1] // block), max(2, arr.shape[0] // block)), Image.Resampling.BOX)
        return small.resize(image.size, Image.Resampling.NEAREST)
    elif mode == "VHS Roll":
        arr = np.roll(arr, int((1.0 - progress) * arr.shape[0] * 0.35 * intensity), axis=0)
    elif mode == "Terminal Wipe":
        wipe = int(arr.shape[1] * progress)
        arr[:, :wipe, :] = (arr[:, :wipe, :].astype(np.float32) * 0.22).astype(np.uint8)
        arr[:, max(0, wipe - 8): min(arr.shape[1], wipe + 8), :] = np.array([186, 244, 200], dtype=np.uint8)
    elif mode == "RGB Burst":
        amount = int((22 + 34 * intensity) * (1.0 - progress))
        arr[:, :, 0] = np.roll(arr[:, :, 0], amount, axis=1)
        arr[:, :, 2] = np.roll(arr[:, :, 2], -amount, axis=1)
    elif mode == "Buffer Underrun":
        step = max(2, int(2 + 10 * (1.0 - progress) * intensity))
        arr[::step, :, :] = 0
        for _ in range(int(3 + 8 * intensity)):
            y = rng.randrange(arr.shape[0])
            h = rng.randint(1, 5)
            arr[y:y + h, :, :] = np.roll(arr[y:y + h, :, :], rng.randint(-60, 60), axis=1)
    elif mode == "Corrupted Carryover" and previous is not None:
        carry = np.array(previous.resize(image.size), dtype=np.uint8)
        mix = max(0.0, 0.65 * (1.0 - progress))
        arr = np.clip(arr.astype(np.float32) * (1 - mix) + carry.astype(np.float32) * mix, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _starts_stutter_hold(frame_index: int, settings: RenderSettings) -> bool:
    seed = (settings.weird_seed or settings.random_seed or 0) + frame_index * 193
    rng = random.Random(seed)
    chance = 0.006 + 0.013 * max(0.0, min(2.0, settings.effect_intensity))
    return frame_index > 3 and rng.random() < chance


def _stutter_hold_length(frame_index: int, settings: RenderSettings) -> int:
    seed = (settings.weird_seed or settings.random_seed or 0) + frame_index * 337
    rng = random.Random(seed)
    return rng.randint(2, 8)


def _audio_hit_levels(settings: RenderSettings, render_duration: float, frame_count: int, log: LogCallback) -> list[float]:
    levels = [0.0] * frame_count
    if not _effect_on(settings.effects, "audio_reactive") or not _uses_external_audio(settings):
        return levels
    try:
        pcm = _decode_audio_pcm(
            settings.audio_path,
            settings.audio_start,
            settings.audio_end,
            render_duration,
            settings.audio_timeline_start,
            settings.audio_timeline_end,
        )
    except Exception as exc:  # noqa: BLE001 - audio reactive should fail soft.
        _emit(log, f"Audio Reactive Hits unavailable: {exc}")
        return levels
    if pcm.size == 0:
        return levels
    samples_per_frame = max(1, int(len(pcm) / max(1, frame_count)))
    energies: list[float] = []
    for index in range(frame_count):
        chunk = pcm[index * samples_per_frame: (index + 1) * samples_per_frame]
        if chunk.size == 0:
            energies.append(0.0)
        else:
            energies.append(float(np.mean(np.abs(chunk.astype(np.float32))) / 32768.0))
    if not energies:
        return levels
    baseline = float(np.percentile(energies, 72)) or 0.001
    peak = float(np.percentile(energies, 96)) or baseline
    for index, energy in enumerate(energies):
        previous = energies[index - 1] if index else energy
        transient = max(0.0, energy - previous * 1.12)
        if energy > baseline * 1.18 or transient > baseline * 0.35:
            levels[index] = max(0.0, min(1.0, (energy - baseline) / max(0.001, peak - baseline)))
    _emit(log, f"Audio Reactive Hits: detected {sum(1 for value in levels if value > 0.01)} hit frame(s).")
    return levels


def _decode_audio_pcm(
    audio_path: str,
    audio_start: float,
    audio_end: float | None,
    render_duration: float,
    audio_offset: float = 0.0,
    audio_output_end: float | None = None,
) -> np.ndarray:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    sample_rate = 11025
    output_samples = max(0, int(render_duration * sample_rate))
    if output_samples <= 0:
        return np.array([], dtype=np.int16)
    offset = max(0.0, min(float(audio_offset or 0.0), float(render_duration)))
    output_end = float(render_duration) if audio_output_end is None else min(float(render_duration), max(offset, float(audio_output_end)))
    output_span = max(0.0, output_end - offset)
    source_span = output_span if audio_end is None else min(output_span, max(0.0, float(audio_end) - float(audio_start)))
    if source_span <= 0:
        return np.zeros(output_samples, dtype=np.int16)
    args = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{audio_start:.6f}",
        "-t",
        f"{source_span:.6f}",
        "-i",
        audio_path,
        "-map",
        "0:a:0",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "pipe:1",
    ]
    completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0:
        raise ffmpeg_utils.FFmpegError((completed.stderr or b"audio decode failed").decode(errors="replace"))
    decoded = np.frombuffer(completed.stdout, dtype=np.int16)
    output = np.zeros(output_samples, dtype=np.int16)
    start_sample = min(output_samples, int(offset * sample_rate))
    end_sample = min(output_samples, start_sample + len(decoded))
    if end_sample > start_sample:
        output[start_sample:end_sample] = decoded[: end_sample - start_sample]
    return output


def _apply_global_artifact_effects(
    image: Image.Image,
    previous: Image.Image | None,
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    seed: int | None,
) -> Image.Image:
    if _effect_on(effects, "motion_melt") and previous is not None:
        image = _apply_motion_melt(image, previous, frame_index, intensity)
    if _effect_on(effects, "terminal_scroll"):
        image = _apply_terminal_scroll(image, frame_index, intensity)
    if _effect_on(effects, "tape_damage"):
        image = _apply_tape_damage(image, frame_index, intensity, seed)
    if _effect_on(effects, "mosaic_collapse"):
        image = _apply_mosaic_collapse(image, frame_index, fps, intensity, seed)
    return image


def _apply_motion_melt(image: Image.Image, previous: Image.Image, frame_index: int, intensity: float) -> Image.Image:
    current = np.array(image, dtype=np.uint8)
    prev = np.array(previous.resize(image.size), dtype=np.uint8)
    mix = min(0.62, 0.18 + 0.18 * max(0.0, intensity))
    melted = np.clip(current.astype(np.float32) * (1 - mix) + prev.astype(np.float32) * mix, 0, 255).astype(np.uint8)
    smear = int(3 + 10 * max(0.0, intensity))
    if smear > 0:
        direction = -1 if (frame_index // 9) % 2 else 1
        melted[:, :, :] = np.maximum(melted, np.roll(melted, direction * smear, axis=1))
    return Image.fromarray(melted, mode="RGB")


def _apply_terminal_scroll(image: Image.Image, frame_index: int, intensity: float) -> Image.Image:
    arr = np.array(image, dtype=np.uint8)
    shift = int(math.sin(frame_index * 0.035) * (2 + 10 * intensity))
    if shift:
        arr = np.roll(arr, shift, axis=0)
        if shift > 0:
            arr[:shift, :, :] = 0
        else:
            arr[shift:, :, :] = 0
    return Image.fromarray(arr, mode="RGB")


def _apply_tape_damage(image: Image.Image, frame_index: int, intensity: float, seed: int | None) -> Image.Image:
    rng = random.Random((seed or 0) + frame_index * 271)
    arr = np.array(image, dtype=np.uint8)
    if rng.random() < 0.08 + 0.08 * intensity:
        for _ in range(rng.randint(1, 3)):
            h = rng.randint(2, max(3, int(14 * max(0.5, intensity))))
            y = rng.randint(0, max(0, arr.shape[0] - h))
            shift = rng.randint(-int(80 * intensity) - 4, int(80 * intensity) + 4)
            arr[y:y + h, :, :] = np.roll(arr[y:y + h, :, :], shift, axis=1)
    if rng.random() < 0.05 + 0.08 * intensity:
        y = rng.randint(0, arr.shape[0] - 1)
        h = rng.randint(1, 4)
        arr[y:y + h, :, :] = (arr[y:y + h, :, :].astype(np.float32) * rng.uniform(0.05, 0.35)).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _apply_mosaic_collapse(image: Image.Image, frame_index: int, fps: int, intensity: float, seed: int | None) -> Image.Image:
    cycle = max(12, int(fps * 2.7))
    local = (frame_index + (seed or 0) % cycle) % cycle
    if local > max(3, int(0.24 * fps)):
        return image
    progress = local / max(1, int(0.24 * fps))
    amount = math.sin(progress * math.pi)
    if amount <= 0.05:
        return image
    block = max(3, int((8 + 34 * intensity) * amount))
    small = image.resize((max(2, image.width // block), max(2, image.height // block)), Image.Resampling.BOX)
    return small.resize(image.size, Image.Resampling.NEAREST)


def _ending_freezes_source(settings: RenderSettings, render_duration: float, output_t: float) -> bool:
    if settings.ending_mode in {"Hard Cut", "Fade Out", "Seamless Loop"} and not settings.loop_friendly:
        return False
    return render_duration > 0.75 and output_t >= render_duration - 0.5


def _apply_ending_effect(
    image: Image.Image,
    first_output: Image.Image | None,
    render_duration: float,
    output_t: float,
    settings: RenderSettings,
    frame_index: int,
) -> Image.Image:
    mode = settings.ending_mode or "Hard Cut"
    if mode == "Hard Cut" or render_duration <= 0:
        return image
    tail = min(1.5, render_duration)
    if output_t < render_duration - tail:
        return image
    progress = (output_t - (render_duration - tail)) / max(0.001, tail)
    arr = np.array(image, dtype=np.uint8)
    if mode == "Fade Out" or mode == "Loop Freeze":
        arr = (arr.astype(np.float32) * (1.0 - 0.82 * progress)).astype(np.uint8)
    elif mode == "VHS Collapse":
        arr = np.asarray(_apply_tape_damage(Image.fromarray(arr), frame_index, 1.0 + settings.effect_intensity, settings.weird_seed), dtype=np.uint8)
        arr = (arr.astype(np.float32) * (1.0 - 0.55 * progress)).astype(np.uint8)
    elif mode == "Seamless Loop" and first_output is not None:
        return Image.blend(image, first_output.resize(image.size), max(0.0, min(1.0, progress)))
    elif mode == "CRT Shutdown":
        h, w = arr.shape[:2]
        band_h = max(2, int(h * (1.0 - progress)))
        canvas = np.zeros_like(arr)
        top = (h - band_h) // 2
        canvas[top:top + band_h, :, :] = arr[top:top + band_h, :, :]
        if progress > 0.82:
            line = h // 2
            canvas[:, :, :] = 0
            canvas[max(0, line - 1):line + 2, :, :] = 230
        arr = canvas
    elif mode == "Buffer Exhausted":
        block = max(3, int(5 + 58 * progress * max(0.5, settings.effect_intensity)))
        small = Image.fromarray(arr).resize((max(2, image.width // block), max(2, image.height // block)), Image.Resampling.BOX)
        image = small.resize(image.size, Image.Resampling.NEAREST)
        arr = np.array(image, dtype=np.uint8)
        arr = (arr.astype(np.float32) * (1.0 - 0.45 * progress)).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _apply_loop_friendly(image: Image.Image, first_output: Image.Image, render_duration: float, output_t: float) -> Image.Image:
    tail = min(0.75, render_duration / 3.0)
    if tail <= 0.05 or output_t < render_duration - tail:
        return image
    progress = (output_t - (render_duration - tail)) / tail
    return Image.blend(image, first_output.resize(image.size), max(0.0, min(0.85, progress * 0.85)))


def _audio_fade_duration(settings: RenderSettings, render_duration: float) -> float:
    if settings.ending_mode == "Hard Cut" and not settings.loop_friendly:
        return 0.0
    return min(1.5, max(0.0, render_duration))


def make_text_layout(
    width_chars: int,
    output_size: tuple[int, int],
    chunky_blocks: bool = False,
) -> TextLayout:
    out_width, out_height = output_size
    font, char_width, line_height = _fit_font(width_chars, out_width, chunky_blocks=chunky_blocks)
    rows = max(1, out_height // line_height)
    x_offset = max(0, (out_width - (char_width * width_chars)) // 2)
    y_offset = max(0, (out_height - (line_height * rows)) // 2)
    return TextLayout(
        font=font,
        cols=width_chars,
        rows=rows,
        char_width=char_width,
        line_height=line_height,
        x_offset=x_offset,
        y_offset=y_offset,
    )


def prepare_ansi_source(
    frame_rgb: np.ndarray,
    output_size: tuple[int, int],
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    framing: dict[str, Any] | None = None,
) -> Image.Image:
    image = fit_frame_to_output(frame_rgb, output_size, **(framing or {}))
    intensity = max(0.0, float(intensity))

    zoom = 1.0
    center_x = 0.5
    center_y = 0.5
    if _effect_on(effects, "ken_burns"):
        phase = frame_index / max(1, fps)
        zoom += 0.035 * intensity + 0.035 * intensity * (0.5 + 0.5 * math.sin(phase * 0.85))
        center_x = 0.5 + 0.12 * math.sin(phase * 0.31)
        center_y = 0.5 + 0.09 * math.cos(phase * 0.27)
    if _effect_on(effects, "tunnel_zoom"):
        phase_seconds = frame_index / max(1, fps)
        cycle_duration = max(2.25, 6.0 - min(2.0, intensity) * 1.75)
        cycle = (phase_seconds % cycle_duration) / cycle_duration
        max_zoom = 0.25 + 0.60 * min(2.0, intensity)
        zoom += cycle * max_zoom
        if cycle < min(0.10, 0.025 + 0.035 * intensity):
            image = _apply_tape_damage(image, frame_index, 0.35 + intensity, None)
    if _effect_on(effects, "_reactive_hit"):
        zoom += 0.22 * intensity * float(effects.get("_hit_level", 1.0))
    if _effect_on(effects, "punch_zoom"):
        phase = (frame_index / max(1, fps)) % 2.15
        if phase < 0.22:
            zoom += 0.18 * intensity * (1.0 - phase / 0.22)
    if zoom > 1.001:
        image = _zoom_crop(image, zoom=zoom, center_x=center_x, center_y=center_y)

    if _effect_on(effects, "boost"):
        image = ImageEnhance.Contrast(image).enhance(1.0 + 0.22 * intensity)
        image = ImageEnhance.Color(image).enhance(1.0 + 0.18 * intensity)
    if _effect_on(effects, "color_drift"):
        image = _hue_shift_image(image, frame_index * 0.7 * intensity)
    if _effect_on(effects, "vhs_wobble"):
        angle = math.sin(frame_index * 0.09) * 0.42 * intensity
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0))
    return image


def prepare_public_access_source(
    frame_rgb: np.ndarray,
    output_size: tuple[int, int],
    preset: dict[str, Any],
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    framing: dict[str, Any] | None = None,
    seed: int | None = None,
) -> Image.Image:
    """Prepare the shared PUBLIC ACCESS source frame for normal and ANSI sections."""
    image = render_normal_frame(
        frame_rgb,
        output_size=output_size,
        effects=effects,
        intensity=intensity,
        frame_index=frame_index,
        fps=fps,
        framing=framing,
    )
    amount = max(0.0, min(2.0, float(preset.get("public_access_amount", 1.0)) * (0.72 + 0.34 * intensity)))
    return _apply_public_access_treatment(image, frame_index, fps, amount, seed)


def _apply_public_access_treatment(
    image: Image.Image,
    frame_index: int,
    fps: int,
    amount: float,
    seed: int | None,
) -> Image.Image:
    """Camcorder-dub public-access texture without disabling ANSI coverage."""
    amount = max(0.0, min(2.0, amount))
    width, height = image.size
    rng = random.Random((seed or 0) + frame_index * 1723)

    # Generation loss and tube softness: small but always present for this profile.
    softened = image.filter(ImageFilter.GaussianBlur(radius=0.45 + 0.34 * amount))
    image = Image.blend(image, softened, min(0.58, 0.24 + 0.18 * amount))

    arr = np.asarray(image, dtype=np.float32)
    phase = frame_index / max(1, fps)

    # Muted camcorder color with slow, uneven broadcast drift.
    luma = (
        arr[:, :, 0] * 0.299
        + arr[:, :, 1] * 0.587
        + arr[:, :, 2] * 0.114
    )
    arr = arr * (0.72 - 0.06 * amount) + luma[:, :, None] * (0.28 + 0.06 * amount)
    warm = np.array([224, 215, 185], dtype=np.float32)
    cool = np.array([178, 232, 206], dtype=np.float32)
    tint = warm * (0.64 + 0.18 * math.sin(phase * 0.31)) + cool * (0.36 - 0.18 * math.sin(phase * 0.31))
    arr = arr * (1.0 - 0.12 * amount) + tint * (0.12 * amount)

    contrast = 0.96 + 0.045 * math.sin(phase * 2.7) + rng.uniform(-0.015, 0.015) * amount
    brightness = 1.0 + 0.035 * math.sin(phase * 3.8 + 1.2) + rng.uniform(-0.012, 0.012) * amount
    arr = ((arr - 127.5) * contrast + 127.5) * brightness
    arr = np.clip(arr, 0, 255).astype(np.uint8)

    # Chroma bleed and analog misregistration.
    bleed = max(1, int(round(1.0 + 2.2 * amount + 1.4 * math.sin(phase * 1.7))))
    shifted = arr.copy()
    shifted[:, :, 0] = np.roll(arr[:, :, 0], bleed, axis=1)
    shifted[:, :, 2] = np.roll(arr[:, :, 2], -max(1, bleed // 2), axis=1)
    arr = shifted

    # Horizontal tape wobble, with stronger instability near the head-switch band.
    wobble = arr.copy()
    base_amp = 1.2 + 3.0 * amount
    for y in range(height):
        bottom_bias = 1.0 + 1.6 * max(0.0, (y / max(1, height)) - 0.82)
        shift = int(round(math.sin(y * 0.038 + phase * 7.2) * base_amp * bottom_bias))
        if shift:
            wobble[y, :, :] = np.roll(wobble[y, :, :], shift, axis=0)
    arr = wobble

    # Bottom head-switching noise band and tracking dirt.
    band_h = max(6, int(height * (0.045 + 0.025 * amount)))
    band_top = max(0, height - band_h - int(3 * math.sin(phase * 4.1)))
    band = arr[band_top:, :, :].copy()
    band_rng = np.random.default_rng((seed or 0) + frame_index * 313 + 19)
    band_noise = band_rng.integers(-56, 64, size=band.shape, dtype=np.int16)
    band = np.clip(band.astype(np.int16) + band_noise, 0, 255).astype(np.uint8)
    for row in range(0, band.shape[0], 3):
        shift = int(round(math.sin(row * 0.7 + phase * 12.0) * (12 + 16 * amount)))
        band[row:row + 2, :, :] = np.roll(band[row:row + 2, :, :], shift, axis=1)
    arr[band_top:, :, :] = band

    # Sparse RF speckle and small dropout streaks.
    speckle_rng = np.random.default_rng((seed or 0) + frame_index * 977 + 41)
    speckle_mask = speckle_rng.random((height, width)) < (0.0018 + 0.0022 * amount)
    if speckle_mask.any():
        speckle_values = speckle_rng.choice(np.array([20, 235], dtype=np.uint8), size=int(speckle_mask.sum()))
        arr[speckle_mask] = speckle_values[:, None]

    line_count = int(1 + 4 * amount)
    for _ in range(line_count):
        if rng.random() > 0.34 + 0.12 * amount:
            continue
        y = rng.randrange(max(1, height))
        h = rng.randint(1, max(2, int(4 + 4 * amount)))
        x0 = rng.randrange(max(1, width))
        span = rng.randint(max(18, width // 12), max(24, width // 2))
        x1 = min(width, x0 + span)
        shade = rng.choice([18, 36, 210, 238])
        arr[y:min(height, y + h), x0:x1, :] = np.clip(
            arr[y:min(height, y + h), x0:x1, :].astype(np.float32) * 0.45 + shade * 0.55,
            0,
            255,
        ).astype(np.uint8)

    result = Image.fromarray(arr, mode="RGB")
    result = _apply_scanlines(result, line_gap=3, strength=min(0.48, 0.18 + 0.12 * amount))
    result = _apply_public_access_vignette(result, amount)
    return result


def _apply_public_access_vignette(image: Image.Image, amount: float) -> Image.Image:
    arr = np.asarray(image, dtype=np.float32)
    height, width = arr.shape[:2]
    yy, xx = np.ogrid[:height, :width]
    x = (xx - width / 2.0) / max(1.0, width / 2.0)
    y = (yy - height / 2.0) / max(1.0, height / 2.0)
    distance = np.clip((x * x + y * y) ** 0.5, 0.0, 1.25)
    vignette = 1.0 - np.clip((distance - 0.48) * (0.18 + 0.10 * amount), 0.0, 0.28)
    arr *= vignette[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


def render_normal_frame(
    frame_rgb: np.ndarray,
    output_size: tuple[int, int],
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    framing: dict[str, Any] | None = None,
) -> Image.Image:
    image = fit_frame_to_output(frame_rgb, output_size, **(framing or {}))
    intensity = max(0.0, float(intensity))
    zoom = 1.0
    if _effect_on(effects, "tunnel_zoom"):
        phase_seconds = frame_index / max(1, fps)
        cycle_duration = max(2.25, 6.0 - min(2.0, intensity) * 1.75)
        cycle = (phase_seconds % cycle_duration) / cycle_duration
        zoom += cycle * (0.22 + 0.58 * min(2.0, intensity))
    if _effect_on(effects, "punch_zoom") or _effect_on(effects, "_reactive_hit"):
        phase = (frame_index / max(1, fps)) % 2.15
        hit = float(effects.get("_hit_level", 1.0)) if _effect_on(effects, "_reactive_hit") else 1.0
        if phase < 0.22 or _effect_on(effects, "_reactive_hit"):
            zoom += 0.14 * intensity * hit
    if zoom > 1.001:
        image = _zoom_crop(image, zoom, 0.5, 0.5)
    if _effect_on(effects, "boost"):
        image = ImageEnhance.Contrast(image).enhance(1.0 + 0.12 * intensity)
        image = ImageEnhance.Color(image).enhance(1.0 + 0.10 * intensity)
    if _effect_on(effects, "vhs_wobble"):
        image = _apply_vhs_wobble(image, frame_index, intensity * 0.55)
    if _effect_on(effects, "scanlines"):
        image = _apply_scanlines(image, line_gap=max(3, output_size[1] // 180), strength=0.16)
    return image


def render_text_art_frame(
    frame_rgb: np.ndarray,
    preset: dict[str, Any],
    layout: TextLayout,
    frame_index: int,
    output_size: tuple[int, int] = OUTPUT_SIZE,
    effects: dict[str, bool] | None = None,
    intensity: float = 1.0,
    fps: int = 24,
    chunky_blocks: bool = False,
    dither_mode: str = "None",
) -> Image.Image:
    effects = effects or {}
    intensity = max(0.0, float(intensity))
    rng = random.Random((frame_index + 1) * 7919)
    resample = Image.Resampling.BOX if chunky_blocks else Image.Resampling.BICUBIC
    sample = Image.fromarray(frame_rgb).resize((layout.cols, layout.rows), resample)

    contrast = float(preset["contrast"])
    saturation = float(preset["saturation"])
    if _effect_on(effects, "boost"):
        contrast *= 1.0 + 0.22 * intensity
        saturation *= 1.0 + 0.18 * intensity
    sample = ImageEnhance.Contrast(sample).enhance(contrast)
    sample = ImageEnhance.Color(sample).enhance(saturation)
    pixels = np.asarray(sample, dtype=np.uint8)
    luma = (
        pixels[:, :, 0].astype(np.float32) * 0.2126
        + pixels[:, :, 1].astype(np.float32) * 0.7152
        + pixels[:, :, 2].astype(np.float32) * 0.0722
    ) / 255.0
    luma = _apply_dither_mode(luma, dither_mode, frame_index)

    image = Image.new("RGB", output_size, tuple(preset["background"]))
    draw = ImageDraw.Draw(image)
    charset = str(preset["charset"])
    jitter_base = 1.0 if chunky_blocks else 2.0
    row_jitter = int(round((jitter_base if _effect_on(effects, "glitch") else 0.0) * intensity))
    noise = float(preset["base_noise"])
    if _effect_on(effects, "char_noise"):
        noise += 0.035 * intensity

    for row in range(layout.rows):
        row_shift = rng.randint(-row_jitter, row_jitter) if row_jitter else 0
        for col in range(layout.cols):
            brightness = float(luma[row, col])
            character = _character_for_brightness(charset, brightness)
            if noise and rng.random() < noise:
                character = rng.choice(charset[1:] or charset)

            x = layout.x_offset + (col * layout.char_width) + row_shift
            y = layout.y_offset + (row * layout.line_height)
            if row_jitter >= 3 and rng.random() < (0.006 if chunky_blocks else 0.014):
                x += rng.randint(-row_jitter * 2, row_jitter * 2)

            color = _character_color(
                pixels[row, col],
                brightness,
                preset,
                frame_index,
                effects,
                intensity,
            )
            draw.text((x, y), character, font=layout.font, fill=color)

    return _apply_ansi_output_effects(image, preset, frame_index, rng, layout, effects, intensity, fps)


def fit_frame_to_output(
    frame_rgb: np.ndarray | Image.Image,
    output_size: tuple[int, int],
    fit_mode: str = "Fill/Crop",
    anchor: str = "Center",
    offset_x: int = 0,
    offset_y: int = 0,
    zoom_amount: float = 0.0,
    letterbox_background: str = "Black",
    upper_bias: bool = True,
) -> Image.Image:
    image = frame_rgb.convert("RGB") if isinstance(frame_rgb, Image.Image) else Image.fromarray(frame_rgb).convert("RGB")
    src_w, src_h = image.size
    out_w, out_h = output_size
    if src_w <= 0 or src_h <= 0:
        return Image.new("RGB", output_size, (0, 0, 0))

    mode = (fit_mode or "Fill/Crop").strip().lower()
    anchor_name = (anchor or "Center").strip().lower()
    zoom = 1.0 + max(0.0, min(1.0, float(zoom_amount or 0.0))) * 0.75

    if mode == "stretch":
        return image.resize(output_size, Image.Resampling.LANCZOS)

    src_aspect = src_w / src_h
    out_aspect = out_w / out_h

    if mode == "fit/letterbox":
        scale = min(out_w / src_w, out_h / src_h) * zoom
        target_w = max(1, int(src_w * scale))
        target_h = max(1, int(src_h * scale))
        resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        if target_w > out_w or target_h > out_h:
            max_crop_x = max(0, target_w - out_w)
            max_crop_y = max(0, target_h - out_h)
            left = _offset_position(max_crop_x, offset_x, anchor_name, "x")
            top = _offset_position(max_crop_y, offset_y, anchor_name, "y")
            resized = resized.crop((left, top, left + min(out_w, target_w), top + min(out_h, target_h)))
            target_w, target_h = resized.size
        background = _letterbox_canvas(image, output_size, letterbox_background)
        max_x = max(0, out_w - target_w)
        max_y = max(0, out_h - target_h)
        x = _offset_position(max_x, offset_x, anchor_name, "x")
        y = _offset_position(max_y, offset_y, anchor_name, "y")
        background.paste(resized, (x, y))
        return background

    scale = max(out_w / src_w, out_h / src_h) * zoom
    target_w = max(out_w, int(src_w * scale))
    target_h = max(out_h, int(src_h * scale))
    resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    max_x = max(0, target_w - out_w)
    max_y = max(0, target_h - out_h)
    effective_anchor = anchor_name
    if mode == "smart portrait" and src_h > src_w and upper_bias:
        effective_anchor = "top"
        offset_y = int(offset_y) - 24
    left = _offset_position(max_x, offset_x, effective_anchor, "x")
    top = _offset_position(max_y, offset_y, effective_anchor, "y")
    return resized.crop((left, top, left + out_w, top + out_h))


def _offset_position(max_offset: int, slider_value: int | float, anchor: str, axis: str) -> int:
    if max_offset <= 0:
        return 0
    position = max_offset / 2.0
    if axis == "x":
        if anchor == "left":
            position = 0.0
        elif anchor == "right":
            position = float(max_offset)
    else:
        if anchor == "top":
            position = 0.0
        elif anchor == "bottom":
            position = float(max_offset)
    position += (max(-100.0, min(100.0, float(slider_value))) / 100.0) * (max_offset / 2.0)
    return int(round(max(0.0, min(float(max_offset), position))))


def _letterbox_canvas(source: Image.Image, output_size: tuple[int, int], background: str) -> Image.Image:
    normalized = (background or "Black").strip().lower()
    if normalized == "pastel pink":
        return Image.new("RGB", output_size, (246, 184, 212))
    if normalized == "blurred source":
        canvas = source.resize(output_size, Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(radius=18))
        return ImageEnhance.Brightness(canvas).enhance(0.55)
    return Image.new("RGB", output_size, (0, 0, 0))



def _fit_font(
    width_chars: int,
    output_width: int,
    chunky_blocks: bool = False,
) -> tuple[ImageFont.ImageFont, int, int]:
    best: tuple[ImageFont.ImageFont, int, int] | None = None
    low, high = 5, 126 if chunky_blocks else 96
    while low <= high:
        size = (low + high) // 2
        font = _load_monospace_font(size, chunky_blocks=chunky_blocks)
        char_width, line_height = _measure_font(font, chunky_blocks=chunky_blocks)
        if char_width * width_chars <= output_width:
            best = (font, char_width, line_height)
            low = size + 1
        else:
            high = size - 1
    if best:
        return best

    font = _load_monospace_font(5, chunky_blocks=chunky_blocks)
    char_width, line_height = _measure_font(font, chunky_blocks=chunky_blocks)
    return font, char_width, line_height


def _load_monospace_font(size: int, chunky_blocks: bool = False) -> ImageFont.ImageFont:
    candidates = _chunky_font_candidates() + FONT_CANDIDATES if chunky_blocks else FONT_CANDIDATES
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _chunky_font_candidates() -> list[str]:
    return [
        "/System/Library/Fonts/Supplemental/Menlo Bold.ttf",
        "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
        "/Library/Fonts/Menlo Bold.ttf",
        "/Library/Fonts/Andale Mono.ttf",
    ]


def _measure_font(
    font: ImageFont.ImageFont,
    chunky_blocks: bool = False,
) -> tuple[int, int]:
    probe = "M"
    try:
        char_width = int(math.ceil(font.getlength(probe)))
    except AttributeError:
        bbox = font.getbbox(probe)
        char_width = bbox[2] - bbox[0]

    try:
        ascent, descent = font.getmetrics()
        scale = 0.98 if chunky_blocks else 0.92
        line_height = int(math.ceil((ascent + descent) * scale))
    except AttributeError:
        bbox = font.getbbox("Hg")
        line_height = bbox[3] - bbox[1]

    return max(1, char_width), max(1, line_height)


def _apply_dither_mode(luma: np.ndarray, mode: str, frame_index: int) -> np.ndarray:
    normalized = (mode or "None").strip().lower()
    if normalized == "none":
        return np.clip(luma, 0.0, 1.0)
    values = np.clip(luma.astype(np.float32), 0.0, 1.0)
    rows, cols = values.shape
    if normalized == "bayer":
        matrix = np.array(
            [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
            dtype=np.float32,
        ) / 16.0
        threshold = np.tile(matrix, (rows // 4 + 1, cols // 4 + 1))[:rows, :cols]
        return np.clip(values + (threshold - 0.5) * 0.24, 0.0, 1.0)
    if normalized == "floyd-steinberg":
        work = values.copy()
        quantized = np.zeros_like(work)
        levels = 5.0
        for y in range(rows):
            for x in range(cols):
                old = work[y, x]
                new = round(old * levels) / levels
                quantized[y, x] = new
                error = old - new
                if x + 1 < cols:
                    work[y, x + 1] += error * 7 / 16
                if y + 1 < rows:
                    if x > 0:
                        work[y + 1, x - 1] += error * 3 / 16
                    work[y + 1, x] += error * 5 / 16
                    if x + 1 < cols:
                        work[y + 1, x + 1] += error * 1 / 16
        return np.clip(quantized, 0.0, 1.0)
    if normalized == "crt dot matrix":
        yy, xx = np.indices(values.shape)
        dots = (((xx + frame_index) % 3 == 0) | ((yy + frame_index) % 3 == 0)).astype(np.float32)
        return np.clip(values * (0.82 + dots * 0.24), 0.0, 1.0)
    if normalized == "pocket camera":
        return np.floor(values * 3.99) / 3.0
    if normalized == "newspaper halftone":
        yy, xx = np.indices(values.shape)
        pattern = (np.sin((xx + yy) * 0.9) + np.sin((xx - yy) * 0.7)) * 0.08
        return np.clip(values + pattern, 0.0, 1.0)
    return np.clip(values, 0.0, 1.0)


def _character_for_brightness(charset: str, brightness: float) -> str:
    clamped = max(0.0, min(1.0, brightness))
    index = int(clamped * (len(charset) - 1))
    return charset[index]


def _character_color(
    rgb: np.ndarray,
    brightness: float,
    preset: dict[str, Any],
    frame_index: int,
    effects: dict[str, bool],
    intensity: float,
) -> tuple[int, int, int]:
    color = rgb.astype(np.float32)
    tint = preset.get("tint")
    if tint:
        tint_color = np.array(tint, dtype=np.float32) * (0.18 + (0.92 * brightness))
        mix = float(preset["tint_mix"])
        color = (color * (1.0 - mix)) + (tint_color * mix)

    if _effect_on(effects, "color_drift"):
        hue_speed = float(preset.get("hue_speed", 0.0)) + 0.02 * intensity
        color = np.array(_shift_hue(color, frame_index * hue_speed), dtype=np.float32)

    color = np.clip(color, 0, 255)
    return int(color[0]), int(color[1]), int(color[2])


def _shift_hue(color: np.ndarray, amount: float) -> tuple[int, int, int]:
    red, green, blue = (max(0.0, min(1.0, channel / 255.0)) for channel in color)
    hue, saturation, value = colorsys.rgb_to_hsv(red, green, blue)
    shifted = colorsys.hsv_to_rgb((hue + amount) % 1.0, saturation, value)
    return tuple(int(channel * 255) for channel in shifted)


def _apply_ansi_output_effects(
    image: Image.Image,
    preset: dict[str, Any],
    frame_index: int,
    rng: random.Random,
    layout: TextLayout,
    effects: dict[str, bool],
    intensity: float,
    fps: int,
) -> Image.Image:
    if _effect_on(effects, "vhs_wobble"):
        image = _apply_vhs_wobble(image, frame_index, intensity)

    if _effect_on(effects, "color_drift"):
        image = _hue_shift_image(image, frame_index * 0.35 * intensity)

    arr = np.array(image, dtype=np.uint8)

    if _effect_on(effects, "scanlines"):
        gap = max(2, layout.line_height // 2)
        strength = min(0.78, float(preset.get("scanline_strength", 0.2)) * max(0.2, intensity))
        arr = np.asarray(_apply_scanlines(Image.fromarray(arr), gap, strength), dtype=np.uint8)

    if _effect_on(effects, "rgb_split"):
        amount = int(round((float(preset.get("rgb_split", 2)) + 2.5 * intensity)))
        if amount:
            shifted = arr.copy()
            shifted[:, :, 0] = np.roll(arr[:, :, 0], amount, axis=1)
            shifted[:, :, 2] = np.roll(arr[:, :, 2], -amount, axis=1)
            arr = shifted

    if _effect_on(effects, "glitch"):
        slice_count = int(round((2 + 5 * intensity) * float(preset.get("glitch_strength", 1.0))))
        height = arr.shape[0]
        for _ in range(max(0, slice_count)):
            if rng.random() > min(0.96, 0.48 + 0.18 * intensity):
                continue
            slice_height = rng.randint(2, max(3, int(18 * max(0.5, intensity))))
            y = rng.randint(0, max(0, height - slice_height))
            shift = rng.randint(-int(48 * intensity) - 1, int(48 * intensity) + 1)
            arr[y : y + slice_height, :, :] = np.roll(arr[y : y + slice_height, :, :], shift, axis=1)

    return Image.fromarray(arr, mode="RGB")


def _apply_scanlines(image: Image.Image, line_gap: int, strength: float) -> Image.Image:
    arr = np.array(image, dtype=np.uint8)
    line_gap = max(2, int(line_gap))
    strength = max(0.0, min(0.95, strength))
    arr[::line_gap, :, :] = (arr[::line_gap, :, :].astype(np.float32) * (1.0 - strength)).astype(
        np.uint8
    )
    if line_gap > 3:
        arr[1::line_gap, :, :] = (
            arr[1::line_gap, :, :].astype(np.float32) * (1.0 - strength * 0.45)
        ).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _apply_vhs_wobble(image: Image.Image, frame_index: int, intensity: float) -> Image.Image:
    arr = np.array(image, dtype=np.uint8)
    height = arr.shape[0]
    amplitude = max(1, int(round(4 * max(0.1, intensity))))
    phase = frame_index * 0.16
    for y in range(height):
        shift = int(round(math.sin((y * 0.027) + phase) * amplitude))
        if shift:
            arr[y, :, :] = np.roll(arr[y, :, :], shift, axis=0)
    return Image.fromarray(arr, mode="RGB")


def _hue_shift_image(image: Image.Image, amount: float) -> Image.Image:
    hsv = np.array(image.convert("HSV"), dtype=np.uint8)
    shifted = (hsv[:, :, 0].astype(np.uint16) + int(amount)) % 256
    hsv[:, :, 0] = shifted.astype(np.uint8)
    return Image.fromarray(hsv, mode="HSV").convert("RGB")


def _zoom_crop(image: Image.Image, zoom: float, center_x: float, center_y: float) -> Image.Image:
    width, height = image.size
    zoom = max(1.0, zoom)
    crop_w = max(1, int(width / zoom))
    crop_h = max(1, int(height / zoom))
    cx = int(width * max(0.0, min(1.0, center_x)))
    cy = int(height * max(0.0, min(1.0, center_y)))
    left = max(0, min(width - crop_w, cx - crop_w // 2))
    top = max(0, min(height - crop_h, cy - crop_h // 2))
    return image.crop((left, top, left + crop_w, top + crop_h)).resize(
        (width, height), Image.Resampling.LANCZOS
    )


def _coerce_block(block: Any) -> Interval:
    if isinstance(block, dict):
        start = _coerce_time(block.get("start", 0.0))
        end = _coerce_time(block.get("end", 0.0))
        return start, end
    if isinstance(block, (list, tuple)) and len(block) >= 2:
        return _coerce_time(block[0]), _coerce_time(block[1])
    raise ValueError(f"Invalid manual block: {block!r}")


def _coerce_time(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parsed = ffmpeg_utils.parse_timecode(str(value))
    if parsed is None:
        return 0.0
    return parsed


def _add_random_intervals(
    intervals: list[Interval],
    duration: float,
    target_seconds: float,
    min_len: float,
    max_len: float,
    seed: int | None,
) -> list[Interval]:
    if target_seconds <= 0:
        return intervals

    rng = random.Random(seed)
    result = list(intervals)
    available = _available_gaps(result, duration)
    available_seconds = _interval_total(available)
    if available_seconds <= 0:
        return result
    if target_seconds >= available_seconds - 0.02:
        return _merge_intervals(result + available, duration)

    random_added = 0.0
    attempts = 0
    while random_added < target_seconds - 0.05 and attempts < 3000:
        attempts += 1
        min_chunk = min(min_len, duration)
        if random_added > 0 and target_seconds - random_added < min_chunk:
            break
        gaps = [gap for gap in _available_gaps(result, duration) if gap[1] - gap[0] >= min_chunk]
        if not gaps:
            break
        gap = _weighted_gap_choice(gaps, rng)
        gap_len = gap[1] - gap[0]
        remaining = target_seconds - random_added
        if remaining < min_chunk:
            chunk_len = min_chunk
        else:
            chunk_max = min(max_len, gap_len, remaining)
            if chunk_max < min_chunk:
                continue
            chunk_len = rng.uniform(min_chunk, chunk_max)
        if chunk_len < min_chunk:
            break
        if gap_len <= chunk_len + 0.02:
            start = gap[0]
        else:
            start = rng.uniform(gap[0], gap[1] - chunk_len)
        candidate = (start, start + chunk_len)
        result = _merge_intervals(result + [candidate], duration)
        random_added += chunk_len
    return result


def _weighted_gap_choice(gaps: list[Interval], rng: random.Random) -> Interval:
    total = _interval_total(gaps)
    pick = rng.random() * total
    cursor = 0.0
    for gap in gaps:
        cursor += gap[1] - gap[0]
        if pick <= cursor:
            return gap
    return gaps[-1]


def _available_gaps(intervals: list[Interval], duration: float) -> list[Interval]:
    merged = _merge_intervals(intervals, duration)
    gaps: list[Interval] = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        gaps.append((cursor, duration))
    return gaps


def _merge_intervals(intervals: Iterable[Interval], duration: float) -> list[Interval]:
    cleaned: list[Interval] = []
    for start, end in intervals:
        start = max(0.0, min(float(start), duration))
        end = max(0.0, min(float(end), duration))
        if end - start > 0.001:
            cleaned.append((start, end))
    cleaned.sort(key=lambda item: item[0])

    merged: list[Interval] = []
    for start, end in cleaned:
        if not merged or start > merged[-1][1] + 0.001:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _interval_total(intervals: Iterable[Interval]) -> float:
    return sum(max(0.0, end - start) for start, end in intervals)


def _effect_on(effects: dict[str, bool], key: str) -> bool:
    return bool(effects.get(key, False))


def _emit(log: LogCallback, message: str) -> None:
    if log:
        log(message)


def _emit_progress(progress: ProgressCallback, value: int) -> None:
    if progress:
        progress(max(0, min(100, value)))
