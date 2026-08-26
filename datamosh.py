"""Authentic MPEG-4 Part 2 interframe manipulation for WZRD.VID.

The user-facing output of this module is always a conventional silent
H.264/yuv420p MP4. MPEG-4 Part 2 elementary streams are temporary prediction
material only and are never written over user source media.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import ffmpeg_utils


LogCallback = Callable[[str], None] | None
START_PREFIX = b"\x00\x00\x01"
VOP_START_CODE = 0xB6
VOP_NAMES = {0: "I", 1: "P", 2: "B", 3: "S"}
DATAMOSH_SEED_SALT = 0x44_41_54_41_4D_4F_53_48


class DatamoshError(RuntimeError):
    """Raised when the authentic compressed-video DATAMOSHING stage fails."""


@dataclass(frozen=True)
class Mpeg4Unit:
    """One MPEG-4 start-code unit, including its complete encoded payload."""

    index: int
    start: int
    end: int
    code: int
    coding_type: int | None
    data: bytes


@dataclass(frozen=True)
class DatamoshEvent:
    operation: str
    frame: int
    absolute_frame: int
    source_p_frame: int
    repeated_at_frames: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "operation": self.operation,
            "frame": self.frame,
            "absolute_frame": self.absolute_frame,
            "source_p_frame": self.source_p_frame,
        }
        if self.repeated_at_frames:
            result["repeated_at_frames"] = list(self.repeated_at_frames)
            result["repeat_count"] = len(self.repeated_at_frames)
        return result


@dataclass(frozen=True)
class DatamoshTransform:
    data: bytes
    events: tuple[DatamoshEvent, ...]
    original_counts: dict[str, int]
    mutated_counts: dict[str, int]
    original_vop_count: int
    mutated_vop_count: int
    input_sha256: str
    output_sha256: str

    @property
    def i_reset_count(self) -> int:
        return sum(event.operation == "I_RESET_SUPPRESSED_WITH_P" for event in self.events)

    @property
    def p_persistence_count(self) -> int:
        return sum(event.operation == "P_PERSISTENCE_REPEAT" for event in self.events)


@dataclass(frozen=True)
class DatamoshResult:
    output_path: Path
    applied: bool
    frame_count: int
    duration: float
    gop_size: int
    eligible_start_frame: int
    events: tuple[DatamoshEvent, ...]
    original_counts: dict[str, int]
    mutated_counts: dict[str, int]
    input_stream_size: int
    manipulated_stream_size: int
    temporary_disk_bytes: int
    intermediate_encode_seconds: float
    transform_seconds: float
    safe_transcode_seconds: float
    manipulated_stream_sha256: str | None

    def evidence(self) -> dict[str, object]:
        return {
            "applied": self.applied,
            "frame_count": self.frame_count,
            "duration": self.duration,
            "gop_size": self.gop_size,
            "eligible_start_frame": self.eligible_start_frame,
            "events": [event.as_dict() for event in self.events],
            "original_counts": self.original_counts,
            "mutated_counts": self.mutated_counts,
            "input_stream_size": self.input_stream_size,
            "manipulated_stream_size": self.manipulated_stream_size,
            "temporary_disk_bytes": self.temporary_disk_bytes,
            "intermediate_encode_seconds": self.intermediate_encode_seconds,
            "transform_seconds": self.transform_seconds,
            "safe_transcode_seconds": self.safe_transcode_seconds,
            "manipulated_stream_sha256": self.manipulated_stream_sha256,
        }


def parse_mpeg4_units(data: bytes) -> tuple[Mpeg4Unit, ...]:
    """Parse bounded MPEG-4 start-code units and classify B6 VOP headers."""
    if not isinstance(data, bytes) or not data:
        raise DatamoshError("DATAMOSHING received an empty MPEG-4 elementary stream.")
    starts: list[int] = []
    cursor = 0
    while cursor < len(data):
        offset = data.find(START_PREFIX, cursor)
        if offset < 0:
            break
        if offset + 3 >= len(data):
            raise DatamoshError(f"DATAMOSHING found a truncated MPEG-4 start code at byte {offset}.")
        starts.append(offset)
        cursor = offset + len(START_PREFIX)
    if not starts:
        raise DatamoshError("DATAMOSHING found no MPEG-4 start codes.")

    units: list[Mpeg4Unit] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(data)
        code = data[start + 3]
        coding_type: int | None = None
        if code == VOP_START_CODE:
            if start + 4 >= end:
                raise DatamoshError(f"DATAMOSHING found a truncated VOP at byte {start}.")
            coding_type = (data[start + 4] >> 6) & 0x03
        units.append(Mpeg4Unit(index, start, end, code, coding_type, data[start:end]))
    return tuple(units)


def vop_units(units: tuple[Mpeg4Unit, ...]) -> tuple[Mpeg4Unit, ...]:
    return tuple(unit for unit in units if unit.code == VOP_START_CODE)


def vop_type_counts(units: tuple[Mpeg4Unit, ...]) -> dict[str, int]:
    counts = {name: 0 for name in VOP_NAMES.values()}
    for unit in vop_units(units):
        if unit.coding_type is None:
            raise DatamoshError("DATAMOSHING found a VOP without a coding type.")
        counts[VOP_NAMES[unit.coding_type]] += 1
    return counts


def transform_mpeg4_part2(
    data: bytes,
    *,
    seed: int | None,
    intensity: float,
    eligible_start_frame: int,
    absolute_frame_offset: int,
    protect_final_gop: bool,
) -> DatamoshTransform:
    """Replace selected encoded I-VOPs and repeat selected encoded P-VOPs."""
    units = parse_mpeg4_units(data)
    vops = vop_units(units)
    if not vops:
        raise DatamoshError("DATAMOSHING found no MPEG-4 Video Object Plane (B6) units.")
    counts = vop_type_counts(units)
    if counts["B"] or counts["S"]:
        raise DatamoshError(
            "DATAMOSHING controlled stream contains unsupported prediction types: "
            f"B={counts['B']}, S={counts['S']}."
        )
    if vops[0].coding_type != 0:
        raise DatamoshError("DATAMOSHING controlled stream does not begin with an I-VOP anchor.")

    start_frame = max(0, min(len(vops), int(eligible_start_frame)))
    if start_frame >= len(vops):
        return _unchanged_transform(data, units, counts)
    if vops[start_frame].coding_type != 0:
        raise DatamoshError(
            "DATAMOSHING could not establish the required clean prediction anchor at "
            f"styled frame {start_frame}."
        )

    protected_tail_start = len(vops)
    if protect_final_gop:
        last_i_frame = max(
            (position for position, unit in enumerate(vops) if unit.coding_type == 0),
            default=len(vops),
        )
        protected_tail_start = max(start_frame + 1, last_i_frame)

    i_candidates = [
        position
        for position, unit in enumerate(vops)
        if start_frame < position < protected_tail_start
        and unit.coding_type == 0
        and vops[position - 1].coding_type == 1
    ]
    p_candidates = [
        position
        for position, unit in enumerate(vops)
        if start_frame + 1 < position < protected_tail_start
        and unit.coding_type == 1
        and vops[position - 1].coding_type == 1
        and vops[position - 2].coding_type == 1
    ]
    i_limit, p_limit, max_repeat = _intensity_policy(intensity, len(i_candidates), len(p_candidates))
    selected_i = sorted(
        sorted(
            i_candidates,
            key=lambda position: _stable_score(seed, 1, absolute_frame_offset + position),
        )[:i_limit]
    )
    p_search = sorted(
        p_candidates,
        key=lambda position: _stable_score(seed, 2, absolute_frame_offset + position),
    )

    replacements: dict[int, bytes] = {}
    occupied = set(selected_i)
    events: list[DatamoshEvent] = []
    for position in selected_i:
        source_position = position - 1
        replacements[vops[position].index] = vops[source_position].data
        events.append(
            DatamoshEvent(
                operation="I_RESET_SUPPRESSED_WITH_P",
                frame=position,
                absolute_frame=absolute_frame_offset + position,
                source_p_frame=source_position,
            )
        )

    p_events = 0
    for start in p_search:
        if p_events >= p_limit:
            break
        if start in occupied or start - 1 in occupied:
            continue
        source_position = start - 1
        source = vops[source_position]
        if source.coding_type != 1:
            continue
        requested = 1 + _stable_score(seed, 3, absolute_frame_offset + start) % max_repeat
        repeated: list[int] = []
        for position in range(start, min(protected_tail_start, start + requested)):
            if position in occupied or vops[position].coding_type != 1:
                break
            repeated.append(position)
        if not repeated:
            continue
        for position in repeated:
            replacements[vops[position].index] = source.data
            occupied.add(position)
        events.append(
            DatamoshEvent(
                operation="P_PERSISTENCE_REPEAT",
                frame=start,
                absolute_frame=absolute_frame_offset + start,
                source_p_frame=source_position,
                repeated_at_frames=tuple(repeated),
            )
        )
        p_events += 1

    if not events:
        return _unchanged_transform(data, units, counts)

    output = bytearray(data[: units[0].start])
    for unit in units:
        output.extend(replacements.get(unit.index, unit.data))
    transformed = bytes(output)
    transformed_units = parse_mpeg4_units(transformed)
    transformed_vops = vop_units(transformed_units)
    if len(transformed_vops) != len(vops):
        raise DatamoshError(
            "DATAMOSHING VOP count changed unexpectedly: "
            f"{len(vops)} input, {len(transformed_vops)} transformed."
        )
    mutated_counts = vop_type_counts(transformed_units)
    if mutated_counts["B"] or mutated_counts["S"]:
        raise DatamoshError("DATAMOSHING transformation introduced an unsupported VOP type.")
    return DatamoshTransform(
        data=transformed,
        events=tuple(sorted(events, key=lambda event: (event.frame, event.operation))),
        original_counts=counts,
        mutated_counts=mutated_counts,
        original_vop_count=len(vops),
        mutated_vop_count=len(transformed_vops),
        input_sha256=_sha256(data),
        output_sha256=_sha256(transformed),
    )


def apply_datamosh(
    silent_video: str | Path,
    output_path: str | Path,
    work_dir: str | Path,
    *,
    fps: int,
    frame_count: int,
    effect_intensity: float,
    weird_seed: int | None,
    eligible_start_frame: int,
    absolute_frame_offset: int,
    loop_friendly: bool,
    video_crf: int,
    video_bitrate: int | None,
    log: LogCallback = None,
) -> DatamoshResult:
    """Run the video-only codec round trip and return a safe silent MP4."""
    source = Path(silent_video)
    destination = Path(output_path)
    temporary = Path(work_dir)
    if not source.is_file():
        raise DatamoshError(f"DATAMOSHING silent visual input is missing: {source}")
    if source.resolve(strict=False) == destination.resolve(strict=False):
        raise DatamoshError("DATAMOSHING refuses to overwrite its silent visual input.")
    if fps <= 0 or frame_count <= 0:
        raise DatamoshError(f"DATAMOSHING received invalid timing: {frame_count} frames at {fps} fps.")
    temporary.mkdir(parents=True, exist_ok=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    controlled_stream = temporary / "controlled_prediction.m4v"
    manipulated_stream = temporary / "manipulated_prediction.m4v"
    gop_size = max(4, min(30, int(round(float(fps)))))

    encode_started = time.perf_counter()
    try:
        _encode_prediction_stream(
            source,
            controlled_stream,
            fps=fps,
            frame_count=frame_count,
            gop_size=gop_size,
            anchor_frame=eligible_start_frame,
            log=log,
        )
    except Exception as exc:  # noqa: BLE001 - convert external codec errors at this boundary.
        raise DatamoshError(f"DATAMOSHING MPEG-4 intermediate encode failed: {exc}") from exc
    encode_seconds = time.perf_counter() - encode_started

    try:
        controlled_data = controlled_stream.read_bytes()
        controlled_vops = vop_units(parse_mpeg4_units(controlled_data))
        if len(controlled_vops) != frame_count:
            raise DatamoshError(
                "DATAMOSHING MPEG-4 intermediate frame count mismatch: "
                f"expected {frame_count}, found {len(controlled_vops)} VOPs."
            )
        transform_started = time.perf_counter()
        transformed = transform_mpeg4_part2(
            controlled_data,
            seed=weird_seed,
            intensity=effect_intensity,
            eligible_start_frame=eligible_start_frame,
            absolute_frame_offset=absolute_frame_offset,
            protect_final_gop=loop_friendly,
        )
        transform_seconds = time.perf_counter() - transform_started
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - isolate parsing/manipulation failures.
        raise DatamoshError(f"DATAMOSHING MPEG-4 VOP manipulation failed: {exc}") from exc

    if not transformed.events:
        _log(
            log,
            "DATAMOSHING: no eligible post-anchor I/P prediction event was available; "
            "leaving the silent visual intermediate unchanged.",
        )
        return DatamoshResult(
            output_path=source,
            applied=False,
            frame_count=frame_count,
            duration=frame_count / fps,
            gop_size=gop_size,
            eligible_start_frame=eligible_start_frame,
            events=(),
            original_counts=transformed.original_counts,
            mutated_counts=transformed.mutated_counts,
            input_stream_size=len(controlled_data),
            manipulated_stream_size=len(controlled_data),
            temporary_disk_bytes=controlled_stream.stat().st_size,
            intermediate_encode_seconds=encode_seconds,
            transform_seconds=transform_seconds,
            safe_transcode_seconds=0.0,
            manipulated_stream_sha256=None,
        )

    try:
        manipulated_stream.write_bytes(transformed.data)
    except OSError as exc:
        raise DatamoshError(f"DATAMOSHING could not write its temporary manipulated stream: {exc}") from exc

    transcode_started = time.perf_counter()
    try:
        _transcode_manipulated_stream(
            manipulated_stream,
            destination,
            fps=fps,
            frame_count=frame_count,
            video_crf=video_crf,
            video_bitrate=video_bitrate,
            log=log,
        )
    except Exception as exc:  # noqa: BLE001 - convert codec failure at the DATAMOSHING boundary.
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        raise DatamoshError(f"DATAMOSHING manipulated-stream H.264 transcode failed: {exc}") from exc
    transcode_seconds = time.perf_counter() - transcode_started

    try:
        duration, decoded_frames = _validate_safe_output(destination, fps=fps, frame_count=frame_count)
    except Exception as exc:  # noqa: BLE001 - do not expose an invalid final-stage video.
        try:
            destination.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, DatamoshError):
            raise
        raise DatamoshError(f"DATAMOSHING safe-output validation failed: {exc}") from exc

    for event in transformed.events:
        if event.operation == "I_RESET_SUPPRESSED_WITH_P":
            _log(
                log,
                f"DATAMOSHING event: absolute frame {event.absolute_frame}, "
                f"I reset suppressed with encoded P frame {absolute_frame_offset + event.source_p_frame}.",
            )
        else:
            _log(
                log,
                f"DATAMOSHING event: absolute frame {event.absolute_frame}, "
                f"encoded P frame {absolute_frame_offset + event.source_p_frame} repeated "
                f"across {len(event.repeated_at_frames)} frame(s).",
            )
    temporary_bytes = sum(
        path.stat().st_size
        for path in (controlled_stream, manipulated_stream, destination)
        if path.exists()
    )
    _log(
        log,
        "DATAMOSHING codec stage: "
        f"{transformed.i_reset_count} I reset(s) suppressed, "
        f"{transformed.p_persistence_count} P persistence event(s), "
        f"{decoded_frames}/{frame_count} frames validated.",
    )
    _log(
        log,
        "DATAMOSHING timing: "
        f"MPEG-4 encode {encode_seconds:.2f}s, VOP transform {transform_seconds:.3f}s, "
        f"safe H.264 transcode {transcode_seconds:.2f}s.",
    )
    return DatamoshResult(
        output_path=destination,
        applied=True,
        frame_count=decoded_frames,
        duration=duration,
        gop_size=gop_size,
        eligible_start_frame=eligible_start_frame,
        events=transformed.events,
        original_counts=transformed.original_counts,
        mutated_counts=transformed.mutated_counts,
        input_stream_size=len(controlled_data),
        manipulated_stream_size=len(transformed.data),
        temporary_disk_bytes=temporary_bytes,
        intermediate_encode_seconds=encode_seconds,
        transform_seconds=transform_seconds,
        safe_transcode_seconds=transcode_seconds,
        manipulated_stream_sha256=transformed.output_sha256,
    )


def _unchanged_transform(
    data: bytes,
    units: tuple[Mpeg4Unit, ...],
    counts: dict[str, int],
) -> DatamoshTransform:
    vop_count = len(vop_units(units))
    digest = _sha256(data)
    return DatamoshTransform(
        data=data,
        events=(),
        original_counts=counts,
        mutated_counts=dict(counts),
        original_vop_count=vop_count,
        mutated_vop_count=vop_count,
        input_sha256=digest,
        output_sha256=digest,
    )


def _stable_score(seed: int | None, category: int, absolute_frame: int) -> int:
    mask = (1 << 64) - 1
    payload = (
        (int(seed or 0) & mask).to_bytes(8, "big")
        + DATAMOSH_SEED_SALT.to_bytes(8, "big")
        + int(category).to_bytes(4, "big")
        + (int(absolute_frame) & mask).to_bytes(8, "big")
    )
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


def _intensity_policy(intensity: float, i_count: int, p_count: int) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, float(intensity) / 2.0))
    i_limit = min(i_count, max(1, int(math.ceil(i_count * (0.05 + 0.75 * amount))))) if i_count else 0
    p_limit = min(p_count, 1 + int(amount * 4.0)) if p_count else 0
    max_repeat = 1 + int(round(amount * 3.0))
    return i_limit, p_limit, max_repeat


def _encode_prediction_stream(
    source: Path,
    destination: Path,
    *,
    fps: int,
    frame_count: int,
    gop_size: int,
    anchor_frame: int,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-c:v",
        "mpeg4",
        "-pix_fmt",
        "yuv420p",
        "-bf",
        "0",
        "-g",
        str(gop_size),
        "-sc_threshold",
        "0",
        "-mpv_flags",
        "+strict_gop",
        "-q:v",
        "3",
        "-threads",
        "1",
        "-frames:v",
        str(frame_count),
        "-r",
        str(fps),
    ]
    if 0 < anchor_frame < frame_count:
        args.extend(["-force_key_frames", f"{anchor_frame / fps:.9f}"])
    args.extend(["-f", "m4v", str(destination)])
    ffmpeg_utils.run_command(args, log)


def _transcode_manipulated_stream(
    source: Path,
    destination: Path,
    *,
    fps: int,
    frame_count: int,
    video_crf: int,
    video_bitrate: int | None,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    args = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "+genpts",
        "-f",
        "m4v",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-frames:v",
        str(frame_count),
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
        args.extend(["-crf", str(max(14, min(40, int(video_crf))))])
    args.extend(
        [
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    ffmpeg_utils.run_command(args, log)


def _validate_safe_output(path: Path, *, fps: int, frame_count: int) -> tuple[float, int]:
    ffprobe_path = ffmpeg_utils.require_binary("ffprobe")
    completed = ffmpeg_utils.run_command(
        [
            ffprobe_path,
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name,pix_fmt,nb_frames,nb_read_frames",
            "-of",
            "json",
            str(path),
        ]
    )
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DatamoshError(f"DATAMOSHING ffprobe returned invalid JSON: {exc}") from exc
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video or video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        raise DatamoshError(f"DATAMOSHING safe output is not H.264/yuv420p: {video}")
    if audio is not None:
        raise DatamoshError("DATAMOSHING safe intermediate unexpectedly contains audio.")
    decoded_frames = int(video.get("nb_read_frames") or video.get("nb_frames") or 0)
    if decoded_frames != frame_count:
        raise DatamoshError(
            f"DATAMOSHING safe output decoded {decoded_frames} frames; expected {frame_count}."
        )
    try:
        duration = float(data.get("format", {}).get("duration", 0.0))
    except (TypeError, ValueError) as exc:
        raise DatamoshError("DATAMOSHING safe output has no valid duration.") from exc
    expected_duration = frame_count / fps
    if abs(duration - expected_duration) > 1.0 / fps + 0.001:
        raise DatamoshError(
            "DATAMOSHING safe output duration drifted beyond one frame: "
            f"{duration:.6f}s vs {expected_duration:.6f}s expected."
        )
    return duration, decoded_frames


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _log(log: LogCallback, message: str) -> None:
    if log:
        log(message)
