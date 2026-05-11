"""ffmpeg and ffprobe helpers for WZRD.VID."""

from __future__ import annotations

import copy
import json
import math
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO, Callable


LogCallback = Callable[[str], None] | None
MACOS_HOMEBREW_DIRS = [
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
]
UNIX_FALLBACK_DIRS = [Path("/usr/bin"), Path("/bin")]
_PROBE_CACHE_MAX = 256
_PROBE_CACHE: dict[tuple[str, int, int], dict] = {}


class FFmpegError(RuntimeError):
    """Raised when ffmpeg or ffprobe cannot complete the requested operation."""


def _log(log: LogCallback, message: str) -> None:
    if log:
        log(message)


def require_binary(name: str) -> str:
    """Return an ffmpeg/ffprobe executable path with platform-aware fallbacks."""
    for binary_name in _binary_names(name):
        path = shutil.which(binary_name)
        if path:
            return path

    for directory in _common_binary_dirs():
        for binary_name in _binary_names(name):
            candidate = directory / binary_name
            if candidate.exists() and candidate.is_file():
                return str(candidate)

    raise FFmpegError(f"Could not find '{name}'. {install_guidance()}")


def _binary_names(name: str) -> list[str]:
    if platform.system() == "Windows" and not name.lower().endswith(".exe"):
        return [name, f"{name}.exe"]
    return [name]


def _common_binary_dirs() -> list[Path]:
    system = platform.system()
    if system == "Darwin":
        return MACOS_HOMEBREW_DIRS + UNIX_FALLBACK_DIRS
    if system == "Windows":
        return []
    return [Path("/usr/local/bin")] + UNIX_FALLBACK_DIRS


def install_guidance() -> str:
    system = platform.system()
    if system == "Darwin":
        return "Install ffmpeg with Homebrew: brew install ffmpeg"
    if system == "Windows":
        return "Install ffmpeg and make sure ffmpeg.exe and ffprobe.exe are on PATH. Try: winget install Gyan.FFmpeg"
    if system == "Linux":
        return "Install ffmpeg with your package manager, for example: sudo apt install ffmpeg, sudo dnf install ffmpeg, or sudo pacman -S ffmpeg"
    return "Install ffmpeg and make sure ffmpeg and ffprobe are on PATH."


def run_command(args: list[str], log: LogCallback = None) -> subprocess.CompletedProcess[str]:
    """Run a subprocess without a shell so paths with spaces are handled safely."""
    display = " ".join(_quote_arg(arg) for arg in args)
    _log(log, display)
    completed = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        if len(details) > 4000:
            details = details[-4000:]
        raise FFmpegError(f"Command failed ({completed.returncode}): {display}\n{details}")
    return completed


def _quote_arg(arg: str) -> str:
    if not arg:
        return "''"
    if any(ch.isspace() or ch in "'\"()[]{}&;|" for ch in arg):
        return "'" + arg.replace("'", "'\\''") + "'"
    return arg


def parse_timecode(value: str | None) -> float | None:
    """Parse seconds, MM:SS, or HH:MM:SS into seconds.

    Empty values and "auto" return None so callers can treat an omitted end
    time as the media duration.
    """
    if value is None:
        return None
    raw = value.strip()
    if not raw or raw.lower() == "auto":
        return None

    parts = raw.split(":")
    if len(parts) == 1:
        return _nonnegative_float(parts[0], raw)
    if len(parts) > 3:
        raise ValueError(f"Invalid time '{raw}'. Use seconds, MM:SS, or HH:MM:SS.")

    total = 0.0
    for part in parts:
        if part == "":
            raise ValueError(f"Invalid time '{raw}'.")
        total = total * 60.0 + _nonnegative_float(part, raw)
    return total


def _nonnegative_float(value: str, raw: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid time '{raw}'.") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"Invalid time '{raw}'. Times must be non-negative.")
    return parsed


def format_duration(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds):
        return "unknown"
    whole = int(seconds)
    frac = seconds - whole
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        base = f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        base = f"{minutes}:{secs:02d}"
    if frac >= 0.01:
        return f"{base}.{int(frac * 100):02d}"
    return base


def probe_media(path: str | Path) -> dict:
    ffprobe_path = require_binary("ffprobe")
    media = Path(path).expanduser()
    media_path = str(media)
    if not media.exists():
        raise FileNotFoundError(f"File does not exist: {media_path}")
    cache_key = _probe_cache_key(media)
    cached = _PROBE_CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    args = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,duration,width,height,r_frame_rate,avg_frame_rate,bit_rate,pix_fmt",
        "-of",
        "json",
        media_path,
    ]
    completed = run_command(args)
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise FFmpegError(f"ffprobe returned invalid JSON for {media_path}") from exc
    _remember_probe(cache_key, data)
    return copy.deepcopy(data)


