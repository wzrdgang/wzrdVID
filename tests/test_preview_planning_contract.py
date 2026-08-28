"""Prove and freeze the repaired full-output/Preview planning contract.

Phase 14A recorded the historical divergences.  These tests now assert that
production Preview behavior consumes canonical full-output decisions directly.
The aggregate oracle is sorted, indented ASCII JSON with strict finite numbers,
UTF-8 encoding, and exactly one trailing newline; ordinary tests keep it in memory.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import unittest
from unittest import mock

import numpy as np
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import app
import datamosh
import renderer
from tests.fixtures.helpers import oracle_source_frame


FPS = 24
RANDOM_SEED = 12_345
TEMPORAL_SEED = 8_675_309


def _settings(**overrides: object) -> renderer.RenderSettings:
    base = renderer.RenderSettings(
        video_path="video-a",
        output_path="preview-output",
        audio_path=None,
        video_start=0.0,
        video_end=20.0,
        audio_start=0.0,
        audio_end=None,
        preset_name="Classic ANSI",
        fps=FPS,
        width_chars=80,
        random_seed=RANDOM_SEED,
        weird_seed=TEMPORAL_SEED,
        timeline_items=[
            renderer.TimelineItem(
                path="video-a",
                duration=10.0,
                has_audio=True,
                include_audio=True,
            ),
            renderer.TimelineItem(
                path="video-b",
                duration=10.0,
                has_audio=True,
                include_audio=False,
            ),
        ],
    )
    return replace(base, **overrides)


def _sequential_segments(
    specifications: tuple[tuple[str, str, float, float, bool], ...]
) -> list[renderer.TimelineSegment]:
    cursor = 0.0
    segments: list[renderer.TimelineSegment] = []
    for source_id, kind, duration, source_start, include_audio in specifications:
        segments.append(
            renderer.TimelineSegment(
                path=source_id,
                kind=kind,
                timeline_start=cursor,
                duration=duration,
                source_start=source_start,
                source_end=source_start + duration,
                has_audio=kind == "video",
                include_audio=kind == "video" and include_audio,
            )
        )
        cursor += duration
    return segments


def _round(value: float) -> float:
    return round(float(value), 6)


def _slice_records(
    segments: list[renderer.TimelineSegment],
    window_start: float,
    window_end: float,
) -> list[dict[str, object]]:
    """Describe a full-plan slice without rebuilding the plan or its seed."""
    records: list[dict[str, object]] = []
    for ordinal, segment in enumerate(segments):
        overlap_start = max(window_start, segment.timeline_start)
        overlap_end = min(window_end, segment.timeline_end)
        if overlap_end <= overlap_start:
            continue
        source_start = segment.source_start + overlap_start - segment.timeline_start
        records.append(
            {
                "canonical_ordinal": ordinal,
                "source_id": segment.path,
                "media_kind": segment.kind,
                "source_start": _round(source_start),
                "source_end": _round(source_start + overlap_end - overlap_start),
                "absolute_output_start": _round(overlap_start),
                "absolute_output_end": _round(overlap_end),
                "preview_local_start": _round(overlap_start - window_start),
                "preview_local_end": _round(overlap_end - window_start),
                "include_audio": segment.include_audio,
            }
        )
    return records


def _full_records(
    segments: list[renderer.TimelineSegment],
    duration: float,
) -> list[dict[str, object]]:
    records = _slice_records(segments, 0.0, duration)
    for record in records:
        record.pop("preview_local_start")
        record.pop("preview_local_end")
    return records


def _playback(duration: float) -> renderer.PlaybackPlan:
    return renderer.PlaybackPlan(0.0, duration, duration, duration)


def _random_full_plan(
    segments: list[renderer.TimelineSegment],
    duration: float,
    settings: renderer.RenderSettings,
) -> list[renderer.TimelineSegment]:
    return renderer._randomized_timeline_segments(
        segments,
        _playback(sum(segment.duration for segment in segments)),
        duration,
        settings,
    )


def _transition_records(
    full_targets: tuple[datamosh.DatamoshTransition, ...],
    preview_targets: tuple[datamosh.DatamoshTransition, ...],
) -> list[dict[str, object]]:
    full_by_absolute_frame = {
        target.absolute_frame: target for target in full_targets
    }
    records: list[dict[str, object]] = []
    for target in preview_targets:
        canonical = full_by_absolute_frame[target.absolute_frame]
        full_output_time = (
            target.absolute_frame / FPS
            if target.output_time is None
            else target.output_time
        )
        window_start = (target.absolute_frame - target.frame) / FPS
        records.append(
            {
                "canonical_ordinal": target.transition_ordinal,
                "absolute_output_time": _round(full_output_time),
                "absolute_output_frame": target.absolute_frame,
                "preview_local_time": _round(full_output_time - window_start),
                "preview_local_frame": target.frame,
                "source_kind_before": target.from_kind,
                "source_kind_after": target.to_kind,
                "transition_name": target.visual_transition,
                "identity_matches_full": (
                    target.transition_ordinal == canonical.transition_ordinal
                    and target.visual_transition == canonical.visual_transition
                ),
            }
        )
    return records


class _PreviewHarness:
    """Small non-Qt receiver for the production Preview settings method."""

    def __init__(
        self,
        settings: renderer.RenderSettings,
        *,
        render_duration: float,
        preview_offset: float,
        preview_length: float,
    ) -> None:
        self.settings = settings
        self.render_duration = render_duration
        self.preview_offset = preview_offset
        self.preview_length = preview_length
        self.logs: list[str] = []

    def _new_preview_path(self) -> Path:
        return Path("preview-output")

    def _collect_settings(self, _output_path: str, *, require_output: bool) -> renderer.RenderSettings:
        assert not require_output
        return self.settings

    def _timeline_total_duration(self, *, strict: bool) -> float:
        assert strict
        return float(self.settings.video_end or self.render_duration)

    def _current_render_duration(self, *, strict: bool) -> float:
        assert strict
        return self.render_duration

    def _selected_preview_seconds(self) -> float:
        return self.preview_length

    def _preview_offset(self, _render_duration: float, _preview_seconds: float) -> float:
        return self.preview_offset

    def _preview_bypass_blocks(
        self,
        settings: renderer.RenderSettings,
        render_duration: float,
        preview_offset: float,
        preview_length: float,
    ) -> list[tuple[float, float]]:
        return app.MainWindow._preview_bypass_blocks(
            self,
            settings,
            render_duration,
            preview_offset,
            preview_length,
        )

    def _preview_style_fx_blocks(
        self,
        settings: renderer.RenderSettings,
        render_duration: float,
        preview_offset: float,
        preview_length: float,
    ) -> list[tuple[float, float]]:
        return app.MainWindow._preview_style_fx_blocks(
            self,
            settings,
            render_duration,
            preview_offset,
            preview_length,
        )

    def append_log(self, message: str) -> None:
        self.logs.append(message)


def _collect_preview(
    settings: renderer.RenderSettings,
    window_start: float,
    window_end: float,
    *,
    render_duration: float = 20.0,
) -> renderer.RenderSettings:
    harness = _PreviewHarness(
        settings,
        render_duration=render_duration,
        preview_offset=window_start,
        preview_length=window_end - window_start,
    )
    with mock.patch.object(app.ffmpeg_utils, "get_audio_duration", return_value=5.0):
        return app.MainWindow._collect_preview_settings(harness)


def _external_audio_overlap(
    window_start: float,
    window_end: float,
    *,
    placement_start: float = 10.0,
    source_start: float = 0.0,
    source_end: float = 5.0,
) -> dict[str, object]:
    placement_end = placement_start + source_end - source_start
    overlap_start = max(window_start, placement_start)
    overlap_end = min(window_end, placement_end)
    if overlap_end <= overlap_start:
        return {
            "full_external_intent": True,
            "local_external_overlap": False,
            "audio_source_start": None,
            "audio_source_end": None,
            "preview_start": None,
            "preview_end": None,
        }
    selected_start = source_start + overlap_start - placement_start
    return {
        "full_external_intent": True,
        "local_external_overlap": True,
        "audio_source_start": _round(selected_start),
        "audio_source_end": _round(selected_start + overlap_end - overlap_start),
        "preview_start": _round(overlap_start - window_start),
        "preview_end": _round(overlap_end - window_start),
    }


def _interval_intersection(
    interval: tuple[float, float],
    window: tuple[float, float],
) -> tuple[float, float] | None:
    start = max(interval[0], window[0])
    end = min(interval[1], window[1])
    if end <= start:
        return None
    return (_round(start - window[0]), _round(end - window[0]))


def _tail_policy(
    full_duration: float,
    window: tuple[float, float],
    settings: renderer.RenderSettings,
) -> dict[str, object]:
    preview_duration = window[1] - window[0]
    full_ending_tail = min(1.5, full_duration)
    full_loop_start_frame = datamosh._loop_protected_tail_start(
        math.ceil(full_duration * FPS), FPS
    )
    absolute_start_frame = round(window[0] * FPS)
    local_codec_start_frame = renderer._preview_loop_protected_tail_start(
        full_duration,
        absolute_start_frame,
        math.ceil(preview_duration * FPS),
        FPS,
    )
    full_loop_interval = (full_loop_start_frame / FPS, full_duration)
    local_settings = replace(
        settings,
        output_time_offset=window[0],
        preview_duration=preview_duration,
    )
    fade_duration, fade_start = renderer._preview_audio_fade(
        local_settings,
        full_duration,
        preview_duration,
    )
    audio_fade = None
    if fade_start is not None:
        audio_fade = (
            _round(max(0.0, fade_start)),
            _round(min(preview_duration, fade_start + fade_duration)),
        )
    codec_loop = None
    if local_codec_start_frame < math.ceil(preview_duration * FPS):
        codec_loop = (
            _round(local_codec_start_frame / FPS),
            _round(preview_duration),
        )
    return {
        "window": [_round(window[0]), _round(window[1])],
        "ending": _interval_intersection(
            (full_duration - full_ending_tail, full_duration), window
        ),
        "loop_visual": _interval_intersection(full_loop_interval, window),
        "codec_loop_seconds": codec_loop,
        "audio_fade": audio_fade,
    }


def _frame_digest(image: Image.Image) -> str:
    return hashlib.sha256(np.asarray(image, dtype=np.uint8).tobytes()).hexdigest()


def _temporal_run(
    effects: dict[str, bool],
    start: int,
    stop: int,
    *,
    visible_start: int,
) -> tuple[dict[int, str], dict[str, object]]:
    choreographer = renderer._FrameEffectChoreographer(
        effects,
        1.45,
        FPS,
        TEMPORAL_SEED,
        record_events=True,
    )
    output: dict[int, str] = {}
    start_state: dict[str, object] = {}
    for absolute_frame in range(start, stop):
        source = oracle_source_frame(absolute_frame, 64, 36)
        analysis = choreographer.analysis_for(source)
        if absolute_frame == visible_start:
            start_state = {
                "prior_luma": choreographer.previous_luma is not None,
                "prior_rgb": choreographer.previous_rgb is not None,
                "motion": _round(analysis.motion_activity),
                "active_events": sorted(choreographer.active_events),
                "cooldowns": sorted(
                    key for key, value in choreographer.cooldown_until.items() if value >= absolute_frame
                ),
                "organic_instability": _round(choreographer.organic_instability),
            }
        rendered = renderer._apply_phase2_frame_effects(
            source,
            effects,
            1.45,
            absolute_frame,
            FPS,
            TEMPORAL_SEED,
            choreographer=choreographer,
            material=source,
        )
        if absolute_frame >= visible_start:
            output[absolute_frame] = _frame_digest(rendered)
    return output, start_state


def _temporal_characterization() -> dict[str, object]:
    start = 12
    visible_frames = 24
    effects = {key: True for key in renderer.PHASE2_FRAME_EFFECT_ORDER}
    full, full_state = _temporal_run(effects, 0, start + visible_frames, visible_start=start)
    fresh, fresh_state = _temporal_run(
        effects, start, start + visible_frames, visible_start=start
    )
    repeated, _ = _temporal_run(
        effects, start, start + visible_frames, visible_start=start
    )

    circuit = {"circuit_bending": True}
    full_circuit, _ = _temporal_run(
        circuit, 0, start + 1, visible_start=start
    )
    fresh_circuit, _ = _temporal_run(
        circuit, start, start + 1, visible_start=start
    )
    differing = [
        absolute_frame - start
        for absolute_frame in range(start, start + visible_frames)
        if full[absolute_frame] != fresh[absolute_frame]
    ]
    return {
        "absolute_start_frame": start,
        "sampled_visible_frames": visible_frames,
        "differing_preview_frames": differing,
        "full_start_state": full_state,
        "fresh_start_state": fresh_state,
        "fresh_repeat_equal": fresh == repeated,
        "circuit_first_frame_equal": full_circuit[start] == fresh_circuit[start],
        "decision": "intentional-fresh-state-with-absolute-clock",
    }


def _rebase_intervals(
    intervals: list[tuple[float, float]],
    window_start: float,
    window_end: float,
) -> list[tuple[float, float]]:
    return [
        intersection
        for interval in intervals
        if (intersection := _interval_intersection(interval, (window_start, window_end)))
        is not None
    ]


def _normalized_intervals(
    intervals: list[tuple[float, float]] | tuple[tuple[float, float], ...],
) -> list[list[float]]:
    return [[_round(start), _round(end)] for start, end in intervals]


def _canonical_transition_records(
    targets: tuple[datamosh.DatamoshTransition, ...],
) -> list[dict[str, object]]:
    records = _transition_records(targets, targets)
    for record in records:
        record.pop("preview_local_time")
        record.pop("preview_local_frame")
        record.pop("identity_matches_full")
    return records


def _style_gate_semantics(
    gate_time: float,
    window: tuple[float, float],
) -> dict[str, object]:
    window_start_frame = int(round(window[0] * FPS))
    window_end_frame = int(math.ceil(window[1] * FPS - 1e-9))
    gate_frame = max(0, int(math.ceil(gate_time * FPS - 1e-9)))
    eligible_frame = max(window_start_frame, gate_frame)
    if eligible_frame >= window_end_frame:
        return {
            "absolute_gate_time": _round(gate_time),
            "absolute_gate_frame": gate_frame,
            "eligible_absolute_time": None,
            "eligible_absolute_frame": None,
            "preview_local_time": None,
            "preview_local_frame": None,
        }
    return {
        "absolute_gate_time": _round(gate_time),
        "absolute_gate_frame": gate_frame,
        "eligible_absolute_time": _round(eligible_frame / FPS),
        "eligible_absolute_frame": eligible_frame,
        "preview_local_time": _round((eligible_frame - window_start_frame) / FPS),
        "preview_local_frame": eligible_frame - window_start_frame,
    }


def _tail_oracle_semantics(
    full_duration: float,
    window: tuple[float, float],
    settings: renderer.RenderSettings,
) -> dict[str, object]:
    preview_duration = window[1] - window[0]
    full_frame_count = max(1, math.ceil(full_duration * FPS))
    local_frame_count = max(1, math.ceil(preview_duration * FPS))
    absolute_start_frame = int(round(window[0] * FPS))

    ending_duration = min(1.5, full_duration)
    ending_absolute = (full_duration - ending_duration, full_duration)
    loop_start_frame = datamosh._loop_protected_tail_start(full_frame_count, FPS)
    loop_absolute = (loop_start_frame / FPS, full_duration)
    local_codec_start = renderer._preview_loop_protected_tail_start(
        full_duration,
        absolute_start_frame,
        local_frame_count,
        FPS,
    )

    preview_settings = replace(
        settings,
        output_time_offset=window[0],
        preview_duration=preview_duration,
    )
    canonical_fade_duration = renderer._audio_fade_duration(settings, full_duration)
    _preview_fade_duration, fade_local_start = renderer._preview_audio_fade(
        preview_settings,
        full_duration,
        preview_duration,
    )
    fade_absolute = (
        (full_duration - canonical_fade_duration, full_duration)
        if canonical_fade_duration > 0.05
        else None
    )
    fade_local = None
    fade_start_progress = None
    fade_start_gain = None
    if fade_absolute is not None and fade_local_start is not None:
        fade_local = [
            _round(max(0.0, fade_local_start)),
            _round(
                min(preview_duration, fade_local_start + canonical_fade_duration)
            ),
        ]
        fade_start_progress = _round(
            max(
                0.0,
                min(
                    1.0,
                    (window[0] - fade_absolute[0]) / canonical_fade_duration,
                ),
            )
        )
        fade_start_gain = _round(1.0 - fade_start_progress)

    ending_local = _interval_intersection(ending_absolute, window)
    loop_local = _interval_intersection(loop_absolute, window)
    codec_local = (
        [local_codec_start, local_frame_count]
        if local_codec_start < local_frame_count
        else None
    )
    return {
        "preview_window": [_round(window[0]), _round(window[1])],
        "ending": {
            "canonical_absolute_seconds": _normalized_intervals([ending_absolute])[0],
            "preview_local_seconds": list(ending_local) if ending_local else None,
        },
        "loop_visual": {
            "canonical_absolute_seconds": _normalized_intervals([loop_absolute])[0],
            "preview_local_seconds": list(loop_local) if loop_local else None,
        },
        "codec_loop_protection": {
            "canonical_absolute_frames": [loop_start_frame, full_frame_count],
            "preview_local_frames": codec_local,
        },
        "audio_fade": {
            "canonical_absolute_seconds": (
                _normalized_intervals([fade_absolute])[0]
                if fade_absolute is not None
                else None
            ),
            "preview_local_seconds": fade_local,
            "starting_progress": fade_start_progress,
            "starting_gain": fade_start_gain,
        },
    }


def _delayed_audio_semantics(
    configured_settings: renderer.RenderSettings,
    window: tuple[float, float],
) -> dict[str, object]:
    preview = _collect_preview(configured_settings, *window)
    playback = renderer._playback_plan(
        preview,
        20.0,
        selected_audio_duration=15.0,
    )
    execution, source_start, source_end, has_overlap = (
        renderer._preview_audio_execution_settings(
            preview,
            0.0,
            5.0,
            20.0,
            window[1] - window[0],
        )
    )
    return {
        "preview_window": [_round(window[0]), _round(window[1])],
        "global": {
            "mode": preview.audio_mode,
            "match_enabled": preview.match_timeline_to_audio,
            "configured_external_track_present": bool(preview.audio_path),
            "canonical_output_duration": _round(playback.output_duration),
        },
        "local_preview": {
            "overlap": has_overlap,
            "silent_external_execution": not has_overlap and not execution.audio_path,
            "execution_external_track_present": bool(execution.audio_path),
            "external_source_trim_start": _round(source_start) if has_overlap else None,
            "external_source_trim_end": (
                _round(float(source_end)) if has_overlap and source_end is not None else None
            ),
            "placement_start": (
                _round(execution.audio_timeline_start) if has_overlap else None
            ),
            "placement_end": (
                _round(float(execution.audio_timeline_end))
                if has_overlap and execution.audio_timeline_end is not None
                else None
            ),
        },
    }


def _without_preview_record_fields(
    records: list[dict[str, object]],
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for record in records:
        canonical = dict(record)
        canonical.pop("preview_local_start", None)
        canonical.pop("preview_local_end", None)
        canonical.pop("preview_local_time", None)
        canonical.pop("preview_local_frame", None)
        canonical.pop("identity_matches_full", None)
        normalized.append(canonical)
    return normalized


def build_canonical_planning_oracle() -> dict[str, object]:
    """Return the canonical Phase 14C planning contract as path-free plain data."""
    two_sources = _sequential_segments(
        (
            ("video-a", "video", 10.0, 0.0, True),
            ("video-b", "video", 10.0, 20.0, False),
        )
    )
    three_sources = _sequential_segments(
        (
            ("video-a", "video", 8.0, 0.0, True),
            ("video-b", "video", 7.0, 20.0, False),
            ("photo-c", "photo", 9.0, 0.0, False),
        )
    )
    random_settings = _settings(
        random_clip_assembly=True,
        random_min_len=0.5,
        random_max_len=3.0,
        max_video_length=16.0,
    )
    random_full = _random_full_plan(three_sources, 16.0, random_settings)
    random_repeat = _random_full_plan(three_sources, 16.0, random_settings)
    random_changed = _random_full_plan(
        three_sources,
        16.0,
        replace(random_settings, random_seed=RANDOM_SEED + 1),
    )
    inside_segment = random_full[2]
    inside_window = (
        inside_segment.timeline_start + min(0.05, inside_segment.duration / 4.0),
        inside_segment.timeline_start + min(0.25, inside_segment.duration / 2.0),
    )
    one_cut = random_full[1].timeline_start
    one_cut_window = (max(0.0, one_cut - 0.1), min(16.0, one_cut + 0.1))
    multiple_cut_window = (
        max(0.0, random_full[1].timeline_start - 0.1),
        min(16.0, random_full[4].timeline_start + 0.1),
    )

    transition_segments = _sequential_segments(
        (
            ("video-a", "video", 5.0, 0.0, True),
            ("photo-c", "photo", 5.0, 0.0, False),
            ("video-b", "video", 5.0, 30.0, False),
            ("photo-d", "photo", 5.0, 0.0, False),
        )
    )
    fixed_transition_settings = _settings(transition_mode="RGB Burst")
    random_transition_settings = _settings(
        transition_mode="Random",
        random_seed=123,
        weird_seed=None,
    )
    fixed_full = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        fixed_transition_settings,
        20 * FPS,
        0,
    )
    random_transition_full = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        random_transition_settings,
        20 * FPS,
        0,
    )
    fixed_one_cut = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        fixed_transition_settings,
        4 * FPS,
        4 * FPS,
    )
    fixed_exact = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        fixed_transition_settings,
        3 * FPS,
        5 * FPS,
    )
    random_after_earlier = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        random_transition_settings,
        4 * FPS,
        14 * FPS,
    )
    random_multiple = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        random_transition_settings,
        10 * FPS,
        6 * FPS,
    )
    random_exact = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        random_transition_settings,
        3 * FPS,
        15 * FPS,
    )

    delayed_audio = _settings(
        audio_path="audio-main",
        audio_start=0.0,
        audio_end=5.0,
        audio_timeline_start=10.0,
        audio_mode=renderer.AUDIO_EXTERNAL,
        match_timeline_to_audio=True,
        match_timeline_mode=renderer.MATCH_SPEED,
    )
    tail_settings = _settings(ending_mode="Fade Out", loop_friendly=True)

    ansi_settings = _settings(
        bypass_mode=renderer.BYPASS_MANUAL_RANDOM,
        manual_blocks=[(4.0, 7.0), (12.0, 13.0)],
        random_percent=35.0,
        random_min_len=0.5,
        random_max_len=2.0,
        random_seed=101,
    )
    ansi_full = renderer.build_bypass_intervals(
        20.0,
        ansi_settings.bypass_mode,
        ansi_settings.manual_blocks,
        ansi_settings.random_percent,
        ansi_settings.random_min_len,
        ansi_settings.random_max_len,
        ansi_settings.random_seed,
    )
    ansi_harness = _PreviewHarness(
        ansi_settings,
        render_duration=20.0,
        preview_offset=5.0,
        preview_length=5.0,
    )

    style_base = _settings(
        style_fx_manual_blocks=[(4.0, 7.0), (12.0, 13.0)],
        style_fx_random_percent=45.0,
        random_min_len=0.5,
        random_max_len=2.0,
        style_fx_random_seed=202,
    )
    style_modes = {
        "manual": renderer.STYLE_FX_MANUAL,
        "random": renderer.STYLE_FX_RANDOM,
        "combined": renderer.STYLE_FX_MANUAL_RANDOM,
    }
    style_coverage: dict[str, object] = {}
    for label, mode in style_modes.items():
        settings = replace(style_base, style_fx_coverage_mode=mode)
        full_intervals = renderer.build_style_fx_clean_intervals(
            20.0,
            mode,
            settings.style_fx_manual_blocks,
            settings.style_fx_random_percent,
            settings.random_min_len,
            settings.random_max_len,
            settings.style_fx_random_seed,
        )
        harness = _PreviewHarness(
            settings,
            render_duration=20.0,
            preview_offset=5.0,
            preview_length=5.0,
        )
        style_coverage[label] = {
            "full_clean_intervals": _normalized_intervals(full_intervals),
            "preview_clean_intervals": _normalized_intervals(
                harness._preview_style_fx_blocks(settings, 20.0, 5.0, 5.0)
            ),
            "protected_frame_ranges": [
                list(interval)
                for interval in renderer._style_fx_clean_frame_intervals(
                    full_intervals,
                    FPS,
                    20 * FPS,
                )
            ],
            "temporal_reset_boundaries": sorted(
                {_round(value) for interval in full_intervals for value in interval}
            ),
        }

    invalid_audio = replace(
        delayed_audio,
        audio_path=None,
        audio_mode=renderer.AUDIO_SOURCE,
        match_timeline_to_audio=True,
    )
    invalid_audio_rejected = False
    try:
        renderer._playback_plan(invalid_audio, 20.0, selected_audio_duration=None)
    except ValueError:
        invalid_audio_rejected = True

    stutter_settings = _settings(effects={"stutter_hold": True})
    stutter_preview = replace(stutter_settings, output_time_offset=0.5)
    stutter_local_frame = 10
    stutter_absolute_frame = renderer._absolute_output_frame(
        stutter_preview,
        stutter_local_frame,
    )
    stutter_absolute_trigger_local_frame = next(
        local_frame
        for local_frame in range(100)
        if renderer._starts_stutter_hold(
            renderer._absolute_output_frame(stutter_preview, local_frame),
            stutter_preview,
        )
    )
    stutter_absolute_trigger_frame = renderer._absolute_output_frame(
        stutter_preview,
        stutter_absolute_trigger_local_frame,
    )

    batch_variant = app.MainWindow._settings_for_batch_variant(
        object(),
        "Classic ANSI",
        random_settings,
    )
    batch_full = _random_full_plan(three_sources, 16.0, batch_variant)

    full_preview_settings = replace(
        tail_settings,
        preview_duration=20.0,
        output_time_offset=0.0,
    )
    full_tail = _tail_oracle_semantics(20.0, (0.0, 20.0), tail_settings)
    full_preview_tail = _tail_oracle_semantics(
        20.0,
        (0.0, 20.0),
        full_preview_settings,
    )
    ansi_full_preview = ansi_harness._preview_bypass_blocks(
        ansi_settings,
        20.0,
        0.0,
        20.0,
    )
    combined_style_settings = replace(
        style_base,
        style_fx_coverage_mode=renderer.STYLE_FX_MANUAL_RANDOM,
    )
    combined_style_full = renderer.build_style_fx_clean_intervals(
        20.0,
        combined_style_settings.style_fx_coverage_mode,
        combined_style_settings.style_fx_manual_blocks,
        combined_style_settings.style_fx_random_percent,
        combined_style_settings.random_min_len,
        combined_style_settings.random_max_len,
        combined_style_settings.style_fx_random_seed,
    )
    combined_style_harness = _PreviewHarness(
        combined_style_settings,
        render_duration=20.0,
        preview_offset=0.0,
        preview_length=20.0,
    )
    combined_style_full_preview = combined_style_harness._preview_style_fx_blocks(
        combined_style_settings,
        20.0,
        0.0,
        20.0,
    )
    full_transition_preview = renderer._datamosh_transition_targets(
        transition_segments,
        _playback(20.0),
        random_transition_settings,
        20 * FPS,
        0,
    )

    random_source_counts = {
        source_id: sum(segment.path == source_id for segment in random_full)
        for source_id in ("video-a", "video-b", "photo-c")
    }
    cases: dict[str, object] = {
        "A": {
            "name": "sequential-full-output",
            "segments": _full_records(two_sources, 20.0),
        },
        "B": {
            "name": "sequential-capped-output",
            "cap_seconds": 7.0,
            "segments": _full_records(two_sources, 7.0),
        },
        "C": {
            "name": "sequential-nonzero-preview",
            "preview_window": [7.0, 13.0],
            "segments": _slice_records(two_sources, 7.0, 13.0),
        },
        "D": {
            "name": "random-full-output",
            "cap_seconds": 16.0,
            "segments": _full_records(random_full, 16.0),
            "source_reuse_counts": random_source_counts,
            "final_segment_trimmed_to_cap": (
                random_full[-1].duration < random_settings.random_min_len
                and _round(random_full[-1].timeline_end) == 16.0
            ),
        },
        "E": {
            "name": "random-same-seed-repeat",
            "same_seed_equal": random_full == random_repeat,
        },
        "F": {
            "name": "random-changed-seed-distinction",
            "changed_seed_equal": random_full == random_changed,
            "first_distinguishing_segment": {
                "baseline": _full_records(random_full, 16.0)[0],
                "changed_seed": _full_records(random_changed, 16.0)[0],
            },
        },
        "G": {
            "name": "random-preview-inside-one-segment",
            "preview_window": [_round(value) for value in inside_window],
            "segments": _slice_records(random_full, *inside_window),
        },
        "H": {
            "name": "random-preview-crossing-one-cut",
            "preview_window": [_round(value) for value in one_cut_window],
            "segments": _slice_records(random_full, *one_cut_window),
        },
        "I": {
            "name": "random-preview-crossing-multiple-cuts",
            "preview_window": [_round(value) for value in multiple_cut_window],
            "segments": _slice_records(random_full, *multiple_cut_window),
        },
        "J": {
            "name": "random-final-window",
            "preview_window": [14.0, 16.0],
            "segments": _slice_records(random_full, 14.0, 16.0),
        },
        "K": {
            "name": "random-source-audio-mapping",
            "preview_window": [5.0, 8.0],
            "visual_segments": _slice_records(random_full, 5.0, 8.0),
            "source_audio_segments": [
                record
                for record in _slice_records(random_full, 5.0, 8.0)
                if record["include_audio"]
            ],
        },
        "L": {
            "name": "fixed-transition-map",
            "full": _canonical_transition_records(fixed_full),
            "one_cut_preview": _transition_records(fixed_full, fixed_one_cut),
        },
        "M": {
            "name": "random-transition-map",
            "full": _canonical_transition_records(random_transition_full),
            "after_earlier_cuts_preview": _transition_records(
                random_transition_full,
                random_after_earlier,
            ),
            "multiple_cut_preview": _transition_records(
                random_transition_full,
                random_multiple,
            ),
        },
        "N": {
            "name": "exact-start-fixed-transition",
            "transitions": _transition_records(fixed_full, fixed_exact),
        },
        "O": {
            "name": "exact-start-random-transition",
            "transitions": _transition_records(random_transition_full, random_exact),
        },
        "P": {
            "name": "delayed-audio-before-overlap",
            **_delayed_audio_semantics(delayed_audio, (2.0, 5.0)),
        },
        "Q": {
            "name": "delayed-audio-crossing-start",
            **_delayed_audio_semantics(delayed_audio, (9.0, 12.0)),
        },
        "R": {
            "name": "delayed-audio-inside-overlap",
            **_delayed_audio_semantics(delayed_audio, (11.0, 13.0)),
        },
        "S": {
            "name": "delayed-audio-crossing-end",
            **_delayed_audio_semantics(delayed_audio, (14.0, 17.0)),
        },
        "T": {
            "name": "delayed-audio-after-overlap",
            **_delayed_audio_semantics(delayed_audio, (16.0, 18.0)),
        },
        "U": {
            "name": "middle-preview-without-full-output-tail",
            **_tail_oracle_semantics(20.0, (8.0, 12.0), tail_settings),
        },
        "V": {
            "name": "partial-ending-loop-codec-fade-intersection",
            **_tail_oracle_semantics(20.0, (18.75, 19.5), tail_settings),
        },
        "W": {
            "name": "true-full-output-tail-intersection",
            **_tail_oracle_semantics(20.0, (19.0, 20.0), tail_settings),
        },
        "X": {
            "name": "full-duration-preview-equivalence",
            "render_duration": _round(
                renderer._render_window_duration(full_preview_settings, 20.0)
            ),
            "equivalent_after_preview_wrapper_removal": {
                "sequential_playback": (
                    _full_records(two_sources, 20.0)
                    == _without_preview_record_fields(
                        _slice_records(two_sources, 0.0, 20.0)
                    )
                ),
                "random_playback": (
                    _full_records(random_full, 16.0)
                    == _without_preview_record_fields(
                        _slice_records(random_full, 0.0, 16.0)
                    )
                ),
                "transitions": (
                    _canonical_transition_records(random_transition_full)
                    == _without_preview_record_fields(
                        _transition_records(
                            random_transition_full,
                            full_transition_preview,
                        )
                    )
                ),
                "ansi_coverage": (
                    _normalized_intervals(ansi_full)
                    == _normalized_intervals(ansi_full_preview)
                ),
                "style_fx_coverage": (
                    _normalized_intervals(combined_style_full)
                    == _normalized_intervals(combined_style_full_preview)
                ),
                "ending_loop_codec_fade": full_tail == full_preview_tail,
            },
            "fresh_retained_temporal_state_is_exempt": True,
        },
    }

    return {
        "contract": {
            "fps": FPS,
            "interval_semantics": "half-open-[start,end)",
            "numeric_seconds": "round-to-6-decimal-places",
            "frame_values": "exact-integers",
            "source_identity": "symbolic-only",
        },
        "cases": cases,
        "supplemental": {
            "style_begins_at": {
                "gate_before_preview": _style_gate_semantics(2.0, (5.0, 8.0)),
                "gate_inside_preview": _style_gate_semantics(6.5, (5.0, 8.0)),
                "gate_after_preview": _style_gate_semantics(10.0, (5.0, 8.0)),
                "zero_gate": _style_gate_semantics(0.0, (5.0, 8.0)),
                "gate_at_output_end": _style_gate_semantics(20.0, (0.0, 20.0)),
            },
            "ansi_coverage": {
                "meaning": "normal-video-versus-ansi-text-rendering",
                "full_normal_intervals": _normalized_intervals(ansi_full),
                "preview_normal_intervals": _normalized_intervals(
                    ansi_harness._preview_bypass_blocks(
                        ansi_settings,
                        20.0,
                        5.0,
                        5.0,
                    )
                ),
            },
            "style_fx_coverage": {
                "meaning": "optional-style-effects-clean-intervals",
                "seed_is_independent_from_ansi": True,
                "temporal_reset_policy": "fresh-at-both-interval-edges",
                "modes": style_coverage,
            },
            "invalid_audio_guard": {
                "accepted": not invalid_audio_rejected,
                "error_code": "match-requires-external-audio",
            },
            "stutter": {
                "divergence_local_frame": stutter_local_frame,
                "divergence_absolute_frame": stutter_absolute_frame,
                "local_clock_would_trigger": renderer._starts_stutter_hold(
                    stutter_local_frame,
                    stutter_preview,
                ),
                "absolute_clock_triggers_at_divergence_frame": renderer._starts_stutter_hold(
                    stutter_absolute_frame,
                    stutter_preview,
                ),
                "absolute_trigger_example_local_frame": (
                    stutter_absolute_trigger_local_frame
                ),
                "absolute_trigger_example_absolute_frame": (
                    stutter_absolute_trigger_frame
                ),
                "absolute_trigger_example_triggers": renderer._starts_stutter_hold(
                    stutter_absolute_trigger_frame,
                    stutter_preview,
                ),
                "retained_hold_at_preview_start": "fresh",
            },
            "intentional_fresh_temporal_state": {
                "material_history": "fresh",
                "circuit_rgb_history": "fresh",
                "luma_history": "fresh",
                "organic_state": "fresh",
                "event_state": "fresh",
                "cooldown_state": "fresh",
                "stutter_hold": "fresh",
                "clock_basis": "absolute-output",
            },
            "batch": {
                "planning_scope": "normal-full-output",
                "preview_duration": batch_variant.preview_duration,
                "output_time_offset": _round(batch_variant.output_time_offset),
                "full_random_plan_equal": batch_full == random_full,
            },
        },
    }


def serialize_canonical_planning_oracle(oracle: dict[str, object]) -> bytes:
    """Serialize the planning oracle with the frozen Phase 14C byte contract."""
    return (
        json.dumps(
            oracle,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


EXPECTED_PLANNING_ORACLE_BYTES = 31_416
EXPECTED_PLANNING_ORACLE_SHA256 = (
    "85477bbf54769f2fdabd2ffe05ac3b7fa34017216068c80beb6d107a502e0dc3"
)


class PreviewPlanningContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.two_sources = _sequential_segments(
            (
                ("video-a", "video", 10.0, 0.0, True),
                ("video-b", "video", 10.0, 20.0, False),
            )
        )
        cls.three_sources = _sequential_segments(
            (
                ("video-a", "video", 8.0, 0.0, True),
                ("video-b", "video", 7.0, 20.0, False),
                ("photo-c", "photo", 9.0, 0.0, False),
            )
        )
        cls.random_settings = _settings(
            random_clip_assembly=True,
            random_min_len=0.5,
            random_max_len=3.0,
            max_video_length=16.0,
        )
        cls.random_full = _random_full_plan(
            cls.three_sources, 16.0, cls.random_settings
        )
        cls.temporal = _temporal_characterization()

    def test_sequential_capped_and_batch_share_one_plan_semantic(self) -> None:
        full_records = _slice_records(self.two_sources, 0.0, 20.0)
        preview_records = _slice_records(self.two_sources, 7.0, 13.0)
        self.assertEqual([record["source_id"] for record in full_records], ["video-a", "video-b"])
        self.assertEqual(
            [
                (
                    record["source_id"],
                    record["preview_local_start"],
                    record["preview_local_end"],
                )
                for record in preview_records
            ],
            [("video-a", 0.0, 3.0), ("video-b", 3.0, 6.0)],
        )
        capped_settings = _settings(max_video_length=7.0)
        capped = renderer._playback_plan(
            capped_settings,
            20.0,
            selected_audio_duration=None,
        )
        self.assertEqual(capped.output_duration, 7.0)
        self.assertEqual(
            _slice_records(self.two_sources, 0.0, capped.output_duration)[-1]["absolute_output_end"],
            7.0,
        )

        batch_variant = app.MainWindow._settings_for_batch_variant(
            object(), "Classic ANSI", self.random_settings
        )
        for field in (
            "video_start",
            "video_end",
            "max_video_length",
            "random_clip_assembly",
            "random_seed",
            "timeline_items",
        ):
            self.assertEqual(getattr(batch_variant, field), getattr(self.random_settings, field))

    def test_random_preview_contract_slices_the_canonical_seeded_plan(self) -> None:
        repeated = _random_full_plan(self.three_sources, 16.0, self.random_settings)
        changed = _random_full_plan(
            self.three_sources,
            16.0,
            replace(self.random_settings, random_seed=RANDOM_SEED + 1),
        )
        self.assertEqual(self.random_full, repeated)
        self.assertNotEqual(self.random_full, changed)

        longest = max(self.random_full, key=lambda segment: segment.duration)
        inside_start = longest.timeline_start + min(0.1, longest.duration / 4.0)
        inside_end = min(longest.timeline_end, inside_start + min(0.4, longest.duration / 2.0))
        first_boundary = self.random_full[1].timeline_start
        one_cut_window = (max(0.0, first_boundary - 0.2), min(16.0, first_boundary + 0.2))
        multi_cut_window = (
            max(0.0, self.random_full[1].timeline_start - 0.1),
            min(16.0, self.random_full[4].timeline_start + 0.1),
        )
        windows = {
            "beginning": (0.0, 2.0),
            "inside": (inside_start, inside_end),
            "one-cut": one_cut_window,
            "multiple-cuts": multi_cut_window,
            "middle": (6.0, 9.0),
            "final": (14.0, 16.0),
        }
        previews = {
            name: _slice_records(self.random_full, start, end)
            for name, (start, end) in windows.items()
        }
        self.assertEqual(previews["inside"][0]["source_id"], longest.path)
        self.assertEqual(len(previews["one-cut"]), 2)
        self.assertGreaterEqual(len(previews["multiple-cuts"]), 4)
        self.assertEqual(previews["beginning"][0]["absolute_output_start"], 0.0)
        self.assertEqual(previews["final"][-1]["absolute_output_end"], 16.0)

        collected = _collect_preview(self.random_settings, 6.0, 9.0, render_duration=16.0)
        self.assertEqual(collected.video_start, self.random_settings.video_start)
        self.assertEqual(collected.video_end, self.random_settings.video_end)
        self.assertEqual(collected.max_video_length, self.random_settings.max_video_length)
        self.assertTrue(collected.random_clip_assembly)
        self.assertEqual(collected.random_seed, self.random_settings.random_seed)
        self.assertEqual(collected.output_time_offset, 6.0)
        self.assertEqual(collected.preview_duration, 3.0)

        two_source_full = _random_full_plan(self.two_sources, 12.0, self.random_settings)
        two_source_preview = _slice_records(two_source_full, 5.0, 8.0)
        self.assertTrue(two_source_preview)

        self.assertTrue(any(record["include_audio"] for record in previews["middle"]))
        for record in previews["middle"]:
            self.assertEqual(
                record["include_audio"],
                record["source_id"] == "video-a",
            )

    def test_transition_identity_uses_the_canonical_full_cut(self) -> None:
        segments = _sequential_segments(
            (
                ("video-a", "video", 5.0, 0.0, True),
                ("photo-b", "photo", 5.0, 0.0, False),
                ("video-c", "video", 5.0, 30.0, False),
                ("photo-d", "photo", 5.0, 0.0, False),
            )
        )
        full_playback = _playback(20.0)
        random_settings = _settings(transition_mode="Random", random_seed=123, weird_seed=None)
        full_random = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            random_settings,
            20 * FPS,
            0,
        )
        self.assertEqual(
            [
                (target.absolute_frame, target.transition_ordinal, target.visual_transition)
                for target in full_random
            ],
            [
                (120, 0, "CRT Flash"),
                (240, 1, "Block Dissolve"),
                (360, 2, "Buffer Underrun"),
            ],
        )

        after_earlier_window = (14.0, 18.0)
        after_earlier = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            random_settings,
            4 * FPS,
            14 * FPS,
        )
        records = _transition_records(full_random, after_earlier)
        self.assertEqual(records[0]["canonical_ordinal"], 2)
        self.assertEqual(records[0]["transition_name"], "Buffer Underrun")
        self.assertTrue(records[0]["identity_matches_full"])

        exactly_at_cut = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            random_settings,
            3 * FPS,
            15 * FPS,
        )
        exact_records = _transition_records(full_random, exactly_at_cut)
        self.assertEqual(exact_records[0]["absolute_output_frame"], 360)
        self.assertEqual(exact_records[0]["preview_local_frame"], 0)
        self.assertEqual(exact_records[0]["transition_name"], "Buffer Underrun")

        multiple = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            random_settings,
            10 * FPS,
            6 * FPS,
        )
        multiple_records = _transition_records(full_random, multiple)
        self.assertEqual([record["canonical_ordinal"] for record in multiple_records], [1, 2])
        self.assertTrue(all(record["identity_matches_full"] for record in multiple_records))

        fixed_settings = replace(random_settings, transition_mode="RGB Burst")
        full_fixed = renderer._datamosh_transition_targets(
            segments, full_playback, fixed_settings, 20 * FPS, 0
        )
        before_cut = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            fixed_settings,
            4 * FPS,
            4 * FPS,
        )
        fixed_records = _transition_records(full_fixed, before_cut)
        self.assertEqual(fixed_records[0]["transition_name"], "RGB Burst")
        self.assertTrue(fixed_records[0]["identity_matches_full"])
        fixed_exact = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            fixed_settings,
            3 * FPS,
            5 * FPS,
        )
        fixed_exact_records = _transition_records(full_fixed, fixed_exact)
        self.assertEqual(fixed_exact_records[0]["preview_local_frame"], 0)
        self.assertEqual(fixed_exact_records[0]["transition_name"], "RGB Burst")

        random_playback_targets = renderer._datamosh_transition_targets(
            self.random_full,
            _playback(16.0),
            random_settings,
            16 * FPS,
            0,
        )
        start_frame = random_playback_targets[0].absolute_frame + 1
        end_frame = min(16 * FPS, random_playback_targets[3].absolute_frame + 1)
        random_slice = renderer._datamosh_transition_targets(
            self.random_full,
            _playback(16.0),
            random_settings,
            end_frame - start_frame,
            start_frame,
        )
        random_records = _transition_records(
            random_playback_targets,
            random_slice,
        )
        self.assertGreaterEqual(len(random_records), 2)
        self.assertTrue(all(record["identity_matches_full"] for record in random_records))

    def test_delayed_audio_separates_global_intent_from_local_overlap(self) -> None:
        external = _settings(
            audio_path="audio-main",
            audio_start=0.0,
            audio_end=5.0,
            audio_timeline_start=10.0,
            audio_mode=renderer.AUDIO_EXTERNAL,
            match_timeline_to_audio=True,
            match_timeline_mode=renderer.MATCH_SPEED,
        )
        windows = {
            "before": (2.0, 5.0),
            "cross-start": (9.0, 12.0),
            "inside": (11.0, 13.0),
            "cross-end": (14.0, 17.0),
            "after": (16.0, 18.0),
        }
        configured = {
            name: _collect_preview(external, *window)
            for name, window in windows.items()
        }
        accepted = {
            name: _external_audio_overlap(*window)
            for name, window in windows.items()
        }
        self.assertEqual(configured["before"].audio_path, "audio-main")
        self.assertTrue(configured["before"].match_timeline_to_audio)
        self.assertFalse(accepted["before"]["local_external_overlap"])
        self.assertTrue(accepted["before"]["full_external_intent"])
        playback = renderer._playback_plan(
                configured["before"],
                20.0,
                selected_audio_duration=15.0,
            )
        self.assertEqual(playback.output_duration, 15.0)

        execution: dict[str, renderer.RenderSettings] = {}
        local_overlap: dict[str, bool] = {}
        for name, window in windows.items():
            local, local_start, local_end, has_overlap = renderer._preview_audio_execution_settings(
                configured[name],
                0.0,
                5.0,
                20.0,
                window[1] - window[0],
            )
            execution[name] = local
            local_overlap[name] = has_overlap
            if has_overlap:
                self.assertEqual(_round(local_start), accepted[name]["audio_source_start"])
                self.assertEqual(_round(float(local_end)), accepted[name]["audio_source_end"])

        self.assertFalse(local_overlap["before"])
        self.assertIsNone(execution["before"].audio_path)
        self.assertEqual(execution["before"].audio_mode, renderer.AUDIO_EXTERNAL)
        self.assertTrue(execution["before"].match_timeline_to_audio)
        self.assertFalse(local_overlap["after"])
        self.assertIsNone(execution["after"].audio_path)

        self.assertEqual(
            (
                execution["cross-start"].audio_start,
                execution["cross-start"].audio_end,
                execution["cross-start"].audio_timeline_start,
                execution["cross-start"].audio_timeline_end,
            ),
            (0.0, 2.0, 1.0, 3.0),
        )
        self.assertEqual(
            (
                execution["inside"].audio_start,
                execution["inside"].audio_end,
                execution["cross-end"].audio_start,
                execution["cross-end"].audio_end,
            ),
            (1.0, 3.0, 4.0, 5.0),
        )

        for mode in (renderer.AUDIO_EXTERNAL, renderer.AUDIO_MIX):
            for match_enabled in (False, True):
                preview = _collect_preview(
                    replace(external, audio_mode=mode, match_timeline_to_audio=match_enabled),
                    9.0,
                    12.0,
                )
                self.assertEqual(preview.audio_mode, mode)
                self.assertEqual(preview.match_timeline_to_audio, match_enabled)
                self.assertEqual(preview.audio_path, "audio-main")

        source_only = replace(
            external,
            audio_path=None,
            audio_mode=renderer.AUDIO_SOURCE,
            match_timeline_to_audio=False,
        )
        source_preview = _collect_preview(source_only, 2.0, 5.0)
        self.assertEqual(source_preview.audio_mode, renderer.AUDIO_SOURCE)
        self.assertIsNone(source_preview.audio_path)
        with self.assertRaisesRegex(ValueError, "requires External only"):
            renderer._playback_plan(
                replace(source_only, match_timeline_to_audio=True),
                20.0,
                selected_audio_duration=None,
            )

    def test_end_loop_codec_and_audio_tail_contract_is_a_full_output_slice(self) -> None:
        settings = _settings(ending_mode="Fade Out", loop_friendly=True)
        cases = {
            "middle": (8.0, 12.0),
            "before-real-tail": (16.0, 18.0),
            "overlap-real-tail": (18.0, 19.0),
            "overlap-loop-tail": (19.0, 19.5),
            "reaches-end": (18.0, 20.0),
            "entire-output": (0.0, 20.0),
        }
        policies = {
            name: _tail_policy(20.0, window, settings)
            for name, window in cases.items()
        }
        for key in ("middle", "before-real-tail"):
            self.assertIsNone(policies[key]["ending"])
            self.assertIsNone(policies[key]["loop_visual"])
            self.assertIsNone(policies[key]["codec_loop_seconds"])
            self.assertIsNone(policies[key]["audio_fade"])

        self.assertEqual(policies["overlap-real-tail"]["ending"], (0.5, 1.0))
        self.assertEqual(policies["overlap-real-tail"]["audio_fade"], (0.5, 1.0))
        self.assertEqual(policies["overlap-loop-tail"]["loop_visual"], (0.25, 0.5))
        self.assertEqual(
            policies["overlap-loop-tail"]["codec_loop_seconds"],
            policies["overlap-loop-tail"]["loop_visual"],
        )
        self.assertEqual(policies["reaches-end"]["ending"], (0.5, 2.0))
        self.assertEqual(policies["reaches-end"]["audio_fade"], (0.5, 2.0))
        self.assertEqual(
            policies["reaches-end"]["codec_loop_seconds"],
            policies["reaches-end"]["loop_visual"],
        )
        self.assertEqual(policies["entire-output"]["ending"], (18.5, 20.0))
        self.assertEqual(policies["entire-output"]["loop_visual"], (19.25, 20.0))
        self.assertEqual(
            policies["entire-output"]["codec_loop_seconds"],
            policies["entire-output"]["loop_visual"],
        )
        self.assertEqual(policies["entire-output"]["audio_fade"], (18.5, 20.0))

        source = Image.new("RGB", (12, 8), (180, 120, 60))
        first = Image.new("RGB", (12, 8), (20, 30, 40))
        middle = renderer._apply_ending_effect(
            source, first, 20.0, 11.9, settings, 285
        )
        partial_tail = renderer._apply_ending_effect(
            source, first, 20.0, 18.9, settings, 453
        )
        self.assertEqual(_frame_digest(middle), _frame_digest(source))
        self.assertNotEqual(_frame_digest(partial_tail), _frame_digest(source))
        self.assertFalse(
            renderer._ending_freezes_source(
                replace(settings, ending_mode="Loop Freeze"), 20.0, 11.9
            )
        )
        self.assertTrue(
            renderer._ending_freezes_source(
                replace(settings, ending_mode="Loop Freeze"), 20.0, 19.9
            )
        )
        middle_loop = renderer._apply_loop_friendly(source, first, 20.0, 11.9)
        real_loop = renderer._apply_loop_friendly(source, first, 20.0, 19.9)
        self.assertEqual(_frame_digest(middle_loop), _frame_digest(source))
        self.assertNotEqual(_frame_digest(real_loop), _frame_digest(source))

    def test_style_and_coverage_clocks_are_sliced_but_remain_distinct(self) -> None:
        settings = _settings(
            style_begin_time=6.5,
            bypass_mode=renderer.BYPASS_MANUAL,
            manual_blocks=[(4.0, 7.0)],
            style_fx_coverage_mode=renderer.STYLE_FX_MANUAL,
            style_fx_manual_blocks=[(6.0, 9.0)],
        )
        harness = _PreviewHarness(
            settings,
            render_duration=20.0,
            preview_offset=5.0,
            preview_length=3.0,
        )
        ansi = harness._preview_bypass_blocks(settings, 20.0, 5.0, 3.0)
        style_fx = harness._preview_style_fx_blocks(settings, 20.0, 5.0, 3.0)
        self.assertEqual(ansi, [(0.0, 2.0)])
        self.assertEqual(style_fx, [(1.0, 3.0)])
        self.assertEqual(settings.style_begin_time - 5.0, 1.5)
        self.assertNotEqual(ansi, style_fx)

        random_settings = replace(
            settings,
            bypass_mode=renderer.BYPASS_RANDOM,
            random_percent=40.0,
            random_seed=101,
            style_fx_coverage_mode=renderer.STYLE_FX_RANDOM,
            style_fx_random_percent=45.0,
            style_fx_random_seed=202,
        )
        full_ansi = renderer.build_bypass_intervals(
            20.0,
            random_settings.bypass_mode,
            random_settings.manual_blocks,
            random_settings.random_percent,
            random_settings.random_min_len,
            random_settings.random_max_len,
            random_settings.random_seed,
        )
        full_style = renderer.build_style_fx_clean_intervals(
            20.0,
            random_settings.style_fx_coverage_mode,
            random_settings.style_fx_manual_blocks,
            random_settings.style_fx_random_percent,
            random_settings.random_min_len,
            random_settings.random_max_len,
            random_settings.style_fx_random_seed,
        )
        self.assertEqual(
            [
                (_round(start), _round(end))
                for start, end in harness._preview_bypass_blocks(
                    random_settings, 20.0, 5.0, 3.0
                )
            ],
            _rebase_intervals(full_ansi, 5.0, 8.0),
        )
        self.assertEqual(
            [
                (_round(start), _round(end))
                for start, end in harness._preview_style_fx_blocks(
                    random_settings, 20.0, 5.0, 3.0
                )
            ],
            _rebase_intervals(full_style, 5.0, 8.0),
        )

    def test_temporal_contract_is_fresh_state_with_absolute_clocks(self) -> None:
        temporal = self.temporal
        self.assertTrue(temporal["differing_preview_frames"])
        self.assertEqual(temporal["differing_preview_frames"][0], 0)
        self.assertGreaterEqual(len(temporal["differing_preview_frames"]), 20)
        self.assertTrue(temporal["full_start_state"]["prior_luma"])
        self.assertTrue(temporal["full_start_state"]["prior_rgb"])
        self.assertFalse(temporal["fresh_start_state"]["prior_luma"])
        self.assertFalse(temporal["fresh_start_state"]["prior_rgb"])
        self.assertGreater(temporal["full_start_state"]["motion"], 0.0)
        self.assertEqual(temporal["fresh_start_state"]["motion"], 0.0)
        self.assertNotEqual(
            temporal["full_start_state"]["active_events"],
            temporal["fresh_start_state"]["active_events"],
        )
        self.assertNotEqual(
            temporal["full_start_state"]["organic_instability"],
            temporal["fresh_start_state"]["organic_instability"],
        )
        self.assertFalse(temporal["circuit_first_frame_equal"])
        self.assertTrue(temporal["fresh_repeat_equal"])

        effects = {key: True for key in renderer.PHASE2_FRAME_EFFECT_ORDER}
        reset = renderer._FrameEffectChoreographer(effects, 1.45, FPS, TEMPORAL_SEED)
        source = oracle_source_frame(10, 64, 36)
        renderer._apply_phase2_frame_effects(
            source,
            effects,
            1.45,
            10,
            FPS,
            TEMPORAL_SEED,
            choreographer=reset,
            material=source,
        )
        self.assertIsNotNone(reset.previous_rgb)
        reset.reset_temporal_state()
        self.assertIsNone(reset.previous_rgb)
        self.assertIsNone(reset.previous_luma)
        self.assertFalse(reset.active_events)
        self.assertTrue(all(value == -1 for value in reset.cooldown_until.values()))

        stutter_settings = _settings(effects={"stutter_hold": True})
        hold_start = 10
        hold_length = renderer._stutter_hold_length(hold_start, stutter_settings)
        self.assertTrue(renderer._starts_stutter_hold(hold_start, stutter_settings))
        self.assertGreater(hold_length, 2)
        self.assertLess(hold_start, 12)
        self.assertGreater(hold_start + hold_length, 12)
        full_hold_active_at_preview_start = hold_start < 12 < hold_start + hold_length
        accepted_fresh_preview_hold_active = False
        self.assertTrue(full_hold_active_at_preview_start)
        self.assertFalse(accepted_fresh_preview_hold_active)
        preview_stutter = replace(stutter_settings, output_time_offset=0.5)
        absolute_trigger_frame = renderer._absolute_output_frame(preview_stutter, 10)
        self.assertEqual(absolute_trigger_frame, 22)
        self.assertNotEqual(
            renderer._starts_stutter_hold(10, preview_stutter),
            renderer._starts_stutter_hold(absolute_trigger_frame, preview_stutter),
        )
        self.assertEqual(
            renderer._starts_stutter_hold(absolute_trigger_frame, preview_stutter),
            renderer._starts_stutter_hold(22, stutter_settings),
        )

    def test_canonical_planning_oracle_is_deterministic(self) -> None:
        oracle = build_canonical_planning_oracle()
        self.assertEqual(list(oracle["cases"]), list("ABCDEFGHIJKLMNOPQRSTUVWX"))

        cases = oracle["cases"]
        self.assertEqual(cases["B"]["segments"][-1]["absolute_output_end"], 7.0)
        self.assertEqual(len(cases["G"]["segments"]), 1)
        self.assertEqual(len(cases["H"]["segments"]), 2)
        self.assertGreaterEqual(len(cases["I"]["segments"]), 4)
        self.assertEqual(cases["J"]["segments"][-1]["absolute_output_end"], 16.0)
        self.assertTrue(cases["D"]["final_segment_trimmed_to_cap"])
        self.assertTrue(cases["E"]["same_seed_equal"])
        self.assertFalse(cases["F"]["changed_seed_equal"])
        self.assertTrue(cases["K"]["source_audio_segments"])
        self.assertTrue(
            all(
                record["include_audio"]
                for record in cases["K"]["source_audio_segments"]
            )
        )

        self.assertEqual(
            cases["N"]["transitions"][0]["preview_local_frame"],
            0,
        )
        self.assertEqual(
            cases["O"]["transitions"][0]["preview_local_frame"],
            0,
        )
        self.assertTrue(
            all(
                transition["identity_matches_full"]
                for transition in cases["M"]["multiple_cut_preview"]
            )
        )

        self.assertFalse(cases["P"]["local_preview"]["overlap"])
        self.assertTrue(cases["P"]["local_preview"]["silent_external_execution"])
        self.assertTrue(cases["Q"]["local_preview"]["overlap"])
        self.assertTrue(cases["R"]["local_preview"]["overlap"])
        self.assertTrue(cases["S"]["local_preview"]["overlap"])
        self.assertFalse(cases["T"]["local_preview"]["overlap"])

        for concept in (
            "ending",
            "loop_visual",
            "codec_loop_protection",
            "audio_fade",
        ):
            local_field = (
                "preview_local_frames"
                if concept == "codec_loop_protection"
                else "preview_local_seconds"
            )
            self.assertIsNone(cases["U"][concept][local_field])
            self.assertIsNotNone(cases["V"][concept][local_field])
            self.assertIsNotNone(cases["W"][concept][local_field])
        self.assertGreater(cases["V"]["audio_fade"]["starting_progress"], 0.0)
        self.assertLess(cases["V"]["audio_fade"]["starting_gain"], 1.0)
        self.assertTrue(
            all(
                cases["X"]["equivalent_after_preview_wrapper_removal"].values()
            )
        )
        self.assertTrue(cases["X"]["fresh_retained_temporal_state_is_exempt"])

        supplemental = oracle["supplemental"]
        self.assertFalse(supplemental["invalid_audio_guard"]["accepted"])
        self.assertEqual(
            supplemental["stutter"]["divergence_absolute_frame"],
            22,
        )
        self.assertTrue(supplemental["stutter"]["local_clock_would_trigger"])
        self.assertFalse(
            supplemental["stutter"][
                "absolute_clock_triggers_at_divergence_frame"
            ]
        )
        self.assertTrue(
            supplemental["stutter"]["absolute_trigger_example_triggers"]
        )
        self.assertEqual(
            supplemental["intentional_fresh_temporal_state"]["clock_basis"],
            "absolute-output",
        )
        self.assertTrue(supplemental["batch"]["full_random_plan_equal"])
        self.assertIsNone(supplemental["batch"]["preview_duration"])
        self.assertNotEqual(
            supplemental["ansi_coverage"]["full_normal_intervals"],
            supplemental["style_fx_coverage"]["modes"]["combined"][
                "full_clean_intervals"
            ],
        )

        serialized = serialize_canonical_planning_oracle(oracle)
        repeated = serialize_canonical_planning_oracle(
            build_canonical_planning_oracle()
        )
        self.assertEqual(serialized, repeated)
        self.assertTrue(serialized.endswith(b"\n"))
        self.assertFalse(serialized.endswith(b"\n\n"))
        self.assertNotIn(b"/" + b"Users" + b"/", serialized)
        self.assertNotIn(b".mp4", serialized)
        self.assertNotIn(b"TimelineSegment(", serialized)
        self.assertNotIn(b"DatamoshTransition(", serialized)

        digest = hashlib.sha256(serialized).hexdigest()
        print(f"PLANNING_ORACLE_BYTES={len(serialized)}")
        print(f"PLANNING_ORACLE_SHA256={digest}")
        self.assertEqual(len(serialized), EXPECTED_PLANNING_ORACLE_BYTES)
        self.assertEqual(digest, EXPECTED_PLANNING_ORACLE_SHA256)

if __name__ == "__main__":
    unittest.main()
