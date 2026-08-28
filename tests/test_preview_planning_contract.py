"""Prove the repaired full-output/Preview planning contract.

Phase 14A recorded the historical divergences.  These tests now assert that
production Preview behavior consumes canonical full-output decisions directly.
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
    for segment in segments:
        overlap_start = max(window_start, segment.timeline_start)
        overlap_end = min(window_end, segment.timeline_end)
        if overlap_end <= overlap_start:
            continue
        source_start = segment.source_start + overlap_start - segment.timeline_start
        records.append(
            {
                "source_id": segment.path,
                "source_start": _round(source_start),
                "source_end": _round(source_start + overlap_end - overlap_start),
                "full_output_start": _round(overlap_start),
                "full_output_end": _round(overlap_end),
                "preview_start": _round(overlap_start - window_start),
                "preview_end": _round(overlap_end - window_start),
                "include_audio": segment.include_audio,
            }
        )
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
                "full_output_time": _round(full_output_time),
                "preview_local_time": _round(full_output_time - window_start),
                "absolute_frame": target.absolute_frame,
                "preview_local_frame": target.frame,
                "stable_cut_ordinal": target.transition_ordinal,
                "full_name": canonical.visual_transition,
                "preview_name": target.visual_transition,
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
            [(record["source_id"], record["preview_start"], record["preview_end"]) for record in preview_records],
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
            _slice_records(self.two_sources, 0.0, capped.output_duration)[-1]["full_output_end"],
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
        self.assertEqual(previews["beginning"][0]["full_output_start"], 0.0)
        self.assertEqual(previews["final"][-1]["full_output_end"], 16.0)

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
        self.assertEqual(records[0]["stable_cut_ordinal"], 2)
        self.assertEqual(records[0]["preview_name"], "Buffer Underrun")
        self.assertEqual(records[0]["preview_name"], records[0]["full_name"])

        exactly_at_cut = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            random_settings,
            3 * FPS,
            15 * FPS,
        )
        exact_records = _transition_records(full_random, exactly_at_cut)
        self.assertEqual(exact_records[0]["absolute_frame"], 360)
        self.assertEqual(exact_records[0]["preview_local_frame"], 0)
        self.assertEqual(exact_records[0]["preview_name"], "Buffer Underrun")

        multiple = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            random_settings,
            10 * FPS,
            6 * FPS,
        )
        multiple_records = _transition_records(full_random, multiple)
        self.assertEqual([record["stable_cut_ordinal"] for record in multiple_records], [1, 2])
        self.assertTrue(all(record["preview_name"] == record["full_name"] for record in multiple_records))

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
        self.assertEqual(fixed_records[0]["preview_name"], "RGB Burst")
        self.assertEqual(fixed_records[0]["preview_name"], fixed_records[0]["full_name"])
        fixed_exact = renderer._datamosh_transition_targets(
            segments,
            full_playback,
            fixed_settings,
            3 * FPS,
            5 * FPS,
        )
        fixed_exact_records = _transition_records(full_fixed, fixed_exact)
        self.assertEqual(fixed_exact_records[0]["preview_local_frame"], 0)
        self.assertEqual(fixed_exact_records[0]["preview_name"], "RGB Burst")

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
        self.assertTrue(all(record["preview_name"] == record["full_name"] for record in random_records))

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

    def test_A_through_X_plain_repaired_evidence_is_deterministic(self) -> None:
        random_inside = self.random_full[2]
        inside_window = (
            random_inside.timeline_start + min(0.05, random_inside.duration / 4.0),
            random_inside.timeline_start + min(0.25, random_inside.duration / 2.0),
        )
        crossing_window = (
            max(0.0, self.random_full[1].timeline_start - 0.1),
            min(16.0, self.random_full[4].timeline_start + 0.1),
        )
        transition_segments = _sequential_segments(
            (
                ("video-a", "video", 5.0, 0.0, True),
                ("photo-b", "photo", 5.0, 0.0, False),
                ("video-c", "video", 5.0, 30.0, False),
            )
        )
        fixed_settings = _settings(transition_mode="RGB Burst")
        random_transition_settings = _settings(
            transition_mode="Random", random_seed=123, weird_seed=None
        )
        fixed_targets = renderer._datamosh_transition_targets(
            transition_segments, _playback(15.0), fixed_settings, 15 * FPS, 0
        )
        random_targets = renderer._datamosh_transition_targets(
            transition_segments,
            _playback(15.0),
            random_transition_settings,
            15 * FPS,
            0,
        )
        coverage_settings = _settings(
            style_fx_coverage_mode=renderer.STYLE_FX_MANUAL,
            style_fx_manual_blocks=[(6.0, 9.0)],
        )
        coverage_harness = _PreviewHarness(
            coverage_settings,
            render_duration=20.0,
            preview_offset=5.0,
            preview_length=3.0,
        )
        random_coverage_settings = replace(
            coverage_settings,
            style_fx_coverage_mode=renderer.STYLE_FX_RANDOM,
            style_fx_random_percent=45.0,
            style_fx_random_seed=202,
        )
        middle_tail = _tail_policy(
            20.0,
            (8.0, 12.0),
            _settings(ending_mode="Fade Out", loop_friendly=True),
        )
        true_tail = _tail_policy(
            20.0,
            (19.0, 20.0),
            _settings(ending_mode="Fade Out", loop_friendly=True),
        )
        full_preview_settings = replace(
            _settings(ending_mode="Fade Out", loop_friendly=True),
            preview_duration=20.0,
            output_time_offset=0.0,
        )
        stutter_clock_settings = replace(_settings(), output_time_offset=0.5)
        oracle = {
            "A": _slice_records(self.two_sources, 0.0, 20.0),
            "B": _slice_records(self.two_sources, 7.0, 13.0),
            "C": _slice_records(self.two_sources, 0.0, 7.0),
            "D": _slice_records(self.random_full, 0.0, 16.0),
            "E": _slice_records(self.random_full, *inside_window),
            "F": _slice_records(self.random_full, *crossing_window),
            "G": [
                [target.absolute_frame, target.visual_transition]
                for target in fixed_targets
            ],
            "H": [
                [target.absolute_frame, target.visual_transition]
                for target in random_targets
            ],
            "I": _external_audio_overlap(2.0, 5.0),
            "J": _external_audio_overlap(9.0, 12.0),
            "K": _tail_policy(20.0, (8.0, 12.0), _settings(loop_friendly=True)),
            "L": _tail_policy(20.0, (18.0, 20.0), _settings(loop_friendly=True)),
            "M": {"absolute_style_start": 6.5, "preview_local_start": 1.5},
            "N": coverage_harness._preview_style_fx_blocks(
                coverage_settings, 20.0, 5.0, 3.0
            ),
            "O": coverage_harness._preview_style_fx_blocks(
                random_coverage_settings, 20.0, 5.0, 3.0
            ),
            "P": self.temporal,
            "Q": middle_tail["loop_visual"],
            "R": true_tail["loop_visual"],
            "S": {
                "visual": true_tail["loop_visual"],
                "codec": true_tail["codec_loop_seconds"],
            },
            "T": middle_tail["audio_fade"],
            "U": true_tail["audio_fade"],
            "V": {
                "local_frame": 10,
                "absolute_frame": renderer._absolute_output_frame(
                    stutter_clock_settings,
                    10,
                ),
            },
            "W": {
                "prior_luma": self.temporal["fresh_start_state"]["prior_luma"],
                "prior_rgb": self.temporal["fresh_start_state"]["prior_rgb"],
                "fresh_repeat_equal": self.temporal["fresh_repeat_equal"],
            },
            "X": {
                "render_duration": renderer._render_window_duration(
                    full_preview_settings,
                    20.0,
                ),
                "transitions": [
                    [
                        target.frame,
                        target.absolute_frame,
                        target.transition_ordinal,
                        target.visual_transition,
                    ]
                    for target in renderer._datamosh_transition_targets(
                        transition_segments,
                        _playback(15.0),
                        random_transition_settings,
                        15 * FPS,
                        0,
                    )
                ],
                "tail": _tail_policy(20.0, (0.0, 20.0), full_preview_settings),
            },
        }
        self.assertEqual(list(oracle), list("ABCDEFGHIJKLMNOPQRSTUVWX"))
        self.assertEqual(oracle["S"]["visual"], oracle["S"]["codec"])
        self.assertIsNone(oracle["T"])
        self.assertEqual(oracle["V"]["absolute_frame"], 22)
        self.assertEqual(oracle["X"]["render_duration"], 20.0)
        first = json.dumps(oracle, sort_keys=True, separators=(",", ":"))
        second = json.dumps(oracle, sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)
        self.assertNotIn("/", first)
        self.assertNotIn(".mp4", first)


if __name__ == "__main__":
    unittest.main()