def _probe_cache_key(media_path: Path) -> tuple[str, int, int]:
    stat = media_path.stat()
    return (
        str(media_path.resolve(strict=False)),
        int(stat.st_mtime_ns),
        int(stat.st_size),
    )


def _remember_probe(cache_key: tuple[str, int, int], data: dict) -> None:
    if len(_PROBE_CACHE) >= _PROBE_CACHE_MAX:
        _PROBE_CACHE.pop(next(iter(_PROBE_CACHE)))
    _PROBE_CACHE[cache_key] = copy.deepcopy(data)


def first_stream(path: str | Path, codec_type: str) -> dict | None:
    data = probe_media(path)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == codec_type:
            return stream
    return None


def has_audio_stream(path: str | Path) -> bool:
    return first_stream(path, "audio") is not None


def get_stream_duration(path: str | Path, codec_type: str) -> float:
    data = probe_media(path)
    for stream in data.get("streams", []):
        if stream.get("codec_type") != codec_type:
            continue
        raw_duration = stream.get("duration")
        if raw_duration not in (None, "N/A"):
            return float(raw_duration)
    if codec_type == "audio":
        # Some containers omit per-stream duration; use format duration only after
        # confirming the audio stream exists.
        if not any(stream.get("codec_type") == "audio" for stream in data.get("streams", [])):
            raise FFmpegError(f"Could not find an audio stream in {path}")
    elif codec_type == "video":
        if not any(stream.get("codec_type") == "video" for stream in data.get("streams", [])):
            raise FFmpegError(f"Could not find a video stream in {path}")
    format_duration_raw = data.get("format", {}).get("duration")
    if format_duration_raw not in (None, "N/A"):
        return float(format_duration_raw)
    raise FFmpegError(f"Could not determine {codec_type} duration for {path}")


def get_audio_duration(path: str | Path) -> float:
    return get_stream_duration(path, "audio")


def get_video_info(path: str | Path) -> dict[str, float | int | str]:
    stream = first_stream(path, "video")
    if not stream:
        raise FFmpegError(f"Could not find a video stream in {path}")
    width = int(stream.get("width", 0) or 0)
    height = int(stream.get("height", 0) or 0)
    fps = _parse_frame_rate(str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"))
    return {"width": width, "height": height, "fps": fps}


def get_duration(path: str | Path) -> float:
    data = probe_media(path)
    candidates: list[float] = []
    format_duration_raw = data.get("format", {}).get("duration")
    if format_duration_raw not in (None, "N/A"):
        candidates.append(float(format_duration_raw))
    for stream in data.get("streams", []):
        raw_duration = stream.get("duration")
        if raw_duration not in (None, "N/A"):
            candidates.append(float(raw_duration))
    if not candidates:
        raise FFmpegError(f"Could not determine duration for {path}")
    return max(candidates)


def extract_still_frame(source_path: str | Path, output_path: str | Path, log: LogCallback = None) -> Path:
    """Use ffmpeg to decode a still/image source to a single image file."""
    ffmpeg_path = require_binary("ffmpeg")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source_path),
        "-frames:v",
        "1",
        str(output),
    ]
    run_command(args, log)
    return output


def _parse_frame_rate(raw: str) -> float:
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        try:
            den = float(denominator)
            if den == 0:
                return 0.0
            return float(numerator) / den
        except ValueError:
            return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def validate_time_range(
    start: float | None,
    end: float | None,
    duration: float,
    label: str,
) -> tuple[float, float]:
    resolved_start = 0.0 if start is None else start
    resolved_end = duration if end is None else end

    if resolved_start < 0:
        raise ValueError(f"{label} start time cannot be negative.")
    if resolved_end <= resolved_start:
        raise ValueError(f"{label} end time must be after its start time.")
    if resolved_start >= duration:
        raise ValueError(
            f"{label} start time {format_duration(resolved_start)} is outside the "
            f"{format_duration(duration)} file."
        )
    if resolved_end > duration + 0.05:
        raise ValueError(
            f"{label} end time {format_duration(resolved_end)} is beyond the "
            f"{format_duration(duration)} file."
        )

    return resolved_start, min(resolved_end, duration)


