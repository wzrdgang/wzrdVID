"""Pure construction of caller-neutral output coverage intervals."""

from __future__ import annotations

import random
from collections.abc import Iterable

import timeline_math


Interval = tuple[float, float]


def build_coverage_intervals(
    duration: float,
    *,
    include_manual: bool,
    manual_intervals: Iterable[Interval],
    include_random: bool,
    random_percent: float,
    random_seed: int | None,
    random_min_length: float,
    random_max_length: float,
) -> tuple[Interval, ...]:
    """Return sorted half-open coverage intervals within one output duration."""
    if duration <= 0:
        return ()

    intervals = list(manual_intervals) if include_manual else []
    intervals = timeline_math.merge_intervals(intervals, duration)

    if include_random:
        clamped_percent = max(0.0, min(100.0, float(random_percent)))
        target_seconds = duration * (clamped_percent / 100.0)
        intervals = _add_random_intervals(
            intervals,
            duration,
            target_seconds,
            min_length=max(0.05, float(random_min_length)),
            max_length=max(float(random_min_length), float(random_max_length)),
            seed=random_seed,
        )

    return tuple(timeline_math.merge_intervals(intervals, duration))


def _add_random_intervals(
    intervals: list[Interval],
    duration: float,
    target_seconds: float,
    *,
    min_length: float,
    max_length: float,
    seed: int | None,
) -> list[Interval]:
    if target_seconds <= 0:
        return intervals

    rng = random.Random(seed)
    result = list(intervals)
    available = _available_gaps(result, duration)
    available_seconds = timeline_math.interval_total(available)
    if available_seconds <= 0:
        return result
    if target_seconds >= available_seconds - 0.02:
        return timeline_math.merge_intervals(result + available, duration)

    random_added = 0.0
    attempts = 0
    while random_added < target_seconds - 0.05 and attempts < 3000:
        attempts += 1
        min_chunk = min(min_length, duration)
        if random_added > 0 and target_seconds - random_added < min_chunk:
            break
        gaps = [
            gap
            for gap in _available_gaps(result, duration)
            if gap[1] - gap[0] >= min_chunk
        ]
        if not gaps:
            break
        gap = _weighted_gap_choice(gaps, rng)
        gap_length = gap[1] - gap[0]
        remaining = target_seconds - random_added
        if remaining < min_chunk:
            chunk_length = min_chunk
        else:
            chunk_max = min(max_length, gap_length, remaining)
            if chunk_max < min_chunk:
                continue
            chunk_length = rng.uniform(min_chunk, chunk_max)
        if chunk_length < min_chunk:
            break
        if gap_length <= chunk_length + 0.02:
            start = gap[0]
        else:
            start = rng.uniform(gap[0], gap[1] - chunk_length)
        candidate = (start, start + chunk_length)
        result = timeline_math.merge_intervals(result + [candidate], duration)
        random_added += chunk_length
    return result


def _weighted_gap_choice(gaps: list[Interval], rng: random.Random) -> Interval:
    total = timeline_math.interval_total(gaps)
    pick = rng.random() * total
    cursor = 0.0
    for gap in gaps:
        cursor += gap[1] - gap[0]
        if pick <= cursor:
            return gap
    return gaps[-1]


def _available_gaps(intervals: list[Interval], duration: float) -> list[Interval]:
    merged = timeline_math.merge_intervals(intervals, duration)
    gaps: list[Interval] = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        gaps.append((cursor, duration))
    return gaps
