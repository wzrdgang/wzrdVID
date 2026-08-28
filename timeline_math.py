"""Pure numeric timeline-window, interval, and frame-quantization helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable


Interval = tuple[float, float]
FrameInterval = tuple[int, int]
_BOUNDARY_EPSILON = 1e-9
_INTERVAL_EPSILON = 0.001


def render_window_duration(
    full_output_duration: float,
    output_time_offset: float,
    preview_duration: float | None,
) -> float:
    """Return the local duration of a full render or bounded Preview window."""
    if preview_duration is None:
        return full_output_duration
    available = full_output_duration - output_time_offset
    if available <= 0.05:
        raise ValueError("Preview start is outside the planned output timeline.")
    return min(float(preview_duration), available)


def absolute_time(local_time_seconds: float, window_start: float) -> float:
    """Map Preview-local time to the canonical full-output clock."""
    return float(window_start) + float(local_time_seconds)


def local_time(absolute_time_seconds: float, window_start: float) -> float:
    """Map canonical full-output time to a Preview-local clock."""
    return float(absolute_time_seconds) - float(window_start)


def intersect_interval(left: Interval, right: Interval) -> Interval | None:
    """Return the half-open intersection of two intervals, if non-empty."""
    start = max(float(left[0]), float(right[0]))
    end = min(float(left[1]), float(right[1]))
    return (start, end) if end > start else None


def rebase_interval(
    interval: Interval,
    window_start: float,
    window_end: float,
) -> Interval | None:
    """Clip an absolute interval to a window and express it in local time."""
    overlap = intersect_interval(
        interval,
        (float(window_start), float(window_end)),
    )
    if overlap is None:
        return None
    return (
        local_time(overlap[0], window_start),
        local_time(overlap[1], window_start),
    )


def rebase_intervals(
    intervals: Iterable[Interval],
    window_start: float,
    window_end: float,
) -> list[Interval]:
    """Return non-empty half-open interval intersections in local time."""
    rebased: list[Interval] = []
    for interval in intervals:
        overlap = rebase_interval(interval, window_start, window_end)
        if overlap is not None:
            rebased.append(overlap)
    return rebased


def merge_intervals(intervals: Iterable[Interval], duration: float) -> list[Interval]:
    """Clamp, discard empty spans, and merge touching time intervals."""
    cleaned: list[Interval] = []
    for start, end in intervals:
        start = max(0.0, min(float(start), duration))
        end = max(0.0, min(float(end), duration))
        if end - start > _INTERVAL_EPSILON:
            cleaned.append((start, end))
    cleaned.sort(key=lambda item: item[0])

    merged: list[Interval] = []
    for start, end in cleaned:
        if not merged or start > merged[-1][1] + _INTERVAL_EPSILON:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def interval_total(intervals: Iterable[Interval]) -> float:
    """Return the non-negative total length of the supplied intervals."""
    return sum(max(0.0, end - start) for start, end in intervals)


def quantize_time_to_frame(time_seconds: float, fps: float) -> int:
    """Map a half-open time boundary to its containing frame boundary."""
    return int(math.ceil(float(time_seconds) * float(fps) - _BOUNDARY_EPSILON))


def absolute_output_frame(
    local_frame: int,
    output_time_offset: float,
    fps: float,
) -> int:
    """Map a local frame index to the canonical full-output frame clock."""
    return max(0, int(round(float(output_time_offset) * float(fps))) + int(local_frame))


def time_intervals_to_frame_intervals(
    intervals: Iterable[Interval],
    fps: float,
    frame_count: int,
) -> tuple[FrameInterval, ...]:
    """Map half-open output-time coverage to the frame indices it contains."""
    mapped: list[FrameInterval] = []
    for start, end in intervals:
        start_frame = max(0, min(frame_count, quantize_time_to_frame(start, fps)))
        end_frame = max(start_frame, min(frame_count, quantize_time_to_frame(end, fps)))
        if end_frame > start_frame:
            mapped.append((start_frame, end_frame))
    return tuple(mapped)


def frames_fully_covered(
    start_frame: int,
    end_frame: int,
    intervals: Iterable[FrameInterval],
) -> bool:
    """Return whether merged or overlapping frame intervals cover the range."""
    cursor = start_frame
    for covered_start, covered_end in intervals:
        if covered_end <= cursor:
            continue
        if covered_start > cursor:
            return False
        cursor = max(cursor, covered_end)
        if cursor >= end_frame:
            return True
    return cursor >= end_frame


def frame_in_intervals(frame: int, intervals: Iterable[FrameInterval]) -> bool:
    """Return whether a frame lies inside any half-open frame interval."""
    return any(start <= frame < end for start, end in intervals)


def ending_tail_duration(full_output_duration: float) -> float:
    """Return the canonical full-output ending/fade duration."""
    return min(1.5, max(0.0, full_output_duration))


def ending_tail_interval(full_output_duration: float) -> Interval | None:
    """Return the canonical full-output ending/fade interval."""
    tail = ending_tail_duration(full_output_duration)
    if tail <= 0.0:
        return None
    return full_output_duration - tail, full_output_duration


def loop_tail_duration(full_output_duration: float) -> float:
    """Return the canonical full-output loop-blend duration."""
    return min(0.75, full_output_duration / 3.0)


def loop_tail_interval(full_output_duration: float) -> Interval | None:
    """Return the canonical full-output loop-blend interval when meaningful."""
    tail = loop_tail_duration(full_output_duration)
    if tail <= 0.05:
        return None
    return full_output_duration - tail, full_output_duration


def loop_protected_tail_start(frame_count: int, fps: int) -> int:
    """Return the first frame protected from codec mutation for loop blending."""
    duration = frame_count / max(1, fps)
    protected_seconds = min(0.75, duration / 3.0)
    protected_frames = max(1, quantize_time_to_frame(protected_seconds, fps))
    return max(0, frame_count - protected_frames)


def preview_loop_protected_tail_start(
    full_output_duration: float,
    absolute_frame_offset: int,
    frame_count: int,
    fps: int,
) -> int:
    """Rebase the canonical loop-protected frame tail into a render window."""
    full_frame_count = max(1, int(math.ceil(full_output_duration * fps)))
    canonical_start = loop_protected_tail_start(full_frame_count, fps)
    return max(0, min(frame_count, canonical_start - absolute_frame_offset))


def preview_fade(
    full_output_duration: float,
    output_time_offset: float,
    render_duration: float,
    fade_duration: float,
) -> tuple[float, float | None]:
    """Return a canonical fade duration and its Preview-local start if visible."""
    if fade_duration <= 0.05:
        return 0.0, None
    local_start = full_output_duration - fade_duration - output_time_offset
    if local_start >= render_duration or local_start + fade_duration <= 0.0:
        return 0.0, None
    return fade_duration, local_start


def style_eligible_start_frame(
    style_begin_time: float,
    output_time_offset: float,
    fps: float,
    frame_count: int,
) -> int:
    """Return the clamped local frame where Style codec effects become eligible."""
    local_style_time = max(0.0, style_begin_time - output_time_offset)
    frame = quantize_time_to_frame(local_style_time, fps)
    return max(0, min(frame_count, frame))