def encode_frames_to_mp4(
    frames_pattern: str | Path,
    fps: int,
    output_path: str | Path,
    log: LogCallback = None,
    *,
    crf: int = 22,
    video_bitrate: int | None = None,
) -> None:
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(frames_pattern),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
    ]
    if video_bitrate is not None:
        bitrate = max(100_000, int(video_bitrate))
        args.extend(
            [
                "-b:v",
                str(bitrate),
                "-maxrate",
                str(bitrate),
                "-bufsize",
                str(max(200_000, bitrate * 2)),
            ]
        )
    else:
        args.extend(["-crf", str(max(14, min(40, int(crf))))])
    args.extend(
        [
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    run_command(args, log)


def encode_raw_rgb_frames_to_mp4(
    write_frames: Callable[[BinaryIO], None],
    width: int,
    height: int,
    fps: int,
    output_path: str | Path,
    log: LogCallback = None,
    *,
    crf: int = 22,
    video_bitrate: int | None = None,
) -> None:
    """Encode raw RGB24 frames written to ffmpeg stdin as an H.264 MP4."""
    if width <= 0 or height <= 0:
        raise FFmpegError(f"Invalid raw frame size: {width}x{height}")
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
    ]
    if video_bitrate is not None:
        bitrate = max(100_000, int(video_bitrate))
        args.extend(
            [
                "-b:v",
                str(bitrate),
                "-maxrate",
                str(bitrate),
                "-bufsize",
                str(max(200_000, bitrate * 2)),
            ]
        )
    else:
        args.extend(["-crf", str(max(14, min(40, int(crf))))])
    args.extend(
        [
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    display = " ".join(_quote_arg(arg) for arg in args)
    _log(log, display)
    process = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if process.stdin is None:
        raise FFmpegError("ffmpeg raw frame pipe did not provide stdin.")

    try:
        try:
            write_frames(process.stdin)
        except Exception as exc:
            try:
                process.stdin.close()
            except OSError:
                pass
            stderr = process.stderr.read() if process.stderr else b""
            if process.poll() is None:
                process.kill()
            process.wait()
            details = _trim_subprocess_details(stderr)
            if details:
                raise FFmpegError(f"Raw frame pipe encode failed while writing frames:\n{details}") from exc
            raise

        process.stdin.close()
        stderr = process.stderr.read() if process.stderr else b""
        return_code = process.wait()
    except FFmpegError:
        raise
    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait()
        raise

    if return_code != 0:
        details = _trim_subprocess_details(stderr)
        raise FFmpegError(f"Command failed ({return_code}): {display}\n{details}")


def _trim_subprocess_details(stderr: bytes | str) -> str:
    if isinstance(stderr, bytes):
        details = stderr.decode(errors="replace").strip()
    else:
        details = stderr.strip()
    if len(details) > 4000:
        return details[-4000:]
    return details


def parse_bitrate_bits_per_second(value: str | int | float | None) -> int:
    """Parse ffmpeg-style bitrates like 64k or 1.5M into bits per second."""
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))

    raw = value.strip().lower()
    if not raw:
        return 0
    multiplier = 1
    if raw.endswith("kbps"):
        raw = raw[:-4].strip()
        multiplier = 1000
    elif raw.endswith("k"):
        raw = raw[:-1].strip()
        multiplier = 1000
    elif raw.endswith("mbps"):
        raw = raw[:-4].strip()
        multiplier = 1_000_000
    elif raw.endswith("m"):
        raw = raw[:-1].strip()
        multiplier = 1_000_000
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid bitrate '{value}'. Use values like 64k or 1.5M.") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError(f"Invalid bitrate '{value}'. Bitrate must be non-negative.")
    return int(parsed * multiplier)


def target_video_bitrate(
    target_mb: float | None,
    duration_seconds: float,
    audio_bitrate: str | int | float | None,
    *,
    minimum_bitrate: int = 100_000,
    safety_margin: float = 1.0,
) -> int | None:
    """Return a video bitrate that aims for target_mb total output size."""
    if target_mb is None:
        return None
    if duration_seconds <= 0:
        raise ValueError("Duration must be positive when targeting a file size.")
    if not math.isfinite(target_mb) or target_mb <= 0:
        raise ValueError("Target file size must be greater than 0 MB.")

    effective_target_mb = target_mb * safety_margin
    target_total_bits = effective_target_mb * 8 * 1024 * 1024
    audio_bits = parse_bitrate_bits_per_second(audio_bitrate) * duration_seconds
    video_bitrate = (target_total_bits - audio_bits) / duration_seconds
    return max(int(minimum_bitrate), int(video_bitrate))


def file_size_mb(path: str | Path) -> float:
    return Path(path).stat().st_size / (1024 * 1024)


def write_silent_output(
    video_path: str | Path,
    output_path: str | Path,
    log: LogCallback = None,
) -> None:
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-c:v",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run_command(args, log)


def mux_audio(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    audio_start: float,
    audio_end: float | None,
    output_duration: float,
    audio_bitrate: str = "128k",
    fade_out_duration: float = 0.0,
    audio_offset: float = 0.0,
    audio_output_end: float | None = None,
    worky_music_mode: bool = False,
    log: LogCallback = None,
) -> None:
    """Mux trimmed audio with an already encoded video.

    The output duration follows the rendered video duration. If the selected
    audio is longer, it is trimmed. If it is shorter, the video remains silent
    after the audio stream ends. `audio_offset` delays external audio inside
    the rendered timeline while preserving total output duration.
    """
    ffmpeg_path = require_binary("ffmpeg")
    output_duration = max(0.001, float(output_duration))
    audio_start = max(0.0, float(audio_start or 0.0))
    offset = max(0.0, min(float(audio_offset or 0.0), output_duration))
    output_end = output_duration if audio_output_end is None else min(output_duration, max(offset, float(audio_output_end)))
    output_span = max(0.0, output_end - offset)
    source_span = output_span if audio_end is None else min(output_span, max(0.0, float(audio_end) - audio_start))
    source_span = max(0.001, source_span)

    delay_ms = max(0, int(round(offset * 1000)))
    duration_text = f"{output_duration:.6f}"
    audio_chain = f"[1:a:0]atrim=0:{source_span:.6f},asetpts=PTS-STARTPTS"
    if worky_music_mode:
        audio_chain += _worky_music_filter_suffix()
    if delay_ms:
        audio_chain += f",adelay={delay_ms}:all=1"
    audio_chain += f",apad,atrim=0:{duration_text},asetpts=PTS-STARTPTS"
    fade_out_duration = max(0.0, min(float(fade_out_duration or 0.0), output_duration))
    if fade_out_duration > 0.05:
        fade_start = max(0.0, output_duration - fade_out_duration)
        audio_chain += f",afade=t=out:st={fade_start:.6f}:d={fade_out_duration:.6f}"
    audio_chain += "[aud]"

    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-ss",
        f"{audio_start:.6f}",
        "-t",
        f"{source_span:.6f}",
        "-i",
        str(audio_path),
        "-filter_complex",
        audio_chain,
        "-map",
        "0:v:0",
        "-map",
        "[aud]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        _worky_music_bitrate(audio_bitrate, worky_music_mode),
        "-t",
        duration_text,
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run_command(args, log)

def build_timeline_audio(
    segments: list[object],
    timeline_start: float,
    output_duration: float,
    output_path: str | Path,
    work_dir: str | Path,
    *,
    audio_bitrate: str = "128k",
    fade_out_duration: float = 0.0,
    log: LogCallback = None,
) -> Path | None:
    """Build an AAC source-audio track for a rendered timeline selection.

    Video segments with audio are trimmed to match their visual segment. Photo
    segments and video segments without audio become silence. If no real source
    audio exists in the selected range, return None so callers can write a
    silent MP4 without adding an empty audio stream.
    """
    if output_duration <= 0:
        return None
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)
    selection_start = float(timeline_start)
    selection_end = selection_start + float(output_duration)
    pieces: list[Path] = []
    found_real_audio = False

    for index, segment in enumerate(segments):
        segment_start = float(getattr(segment, "timeline_start"))
        segment_duration = float(getattr(segment, "duration"))
        segment_end = float(getattr(segment, "timeline_end", segment_start + segment_duration))
        start = max(selection_start, segment_start)
        end = min(selection_end, segment_end)
        part_duration = end - start
        if part_duration <= 0.01:
            continue
        piece = work_path / f"audio_piece_{index:04d}.wav"
        kind = str(getattr(segment, "kind", "video")).lower()
        source_path = Path(str(getattr(segment, "path", "")))
        include_audio = bool(getattr(segment, "include_audio", False))
        if kind == "video" and include_audio and source_path.exists() and has_audio_stream(source_path):
            source_start = float(getattr(segment, "source_start", 0.0)) + (start - segment_start)
            _extract_audio_piece(source_path, source_start, part_duration, piece, log)
            found_real_audio = True
        else:
            _write_silence_piece(part_duration, piece, log)
        pieces.append(piece)

    if not pieces or not found_real_audio:
        return None

    list_path = work_path / "concat.txt"
    list_path.write_text("".join(_concat_file_line(piece) for piece in pieces))
    output = Path(output_path)
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
    ]
    fade_out_duration = max(0.0, min(float(fade_out_duration or 0.0), float(output_duration)))
    if fade_out_duration > 0.05:
        fade_start = max(0.0, float(output_duration) - fade_out_duration)
        args.extend(["-af", f"afade=t=out:st={fade_start:.6f}:d={fade_out_duration:.6f}"])
    args.extend(["-c:a", "aac", "-b:a", audio_bitrate, "-t", f"{output_duration:.6f}", str(output)])
    run_command(args, log)
    return output


def mix_external_and_source_audio(
    external_audio_path: str | Path,
    source_audio_path: str | Path,
    output_path: str | Path,
    external_start: float,
    external_end: float | None,
    output_duration: float,
    *,
    audio_bitrate: str = "128k",
    external_volume: float = 1.0,
    source_volume: float = 1.0,
    external_offset: float = 0.0,
    external_output_end: float | None = None,
    worky_music_mode: bool = False,
    log: LogCallback = None,
) -> Path:
    """Trim external audio, place it in output time, mix with source audio, and encode AAC."""
    if output_duration <= 0:
        raise ValueError("Output duration must be positive when mixing audio.")
    ffmpeg_path = require_binary("ffmpeg")
    output = Path(output_path)
    external_start = max(0.0, float(external_start or 0.0))
    output_duration = float(output_duration)
    offset = max(0.0, min(float(external_offset or 0.0), output_duration))
    output_end = output_duration if external_output_end is None else min(output_duration, max(offset, float(external_output_end)))
    output_span = max(0.0, output_end - offset)
    external_duration = output_span
    if external_end is not None:
        external_duration = min(output_span, max(0.0, float(external_end) - external_start))
    external_duration = max(0.001, external_duration)

    ext_vol = max(0.0, float(external_volume or 0.0))
    src_vol = max(0.0, float(source_volume or 0.0))
    delay_ms = max(0, int(round(offset * 1000)))
    duration_text = f"{output_duration:.6f}"
    external_chain = f"[0:a:0]volume={ext_vol:.4f},atrim=0:{external_duration:.6f},asetpts=PTS-STARTPTS"
    if worky_music_mode:
        external_chain += _worky_music_filter_suffix()
    if delay_ms:
        external_chain += f",adelay={delay_ms}:all=1"
    external_chain += f",apad,atrim=0:{duration_text},asetpts=PTS-STARTPTS[a0]"
    filter_complex = (
        f"{external_chain};"
        f"[1:a:0]volume={src_vol:.4f},atrim=0:{duration_text},asetpts=PTS-STARTPTS[a1];"
        f"[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0,"
        f"atrim=0:{duration_text},asetpts=PTS-STARTPTS[mix]"
    )
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{external_start:.6f}",
        "-t",
        f"{external_duration:.6f}",
        "-i",
        str(external_audio_path),
        "-i",
        str(source_audio_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[mix]",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-t",
        duration_text,
        str(output),
    ]
    run_command(args, log)
    return output


def _worky_music_filter_suffix() -> str:
    return (
        ",highpass=f=90"
        ",lowpass=f=4800"
        ",acompressor=threshold=-18dB:ratio=2.5:attack=20:release=120"
        ",aformat=sample_rates=24000:channel_layouts=mono"
    )


def _worky_music_bitrate(audio_bitrate: str, enabled: bool) -> str:
    return "32k" if enabled else audio_bitrate

def _extract_audio_piece(
    source_path: Path,
    source_start: float,
    duration: float,
    output_path: Path,
    log: LogCallback,
) -> None:
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{source_start:.6f}",
        "-t",
        f"{duration:.6f}",
        "-i",
        str(source_path),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    run_command(args, log)


def _write_silence_piece(duration: float, output_path: Path, log: LogCallback) -> None:
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-t",
        f"{duration:.6f}",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    run_command(args, log)


def _concat_file_line(path: Path) -> str:
    escaped = str(path).replace("'", "'\\''")
    return f"file '{escaped}'\n"


def optimize_mp4_to_target(
    input_path: str | Path,
    output_path: str | Path,
    target_mb: float,
    audio_bitrate: str,
    log: LogCallback = None,
    *,
    safety_margin: float = 0.93,
    two_pass: bool = True,
) -> dict[str, float | int | str | bool]:
    """Transcode an MP4 toward a max size while preserving phone compatibility."""
    source = Path(input_path)
    destination = Path(output_path)
    if source.resolve(strict=False) == destination.resolve(strict=False):
        raise ValueError("Optimized output path must be different from the source MP4.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    duration = get_duration(source)
    video_info = get_video_info(source)
    source_width = int(video_info["width"])
    source_height = int(video_info["height"])
    source_fps = float(video_info["fps"]) or 24.0
    has_audio = has_audio_stream(source)
    encode_audio_bitrate = audio_bitrate if has_audio else "0k"
    video_bitrate = target_video_bitrate(
        target_mb,
        duration,
        encode_audio_bitrate if has_audio else None,
        minimum_bitrate=150_000,
        safety_margin=safety_margin,
    )
    if video_bitrate is None:
        raise ValueError("Could not calculate target video bitrate.")

    _log(log, "Auto Optimize Output:")
    _log(log, f"  duration: {format_duration(duration)}")
    _log(log, f"  target: {target_mb:.1f} MB ({safety_margin:.0%} safety target)")
    _log(log, f"  video bitrate: {video_bitrate / 1000:.0f} kbps")
    _log(log, f"  audio bitrate: {encode_audio_bitrate if has_audio else 'none'}")

    attempts = _optimization_attempts(source_width, source_height, source_fps)
    last_result: dict[str, float | int | str | bool] | None = None
    with tempfile.TemporaryDirectory(prefix="wzrd_vid_ffmpeg_pass_") as pass_root:
        passlog = str(Path(pass_root) / "x264_pass")
        for attempt_index, (max_width, fps) in enumerate(attempts, start=1):
            target_width, target_height = _scaled_dimensions(source_width, source_height, max_width)
            filters = _video_filters(source_width, source_height, source_fps, target_width, target_height, fps)
            _log(
                log,
                f"  optimize pass {attempt_index}: {target_width}x{target_height} at {fps:.2f} fps",
            )
            try:
                if two_pass:
                    _transcode_two_pass(
                        source,
                        destination,
                        video_bitrate,
                        encode_audio_bitrate,
                        has_audio,
                        filters,
                        passlog,
                        log,
                    )
                else:
                    _transcode_one_pass(
                        source,
                        destination,
                        video_bitrate,
                        encode_audio_bitrate,
                        has_audio,
                        filters,
                        log,
                    )
            except FFmpegError as exc:
                if not two_pass:
                    raise
                _log(log, f"  two-pass encode failed; retrying one-pass bitrate mode: {exc}")
                _transcode_one_pass(
                    source,
                    destination,
                    video_bitrate,
                    encode_audio_bitrate,
                    has_audio,
                    filters,
                    log,
                )

            size_mb = file_size_mb(destination)
            last_result = {
                "output_path": str(destination),
                "size_mb": size_mb,
                "target_mb": target_mb,
                "duration": duration,
                "video_bitrate": video_bitrate,
                "audio_bitrate": encode_audio_bitrate,
                "width": target_width,
                "height": target_height,
                "fps": fps,
                "within_target": size_mb <= target_mb,
            }
            _log(log, f"  optimized file size: {size_mb:.2f} MB")
            if size_mb <= target_mb:
                return last_result
            if attempt_index < len(attempts):
                _log(log, "  optimized file is over target; reducing output dimensions/FPS and retrying.")

    if last_result is None:
        raise FFmpegError("Optimization did not produce an output file.")
    _log(log, f"  warning: optimized file is still over the {target_mb:.1f} MB target.")
    return last_result


def _optimization_attempts(width: int, height: int, fps: float) -> list[tuple[int, float]]:
    width_steps = [2560, 1920, 1280, 960, 720, 540, 360, 240]
    current = max(240, int(width))
    lower_width = next((step for step in width_steps if step < current), 240)
    lower_fps = max(8.0, float(fps) - 4.0)
    attempts = [
        (current, float(fps)),
        (lower_width, float(fps)),
        (lower_width, lower_fps),
    ]
    deduped: list[tuple[int, float]] = []
    for attempt in attempts:
        if attempt not in deduped:
            deduped.append(attempt)
    return deduped


def _scaled_dimensions(source_width: int, source_height: int, max_width: int) -> tuple[int, int]:
    target_width = min(source_width, max(240, int(max_width)))
    if target_width % 2:
        target_width -= 1
    if source_width <= 0 or source_height <= 0:
        return target_width, max(2, int(target_width * 9 / 16) // 2 * 2)
    target_height = int(round(source_height * (target_width / source_width)))
    if target_height % 2:
        target_height += 1
    return max(2, target_width), max(2, target_height)


def _video_filters(
    source_width: int,
    source_height: int,
    source_fps: float,
    target_width: int,
    target_height: int,
    target_fps: float,
) -> str | None:
    filters: list[str] = []
    if target_width < source_width or target_height < source_height:
        filters.append(f"scale={target_width}:{target_height}")
    if target_fps > 0 and abs(target_fps - source_fps) > 0.1:
        filters.append(f"fps={target_fps:.3f}")
    return ",".join(filters) if filters else None


def _video_encode_args(video_bitrate: int) -> list[str]:
    bitrate = max(150_000, int(video_bitrate))
    return [
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-b:v",
        str(bitrate),
        "-maxrate",
        str(bitrate),
        "-bufsize",
        str(max(300_000, bitrate * 2)),
        "-pix_fmt",
        "yuv420p",
    ]


def _transcode_two_pass(
    input_path: Path,
    output_path: Path,
    video_bitrate: int,
    audio_bitrate: str,
    has_audio: bool,
    filters: str | None,
    passlog: str,
    log: LogCallback,
) -> None:
    ffmpeg_path = require_binary("ffmpeg")
    pass1 = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-an",
    ]
    if filters:
        pass1.extend(["-vf", filters])
    pass1.extend(
        _video_encode_args(video_bitrate)
        + [
            "-pass",
            "1",
            "-passlogfile",
            passlog,
            "-f",
            "null",
            "/dev/null",
        ]
    )
    run_command(pass1, log)

    pass2 = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
    ]
    if has_audio:
        pass2.extend(["-map", "0:a:0"])
    if filters:
        pass2.extend(["-vf", filters])
    pass2.extend(_video_encode_args(video_bitrate) + ["-pass", "2", "-passlogfile", passlog])
    if has_audio:
        pass2.extend(["-c:a", "aac", "-b:a", audio_bitrate])
    else:
        pass2.append("-an")
    pass2.extend(["-movflags", "+faststart", str(output_path)])
    run_command(pass2, log)


def _transcode_one_pass(
    input_path: Path,
    output_path: Path,
    video_bitrate: int,
    audio_bitrate: str,
    has_audio: bool,
    filters: str | None,
    log: LogCallback,
) -> None:
    ffmpeg_path = require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
    ]
    if has_audio:
        args.extend(["-map", "0:a:0"])
    if filters:
        args.extend(["-vf", filters])
    args.extend(_video_encode_args(video_bitrate))
    if has_audio:
        args.extend(["-c:a", "aac", "-b:a", audio_bitrate])
    else:
        args.append("-an")
    args.extend(["-movflags", "+faststart", str(output_path)])
    run_command(args, log)
