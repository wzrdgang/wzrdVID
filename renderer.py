"""Video-to-ANSI-art renderer for WZRD.VID."""

from __future__ import annotations

import colorsys
import math
import os
import random
import subprocess
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import datamosh
import ffmpeg_utils
import still_cache
from presets import get_preset
from state_contract import (
    CODEC_LAYER_ORDER,
    MAX_ZONES,
    STYLE_FX_FULL,
    STYLE_FX_MANUAL,
    STYLE_FX_MANUAL_RANDOM,
    STYLE_FX_RANDOM,
    ZONE_ASSIGNMENT_EFFECT_ORDER,
    ZoneDefinition,
    normalize_codec_layer_order,
    normalize_style_fx_coverage_mode,
    normalize_zone_state,
)


ProgressCallback = Callable[[int], None] | None
LogCallback = Callable[[str], None] | None
Interval = tuple[float, float]
FrameWriter = Callable[[int, Image.Image], None]


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
LONG_MEDIA_WARNING_SECONDS = 30 * 60
VERY_LONG_MEDIA_WARNING_SECONDS = 60 * 60
PHASE2_FRAME_EFFECT_ORDER = (
    "pixel_sorting",
    "databending",
    "circuit_bending",
    "hex_editing",
    "random_noise_bw",
)
_PIXEL_SORTING_SALT = 0x50_49_58_45_4C
_DATABENDING_SALT = 0x44_41_54_41_42
_CIRCUIT_BENDING_SALT = 0x43_49_52_43_55
_HEX_EDITING_SALT = 0x48_45_58_45_44
_RANDOM_NOISE_BW_SALT = 0x42_57_4E_4F_49
def rasterize_zone(
    zone: ZoneDefinition,
    output_size: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """Resolve one Zone to a clamped half-open output-pixel rectangle."""
    output_width = max(0, int(output_size[0]))
    output_height = max(0, int(output_size[1]))
    if output_width <= 0 or output_height <= 0:
        return None
    left = max(0, min(output_width, math.floor(zone.x * output_width)))
    top = max(0, min(output_height, math.floor(zone.y * output_height)))
    right = max(0, min(output_width, math.ceil((zone.x + zone.width) * output_width)))
    bottom = max(0, min(output_height, math.ceil((zone.y + zone.height) * output_height)))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom

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
class _PhotoFrameRecord:
    image: Image.Image
    array: np.ndarray
    is_heic: bool


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
    max_video_length: float | None = None
    random_clip_assembly: bool = False
    style_begin_time: float = 0.0
    output_time_offset: float = 0.0
    audio_mode: str = AUDIO_EXTERNAL
    worky_music_mode: bool = False
    match_timeline_to_audio: bool = False
    match_timeline_mode: str = MATCH_SPEED
    target_size_mb: float | None = None
    optimize_enabled: bool = False
    optimize_target_mb: float = 29.0
    chunky_blocks: bool = False
    effects: dict[str, bool] = field(default_factory=dict)
    zones: tuple[ZoneDefinition, ...] = ()
    effect_zone_assignments: dict[str, str] = field(default_factory=dict)
    codec_layer_order: tuple[str, ...] = CODEC_LAYER_ORDER
    effect_intensity: float = 1.0
    bypass_mode: str = BYPASS_FULL_ANSI
    manual_blocks: list[Interval] = field(default_factory=list)
    random_percent: float = 0.0
    random_seed: int | None = None
    random_min_len: float = RANDOM_CHUNK_MIN
    random_max_len: float = RANDOM_CHUNK_MAX
    style_fx_coverage_mode: str = STYLE_FX_FULL
    style_fx_manual_blocks: list[Interval] = field(default_factory=list)
    style_fx_random_percent: float = 0.0
    style_fx_random_seed: int | None = None
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
    experimental_frame_pipe: bool = False
    force_legacy_png_staging: bool = False
    preview_duration: float | None = None


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
    x_positions: tuple[int, ...]
    y_positions: tuple[int, ...]


@dataclass
class _FrameTimingDetail:
    resize_framing_seconds: float = 0.0
    ansi_effect_seconds: float = 0.0
    text_prepare_seconds: float = 0.0
    image_draw_text_seconds: float = 0.0
    ansi_output_effect_seconds: float = 0.0


@dataclass
class _FrameMaterialAnalysis:
    """Lazy, render-local material measurements shared by the Style effects."""

    rgb: np.ndarray
    previous_luma: np.ndarray | None = None
    _luma: np.ndarray | None = field(default=None, init=False, repr=False)
    _edge_x: np.ndarray | None = field(default=None, init=False, repr=False)
    _edge_y: np.ndarray | None = field(default=None, init=False, repr=False)
    _edge_magnitude: np.ndarray | None = field(default=None, init=False, repr=False)
    _texture: np.ndarray | None = field(default=None, init=False, repr=False)
    _motion: np.ndarray | None = field(default=None, init=False, repr=False)
    _texture_activity: float | None = field(default=None, init=False, repr=False)
    _motion_activity: float | None = field(default=None, init=False, repr=False)
    _motion_direction: tuple[float, float, float] | None = field(default=None, init=False, repr=False)

    @property
    def luma(self) -> np.ndarray:
        if self._luma is None:
            self._luma = _phase2_luma(self.rgb)
        return self._luma

    def directional_edges(self) -> tuple[np.ndarray, np.ndarray]:
        if self._edge_x is None or self._edge_y is None:
            self._edge_x = np.abs(cv2.Sobel(self.luma, cv2.CV_32F, 1, 0, ksize=3))
            self._edge_y = np.abs(cv2.Sobel(self.luma, cv2.CV_32F, 0, 1, ksize=3))
        return self._edge_x, self._edge_y

    @property
    def edge_magnitude(self) -> np.ndarray:
        if self._edge_magnitude is None:
            edge_x, edge_y = self.directional_edges()
            self._edge_magnitude = cv2.magnitude(edge_x, edge_y)
        return self._edge_magnitude

    @property
    def texture(self) -> np.ndarray:
        if self._texture is None:
            local_mean = cv2.GaussianBlur(self.luma, (0, 0), 2.0)
            raw_texture = np.abs(self.luma - local_mean)
            self._texture_activity = float(np.clip(float(raw_texture.mean()) / 32.0, 0.0, 1.0))
            self._texture = _normalized_signal(raw_texture)
        return self._texture

    @property
    def motion(self) -> np.ndarray:
        if self._motion is None:
            if self.previous_luma is None or self.previous_luma.shape != self.luma.shape:
                self._motion = np.zeros_like(self.luma, dtype=np.float32)
                self._motion_activity = 0.0
            else:
                raw_motion = np.abs(self.luma - self.previous_luma)
                self._motion_activity = float(np.clip(float(raw_motion.mean()) / 64.0, 0.0, 1.0))
                self._motion = _normalized_signal(raw_motion)
        return self._motion

    @property
    def edge_activity(self) -> float:
        return float(np.clip(float(self.edge_magnitude.mean()) / 96.0, 0.0, 1.0))

    @property
    def texture_activity(self) -> float:
        if self._texture_activity is None:
            _ = self.texture
        return float(self._texture_activity or 0.0)

    @property
    def motion_activity(self) -> float:
        if self._motion_activity is None:
            _ = self.motion
        return float(self._motion_activity or 0.0)

    def motion_direction(self) -> tuple[float, float, float]:
        """Return a small global phase-shift signal; this is not retained optical flow."""
        if self._motion_direction is None:
            if self.previous_luma is None or self.previous_luma.shape != self.luma.shape:
                self._motion_direction = (0.0, 0.0, 0.0)
            elif self.motion_activity < 0.012:
                self._motion_direction = (0.0, 0.0, 0.0)
            else:
                height, width = self.luma.shape
                scale = min(1.0, 192.0 / max(1, width), 108.0 / max(1, height))
                sample_size = (
                    max(16, int(round(width * scale))),
                    max(16, int(round(height * scale))),
                )
                previous = cv2.resize(
                    self.previous_luma,
                    sample_size,
                    interpolation=cv2.INTER_AREA,
                ).astype(np.float32)
                current = cv2.resize(
                    self.luma,
                    sample_size,
                    interpolation=cv2.INTER_AREA,
                ).astype(np.float32)
                window = cv2.createHanningWindow(sample_size, cv2.CV_32F)
                shift, response = cv2.phaseCorrelate(previous, current, window)
                normalized_x = float(np.clip(shift[0] / max(1.0, sample_size[0] * 0.12), -1.0, 1.0))
                normalized_y = float(np.clip(shift[1] / max(1.0, sample_size[1] * 0.12), -1.0, 1.0))
                confidence = float(np.clip(response, 0.0, 1.0))
                self._motion_direction = (normalized_x, normalized_y, confidence)
        return self._motion_direction

    @property
    def bright_fraction(self) -> float:
        return float(np.mean(self.luma >= 205.0))

    @property
    def channel_spread(self) -> float:
        means = self.rgb.reshape(-1, 3).mean(axis=0)
        return float(np.clip(float(np.ptp(means)) / 128.0, 0.0, 1.0))

    def activity_focus(self) -> tuple[float, float]:
        activity = self.edge_magnitude + self.texture * 72.0
        flat_index = int(np.argmax(activity))
        y, x = np.unravel_index(flat_index, activity.shape)
        height, width = activity.shape
        return (
            float(x) / max(1.0, float(width - 1)),
            float(y) / max(1.0, float(height - 1)),
        )

    def scatter_regions(self, *, limit: int = 6) -> tuple[datamosh.DatamoshSpatialRegion, ...]:
        """Return a few anonymous coarse cells ranked by structure and local motion."""
        if limit <= 0:
            return ()
        edge = _normalized_signal(self.edge_magnitude)
        signal = edge * 0.42 + self.texture * 0.28 + self.motion * 0.60
        height, width = signal.shape
        rows, columns = 4, 5
        candidates: list[tuple[float, int, int, int, int]] = []
        for row in range(rows):
            y0 = int(round(row * height / rows))
            y1 = int(round((row + 1) * height / rows))
            for column in range(columns):
                x0 = int(round(column * width / columns))
                x1 = int(round((column + 1) * width / columns))
                cell = signal[y0:y1, x0:x1]
                score = float(cell.mean()) if cell.size else 0.0
                candidates.append((score, x0, y0, x1, y1))
        peak = max((candidate[0] for candidate in candidates), default=0.0)
        if peak <= 0.0:
            return ()
        selected = sorted(candidates, key=lambda candidate: candidate[0], reverse=True)[:limit]
        return tuple(
            datamosh.DatamoshSpatialRegion(
                x=x0 / max(1.0, float(width)),
                y=y0 / max(1.0, float(height)),
                width=(x1 - x0) / max(1.0, float(width)),
                height=(y1 - y0) / max(1.0, float(height)),
                weight=max(0.0, min(1.0, score / peak)),
            )
            for score, x0, y0, x1, y1 in selected
        )

    @property
    def cached_bytes(self) -> int:
        arrays = (
            self.rgb,
            self._luma,
            self._edge_x,
            self._edge_y,
            self._edge_magnitude,
            self._texture,
            self._motion,
        )
        return sum(int(array.nbytes) for array in arrays if array is not None)


@dataclass(frozen=True)
class _FrameEffectEvent:
    effect: str
    trigger_frame: int
    trigger_type: str
    attack_frames: int
    sustain_frames: int
    decay_frames: int
    peak_strength: float
    event_seed: int
    focus_x: float
    focus_y: float
    transition_absolute_frame: int | None
    organic_instability: float
    material_metrics: tuple[tuple[str, float], ...]

    @property
    def end_frame(self) -> int:
        return self.trigger_frame + self.attack_frames + self.sustain_frames + self.decay_frames


@dataclass(frozen=True)
class _FrameEffectControl:
    strength: float
    event_strength: float
    event_seed: int
    event_frame: int
    focus_x: float | None = None
    focus_y: float | None = None
    event: _FrameEffectEvent | None = None


_PHASE2_EVENT_SALT = 0x45_56_45_4E_54
_PHASE2_TRANSITION_SALT = 0x54_52_41_4E_53
_PHASE2_ORGANIC_SALT = 0x4F_52_47_41_4E_49_43


class _FrameEffectChoreographer:
    """Render-local material event state for the five fixed-order frame effects."""

    def __init__(
        self,
        effects: dict[str, bool],
        intensity: float,
        fps: int,
        seed: int | None,
        transitions: tuple[datamosh.DatamoshTransition, ...] = (),
        *,
        record_events: bool = False,
    ) -> None:
        self.enabled = tuple(key for key in PHASE2_FRAME_EFFECT_ORDER if _effect_on(effects, key))
        self.intensity = max(0.0, float(intensity))
        self.amount = _phase2_effect_amount(intensity)
        self.fps = max(1, int(fps))
        self.seed = seed
        self.transitions = {int(target.absolute_frame): target for target in transitions}
        self.transition_effects = self._select_transition_effects(tuple(transitions))
        self.active_events: dict[str, _FrameEffectEvent] = {}
        self.cooldown_until: dict[str, int] = {key: -1 for key in PHASE2_FRAME_EFFECT_ORDER}
        self.previous_scores: dict[str, float] = {key: 0.0 for key in PHASE2_FRAME_EFFECT_ORDER}
        self.previous_luma: np.ndarray | None = None
        self.previous_rgb: np.ndarray | None = None
        self.zone_previous_luma: dict[tuple[int, int, int, int], np.ndarray] = {}
        self.zone_previous_rgb: dict[tuple[int, int, int, int], np.ndarray] = {}
        self.organic_instability = 0.0
        self.organic_aftershock = 0.0
        self.organic_drive = 0.0
        self.previous_absolute_frame: int | None = None
        self.effect_wander: dict[str, float] = {
            key: 0.0 for key in PHASE2_FRAME_EFFECT_ORDER
        }
        self.ambient_seed: dict[str, int] = {
            key: _phase2_effect_seed(
                self.seed,
                _PHASE2_ORGANIC_SALT ^ _phase2_effect_salt(key),
                0,
            )
            for key in PHASE2_FRAME_EFFECT_ORDER
        }
        self.ambient_until: dict[str, int] = {
            key: -1 for key in PHASE2_FRAME_EFFECT_ORDER
        }
        self.record_events = record_events
        self.recorded_events: list[_FrameEffectEvent] = []
        self.recorded_organic_states: list[dict[str, float | int | bool]] = []
        self.peak_analysis_bytes = 0

    def _select_transition_effects(
        self,
        transitions: tuple[datamosh.DatamoshTransition, ...],
    ) -> dict[int, frozenset[str]]:
        selection_count = 1 + int(self.amount >= 0.34) + int(self.amount >= 0.80)
        selected: dict[int, frozenset[str]] = {}
        affinities = {
            "pixel_sorting": 0.05,
            "databending": 0.12,
            "circuit_bending": 0.16,
            "hex_editing": 0.02,
            "random_noise_bw": 0.0,
        }
        for target in transitions:
            ranked: list[tuple[float, str]] = []
            for effect_index, effect in enumerate(PHASE2_FRAME_EFFECT_ORDER):
                salt = _PHASE2_TRANSITION_SALT ^ (effect_index + 1) * 0x9E37
                rng = _phase2_effect_rng(self.seed, salt, int(target.absolute_frame))
                ranked.append((float(rng.random()) + affinities[effect], effect))
            ranked.sort(reverse=True)
            selected[int(target.absolute_frame)] = frozenset(
                effect for _, effect in ranked[:selection_count]
            )
        return selected

    def analysis_for(self, frame: np.ndarray | Image.Image) -> _FrameMaterialAnalysis:
        return _FrameMaterialAnalysis(
            rgb=_phase2_rgb_copy(frame),
            previous_luma=self.previous_luma,
        )

    def analysis_for_zone(
        self,
        frame: np.ndarray,
        rectangle: tuple[int, int, int, int],
    ) -> _FrameMaterialAnalysis:
        left, top, right, bottom = rectangle
        return _FrameMaterialAnalysis(
            rgb=np.ascontiguousarray(frame[top:bottom, left:right], dtype=np.uint8),
            previous_luma=self.zone_previous_luma.get(rectangle),
        )

    def controls_for(
        self,
        analysis: _FrameMaterialAnalysis,
        absolute_frame: int,
        effect_analyses: dict[str, _FrameMaterialAnalysis] | None = None,
    ) -> dict[str, _FrameEffectControl]:
        controls: dict[str, _FrameEffectControl] = {}
        transition = self.transitions.get(int(absolute_frame))
        analyses = effect_analyses or {}
        material = {
            effect: self._material_score(effect, analyses.get(effect, analysis))
            for effect in self.enabled
        }
        self._advance_organic_state(
            absolute_frame,
            tuple(score for score, _, _ in material.values()),
            transition is not None,
        )
        for effect in self.enabled:
            effect_analysis = analyses.get(effect, analysis)
            score, trigger_type, metrics = material[effect]
            event = self.active_events.get(effect)
            if event is not None and absolute_frame >= event.end_frame:
                self.active_events.pop(effect, None)
                event = None

            transition_selected = (
                transition is not None
                and effect in self.transition_effects.get(int(absolute_frame), frozenset())
            )
            if transition_selected:
                event = self._start_event(
                    effect,
                    absolute_frame,
                    "source_transition",
                    max(score, 0.72),
                    metrics,
                    effect_analysis,
                    transition_absolute_frame=int(absolute_frame),
                )
            elif event is None and absolute_frame >= self.cooldown_until[effect]:
                threshold = self._material_threshold(effect) * (
                    1.08 - 0.25 * self.organic_instability
                )
                previous_score = self.previous_scores[effect]
                crossed = score >= threshold and (
                    previous_score < threshold * 0.88
                    or score >= previous_score + 0.12
                )
                gate_rng = _phase2_effect_rng(
                    self.seed,
                    _PHASE2_EVENT_SALT ^ _phase2_effect_salt(effect),
                    absolute_frame,
                )
                material_gate = float(gate_rng.random()) < min(
                    0.98,
                    (0.46 + 0.44 * self.amount)
                    * (0.68 + 0.55 * self.organic_instability),
                )
                background_gate = (
                    score >= threshold * 0.45
                    and float(gate_rng.random())
                    < (0.0015 + 0.0065 * self.amount)
                    * (0.25 + 2.30 * self.organic_instability)
                )
                if crossed and material_gate:
                    event = self._start_event(
                        effect,
                        absolute_frame,
                        trigger_type,
                        score,
                        metrics,
                        effect_analysis,
                    )
                elif background_gate:
                    event = self._start_event(
                        effect,
                        absolute_frame,
                        "background_material",
                        max(score, threshold * 0.55),
                        metrics,
                        effect_analysis,
                    )

            controls[effect] = self._control_for(effect, absolute_frame, event)
            self.previous_scores[effect] = score
        distinct_analyses = {id(candidate): candidate for candidate in analyses.values()}
        analysis_bytes = analysis.cached_bytes + sum(
            candidate.cached_bytes
            for candidate in distinct_analyses.values()
            if candidate is not analysis
        )
        self.peak_analysis_bytes = max(self.peak_analysis_bytes, analysis_bytes)
        return controls

    def _advance_organic_state(
        self,
        absolute_frame: int,
        scores: tuple[float, ...],
        is_transition: bool,
    ) -> None:
        """Evolve one shared, slow material state without synchronizing effect RNGs."""
        frame = int(absolute_frame)
        if self.previous_absolute_frame is not None and frame != self.previous_absolute_frame + 1:
            self.organic_instability = 0.0
            self.organic_aftershock = 0.0
            self.organic_drive = 0.0
            self.effect_wander = {key: 0.0 for key in PHASE2_FRAME_EFFECT_ORDER}
            self.ambient_until = {key: -1 for key in PHASE2_FRAME_EFFECT_ORDER}

        mean_score = float(np.mean(scores)) if scores else 0.0
        peak_score = max(scores, default=0.0)
        material_change = max(0.0, peak_score - self.organic_drive)
        aftershock_decay = math.exp(-1.0 / (self.fps * (2.4 + 2.2 * self.amount)))
        self.organic_aftershock *= aftershock_decay
        self.organic_aftershock = max(
            self.organic_aftershock,
            min(1.0, material_change * 2.35),
            0.88 if is_transition else 0.0,
        )

        wander_period = max(2, int(round(self.fps * (4.5 - 1.5 * self.amount))))
        wander_bucket, wander_offset = divmod(frame, wander_period)
        wander_phase = wander_offset / float(wander_period)
        wander_phase = wander_phase * wander_phase * (3.0 - 2.0 * wander_phase)
        wander_rng_a = _phase2_effect_rng(
            self.seed,
            _PHASE2_ORGANIC_SALT,
            wander_bucket,
        )
        wander_rng_b = _phase2_effect_rng(
            self.seed,
            _PHASE2_ORGANIC_SALT,
            wander_bucket + 1,
        )
        slow_wander = (
            float(wander_rng_a.random()) * (1.0 - wander_phase)
            + float(wander_rng_b.random()) * wander_phase
        )
        target = float(
            np.clip(
                0.03
                + mean_score * (0.40 + 0.20 * self.amount)
                + peak_score * 0.18
                + self.organic_aftershock * (0.22 + 0.18 * self.amount)
                + slow_wander * (0.10 + 0.08 * self.amount),
                0.0,
                1.0,
            )
        )
        tau = (
            0.45 + 0.45 * (1.0 - self.amount)
            if target > self.organic_instability
            else 2.8 + 2.4 * (1.0 - self.amount)
        )
        alpha = 1.0 - math.exp(-1.0 / (self.fps * tau))
        self.organic_instability += (target - self.organic_instability) * alpha
        self.organic_drive = peak_score

        for effect in self.enabled:
            effect_rng = _phase2_effect_rng(
                self.seed,
                _PHASE2_ORGANIC_SALT ^ _phase2_effect_salt(effect),
                wander_bucket,
            )
            effect_target = float(effect_rng.random())
            effect_alpha = 1.0 - math.exp(
                -1.0 / (self.fps * (1.2 + float(effect_rng.random()) * 3.2))
            )
            self.effect_wander[effect] += (
                effect_target - self.effect_wander[effect]
            ) * effect_alpha

        self.previous_absolute_frame = frame
        if self.record_events:
            self.recorded_organic_states.append(
                {
                    "frame": frame,
                    "instability": round(self.organic_instability, 6),
                    "aftershock": round(self.organic_aftershock, 6),
                    "material_mean": round(mean_score, 6),
                    "material_peak": round(peak_score, 6),
                    "slow_wander": round(slow_wander, 6),
                    "transition": bool(is_transition),
                }
            )

    def commit(
        self,
        analysis: _FrameMaterialAnalysis,
        effect_input: np.ndarray | Image.Image,
    ) -> None:
        self.previous_luma = analysis.luma.copy()
        self.previous_rgb = _phase2_rgb_copy(effect_input)
        self.peak_analysis_bytes = max(
            self.peak_analysis_bytes,
            analysis.cached_bytes + int(self.previous_luma.nbytes) + int(self.previous_rgb.nbytes),
        )

    def commit_zones(
        self,
        analyses: dict[tuple[int, int, int, int], _FrameMaterialAnalysis],
        effect_input: np.ndarray,
    ) -> None:
        for rectangle, analysis in analyses.items():
            left, top, right, bottom = rectangle
            self.zone_previous_luma[rectangle] = analysis.luma.copy()
            self.zone_previous_rgb[rectangle] = np.ascontiguousarray(
                effect_input[top:bottom, left:right],
                dtype=np.uint8,
            )
        history_bytes = sum(array.nbytes for array in self.zone_previous_luma.values())
        history_bytes += sum(array.nbytes for array in self.zone_previous_rgb.values())
        analysis_bytes = sum(analysis.cached_bytes for analysis in analyses.values())
        self.peak_analysis_bytes = max(
            self.peak_analysis_bytes,
            int(history_bytes + analysis_bytes),
        )

    def reset_temporal_state(self) -> None:
        """Drop effect history at a Style FX coverage boundary."""
        self.active_events.clear()
        self.cooldown_until = {key: -1 for key in PHASE2_FRAME_EFFECT_ORDER}
        self.previous_scores = {key: 0.0 for key in PHASE2_FRAME_EFFECT_ORDER}
        self.previous_luma = None
        self.previous_rgb = None
        self.zone_previous_luma.clear()
        self.zone_previous_rgb.clear()
        self.organic_instability = 0.0
        self.organic_aftershock = 0.0
        self.organic_drive = 0.0
        self.previous_absolute_frame = None
        self.effect_wander = {key: 0.0 for key in PHASE2_FRAME_EFFECT_ORDER}
        self.ambient_until = {key: -1 for key in PHASE2_FRAME_EFFECT_ORDER}

    def _material_score(
        self,
        effect: str,
        analysis: _FrameMaterialAnalysis,
    ) -> tuple[float, str, tuple[tuple[str, float], ...]]:
        if effect == "pixel_sorting":
            edge = analysis.edge_activity
            texture = analysis.texture_activity
            score = edge * 0.58 + texture * 0.42
            trigger = "high_edges" if edge >= texture else "high_texture"
            metrics = (("edge", edge), ("texture", texture))
        elif effect == "databending":
            texture = analysis.texture_activity
            channels = analysis.channel_spread
            score = texture * 0.68 + channels * 0.32
            trigger = "data_texture" if texture >= channels else "channel_structure"
            metrics = (("texture", texture), ("channel_spread", channels))
        elif effect == "circuit_bending":
            edge = analysis.edge_activity
            motion = analysis.motion_activity
            bright = analysis.bright_fraction
            score = motion * 0.58 + bright * 0.24 + edge * 0.18
            trigger = "motion_change" if motion >= max(bright, edge) else (
                "bright_overload" if bright >= edge else "edge_energy"
            )
            metrics = (("motion", motion), ("bright_fraction", bright), ("edge", edge))
        elif effect == "hex_editing":
            edge = analysis.edge_activity
            texture = analysis.texture_activity
            score = edge * 0.76 + texture * 0.24
            trigger = "structural_edges"
            metrics = (("edge", edge), ("texture", texture))
        else:
            texture = analysis.texture_activity
            motion = analysis.motion_activity
            score = texture * 0.68 + motion * 0.32
            trigger = "binary_activity" if texture >= motion else "signal_change"
            metrics = (("texture", texture), ("motion", motion))
        return float(np.clip(score, 0.0, 1.0)), trigger, metrics

    @staticmethod
    def _material_threshold(effect: str) -> float:
        return {
            "pixel_sorting": 0.16,
            "databending": 0.13,
            "circuit_bending": 0.14,
            "hex_editing": 0.18,
            "random_noise_bw": 0.13,
        }[effect]

    def _start_event(
        self,
        effect: str,
        frame: int,
        trigger_type: str,
        score: float,
        metrics: tuple[tuple[str, float], ...],
        analysis: _FrameMaterialAnalysis,
        transition_absolute_frame: int | None = None,
    ) -> _FrameEffectEvent:
        salt = _PHASE2_EVENT_SALT ^ _phase2_effect_salt(effect)
        event_seed = _phase2_effect_seed(self.seed, salt, frame)
        rng = np.random.default_rng(event_seed)
        attack_seconds, sustain_seconds, decay_seconds = {
            "pixel_sorting": ((0.18, 0.48), (0.45, 1.35), (0.35, 0.95)),
            "databending": ((0.12, 0.36), (0.75, 1.75), (0.45, 1.05)),
            "circuit_bending": ((0.10, 0.30), (0.55, 1.55), (0.75, 1.80)),
            "hex_editing": ((0.06, 0.20), (0.25, 0.80), (0.22, 0.65)),
            "random_noise_bw": ((0.15, 0.42), (0.30, 1.00), (0.45, 1.20)),
        }[effect]
        duration_scale = (
            (0.72 + 0.78 * self.amount)
            * float(rng.uniform(0.68, 1.48))
            * (0.86 + 0.46 * self.organic_instability)
        )
        if trigger_type == "source_transition":
            duration_scale *= 1.15
        attack = max(1, int(round(self.fps * float(rng.uniform(*attack_seconds)) * duration_scale)))
        sustain = max(1, int(round(self.fps * float(rng.uniform(*sustain_seconds)) * duration_scale)))
        decay = max(1, int(round(self.fps * float(rng.uniform(*decay_seconds)) * duration_scale)))
        if float(rng.random()) < 0.08 + 0.34 * self.amount * self.organic_instability:
            sustain = max(1, int(round(sustain * float(rng.uniform(1.45, 2.65)))))
        elif float(rng.random()) < 0.18:
            sustain = max(1, int(round(sustain * float(rng.uniform(0.52, 0.84)))))
        peak = float(
            np.clip(
                0.43
                + 0.35 * self.amount
                + 0.23 * score
                + 0.13 * self.organic_instability,
                0.48,
                1.0,
            )
        )
        focus_x, focus_y = analysis.activity_focus()
        event = _FrameEffectEvent(
            effect=effect,
            trigger_frame=int(frame),
            trigger_type=trigger_type,
            attack_frames=attack,
            sustain_frames=sustain,
            decay_frames=decay,
            peak_strength=peak,
            event_seed=event_seed,
            focus_x=focus_x,
            focus_y=focus_y,
            transition_absolute_frame=transition_absolute_frame,
            organic_instability=round(self.organic_instability, 6),
            material_metrics=tuple((name, round(float(value), 6)) for name, value in metrics),
        )
        self.active_events[effect] = event
        cooldown_seconds = float(rng.uniform(0.08, 0.82)) * (
            1.18 - 0.62 * self.organic_instability
        )
        self.cooldown_until[effect] = event.end_frame + max(
            1,
            int(round(self.fps * cooldown_seconds)),
        )
        if self.record_events:
            self.recorded_events.append(event)
        return event

    def _control_for(
        self,
        effect: str,
        frame: int,
        event: _FrameEffectEvent | None,
    ) -> _FrameEffectControl:
        baseline = {
            "pixel_sorting": 0.10,
            "databending": 0.13,
            "circuit_bending": 0.08,
            "hex_editing": 0.045,
            "random_noise_bw": 0.13,
        }[effect] + self.amount * {
            "pixel_sorting": 0.13,
            "databending": 0.13,
            "circuit_bending": 0.15,
            "hex_editing": 0.085,
            "random_noise_bw": 0.14,
        }[effect]
        organic_affinity = {
            "pixel_sorting": 0.72,
            "databending": 0.92,
            "circuit_bending": 1.0,
            "hex_editing": 0.58,
            "random_noise_bw": 0.76,
        }[effect]
        organic_lift = (
            self.organic_instability
            * organic_affinity
            * (0.08 + 0.17 * self.amount)
            * (0.62 + 0.76 * self.effect_wander[effect])
        )
        baseline += (1.0 - baseline) * organic_lift
        if event is None:
            if frame >= self.ambient_until[effect]:
                ambient_rng = _phase2_effect_rng(
                    self.seed,
                    _PHASE2_ORGANIC_SALT ^ _phase2_effect_salt(effect),
                    frame,
                )
                self.ambient_seed[effect] = _phase2_effect_seed(
                    self.seed,
                    _PHASE2_EVENT_SALT ^ _phase2_effect_salt(effect),
                    frame,
                )
                dwell_seconds = float(ambient_rng.uniform(0.55, 2.85)) * (
                    1.25 - 0.58 * self.organic_instability
                )
                self.ambient_until[effect] = frame + max(
                    1,
                    int(round(self.fps * dwell_seconds)),
                )
            return _FrameEffectControl(
                strength=baseline,
                event_strength=0.0,
                event_seed=self.ambient_seed[effect],
                event_frame=0,
            )

        local = max(0, int(frame - event.trigger_frame))
        if local < event.attack_frames:
            phase = (local + 1) / max(1, event.attack_frames)
            envelope = math.sin(phase * math.pi / 2.0)
        elif local < event.attack_frames + event.sustain_frames:
            sustain_local = local - event.attack_frames
            sustain_phase = sustain_local / max(1, event.sustain_frames)
            envelope = {
                "pixel_sorting": 0.82 + 0.18 * math.sin(math.pi * sustain_phase),
                "databending": 0.94 + 0.06 * math.sin(math.tau * sustain_phase),
                "circuit_bending": 0.78 + 0.22 * math.sin(math.pi * sustain_phase),
                "hex_editing": 1.0,
                "random_noise_bw": 0.86 + 0.14 * math.sin(math.pi * sustain_phase),
            }[effect]
        else:
            decay_local = local - event.attack_frames - event.sustain_frames
            decay_phase = min(1.0, decay_local / max(1, event.decay_frames))
            decay_power = {
                "pixel_sorting": 1.25,
                "databending": 0.85,
                "circuit_bending": 0.62,
                "hex_editing": 1.8,
                "random_noise_bw": 1.05,
            }[effect]
            envelope = (1.0 - decay_phase) ** decay_power
        event_strength = float(np.clip(envelope * event.peak_strength, 0.0, 1.0))
        strength = baseline + (1.0 - baseline) * event_strength
        return _FrameEffectControl(
            strength=float(np.clip(strength, 0.0, 1.0)),
            event_strength=event_strength,
            event_seed=event.event_seed,
            event_frame=local,
            focus_x=event.focus_x,
            focus_y=event.focus_y,
            event=event,
        )

    def event_trace(self) -> list[dict[str, Any]]:
        return [
            {
                "effect": event.effect,
                "trigger_frame": event.trigger_frame,
                "trigger_type": event.trigger_type,
                "attack_frames": event.attack_frames,
                "sustain_frames": event.sustain_frames,
                "decay_frames": event.decay_frames,
                "end_frame": event.end_frame,
                "peak_strength": round(event.peak_strength, 6),
                "event_seed": event.event_seed,
                "focus": [round(event.focus_x, 6), round(event.focus_y, 6)],
                "transition_absolute_frame": event.transition_absolute_frame,
                "organic_instability": event.organic_instability,
                "material_metrics": dict(event.material_metrics),
            }
            for event in self.recorded_events
        ]

    def organic_state_trace(self) -> list[dict[str, float | int | bool]]:
        return list(self.recorded_organic_states)


class RenderError(RuntimeError):
    """Raised when the ANSI render cannot be completed."""


class SourceMediaError(RenderError):
    """Raised when a source file cannot be opened or decoded."""


class FramePipeTransportError(RenderError):
    """Raised when the raw ffmpeg frame-pipe transport fails."""


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


def build_style_fx_clean_intervals(
    duration: float,
    mode: object,
    manual_blocks: list[Any],
    random_percent: float,
    min_len: float,
    max_len: float,
    seed: int | None,
) -> list[Interval]:
    """Build deterministic half-open intervals where optional Style effects are off."""
    normalized = normalize_style_fx_coverage_mode(mode)
    if normalized == STYLE_FX_FULL:
        return []
    return build_bypass_intervals(
        duration,
        normalized,
        manual_blocks,
        random_percent,
        min_len,
        max_len,
        seed,
    )


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
    probe_started = time.perf_counter()
    timeline_segments, timeline_duration = _build_timeline(settings)
    audio_mode = _audio_mode(settings)
    configured_external_audio = _uses_external_audio(settings)

    audio_start = settings.audio_start
    audio_end = settings.audio_end
    external_audio_duration: float | None = None
    selected_audio_duration: float | None = None
    selected_audio_clip_duration: float | None = None
    if configured_external_audio:
        audio_duration = ffmpeg_utils.get_audio_duration(settings.audio_path)
        external_audio_duration = audio_duration
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
    if settings.random_clip_assembly:
        random_started = time.perf_counter()
        random_target_duration = (
            float(settings.max_video_length)
            if settings.max_video_length is not None
            else playback.output_duration
        )
        timeline_segments = _randomized_timeline_segments(
            timeline_segments,
            playback,
            random_target_duration,
            settings,
        )
        _emit_elapsed(log, "Random assembly stage", random_started)
        timeline_duration = sum(segment.duration for segment in timeline_segments)
        playback = PlaybackPlan(
            timeline_start=0.0,
            timeline_end=timeline_duration,
            source_duration=timeline_duration,
            output_duration=timeline_duration,
            speed_factor=1.0,
            loop_timeline=False,
        )
    _emit_elapsed(log, "Probe/planning stage", probe_started)
    full_output_duration = playback.output_duration
    configured_settings = settings
    configured_audio_start = audio_start
    configured_audio_end = audio_end
    render_duration = _render_window_duration(settings, full_output_duration)
    settings, audio_start, audio_end, external_audio = _preview_audio_execution_settings(
        settings,
        audio_start,
        audio_end,
        full_output_duration,
        render_duration,
    )
    _emit_long_media_warnings(
        timeline_segments,
        playback,
        external_audio_duration=external_audio_duration,
        selected_audio_clip_duration=selected_audio_clip_duration,
        settings=configured_settings,
        log=log,
    )
    source_count = len({segment.path for segment in timeline_segments})
    _emit(
        log,
        f"Timeline: {len(timeline_segments)} segment(s), {source_count} source file(s), "
        f"{ffmpeg_utils.format_duration(playback.source_duration)} selected.",
    )
    if settings.max_video_length is None:
        _emit(log, f"Max video length: auto/full selected timeline ({ffmpeg_utils.format_duration(full_output_duration)}).")
        if settings.random_clip_assembly:
            _emit(log, f"Random clip assembly: built {len(timeline_segments)} randomized segment(s) for the selected timeline duration.")
    elif settings.random_clip_assembly:
        _emit(log, f"Random clip assembly: built {len(timeline_segments)} randomized segment(s) for {ffmpeg_utils.format_duration(full_output_duration)}.")
    else:
        _emit(log, f"Max video length: output capped at {ffmpeg_utils.format_duration(full_output_duration)}.")
    if settings.style_begin_time <= 0:
        _emit(log, "Style begins at: 0:00 (first output frame).")
    elif settings.style_begin_time >= settings.output_time_offset + render_duration:
        _emit(
            log,
            f"Style begins at: {ffmpeg_utils.format_duration(settings.style_begin_time)}; "
            "this render window ends earlier, so its visual output remains clean.",
        )
    else:
        _emit(log, f"Style begins at: {ffmpeg_utils.format_duration(settings.style_begin_time)} on the rendered output timeline.")
    if settings.output_time_offset > 0:
        _emit(
            log,
            "Render window on output timeline: "
            f"{ffmpeg_utils.format_duration(settings.output_time_offset)} to "
            f"{ffmpeg_utils.format_duration(settings.output_time_offset + render_duration)}.",
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
    if configured_external_audio and configured_settings.audio_timeline_start > 0:
        _emit(log, f"External audio starts in video at {ffmpeg_utils.format_duration(configured_settings.audio_timeline_start)}.")
    if configured_external_audio and configured_settings.audio_timeline_end is not None:
        _emit(log, f"External audio stops in video at {ffmpeg_utils.format_duration(configured_settings.audio_timeline_end)}.")
    if configured_external_audio:
        trim_end = "auto" if configured_audio_end is None else ffmpeg_utils.format_duration(configured_audio_end)
        placement_end = "auto/output end" if configured_settings.audio_timeline_end is None else ffmpeg_utils.format_duration(configured_settings.audio_timeline_end)
        _emit(
            log,
            "Requested external audio source trim: "
            f"{ffmpeg_utils.format_duration(configured_audio_start)} to {trim_end}.",
        )
        _emit(
            log,
            "Requested external audio output placement: "
            f"video {ffmpeg_utils.format_duration(configured_settings.audio_timeline_start)} to {placement_end}.",
        )
    if configured_external_audio and settings.worky_music_mode:
        _emit(log, "worky_music_profile_v1: external audio becomes tiny mono broadcast texture.")
    if settings.match_timeline_to_audio and configured_external_audio:
        if playback.loop_timeline:
            _emit(log, f"Match to music: looping visual timeline to {ffmpeg_utils.format_duration(full_output_duration)}.")
        elif settings.match_timeline_mode == MATCH_TRIM:
            _emit(log, f"Match to music: trimming visual timeline to {ffmpeg_utils.format_duration(full_output_duration)}.")
        else:
            _emit(log, f"Match to music: visual speed factor {playback.speed_factor:.3f}x for {ffmpeg_utils.format_duration(full_output_duration)} output.")

    if configured_external_audio and not external_audio:
        _emit(log, "Preview window is outside the configured external-audio placement; rendering it without external samples.")

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

    style_fx_clean_intervals = build_style_fx_clean_intervals(
        duration=render_duration,
        mode=settings.style_fx_coverage_mode,
        manual_blocks=settings.style_fx_manual_blocks,
        random_percent=settings.style_fx_random_percent,
        min_len=settings.random_min_len,
        max_len=settings.random_max_len,
        seed=settings.style_fx_random_seed,
    )
    style_fx_clean_seconds = _interval_total(style_fx_clean_intervals)
    if style_fx_clean_intervals:
        _emit(
            log,
            f"Style FX Coverage: {len(style_fx_clean_intervals)} clean section(s), "
            f"{style_fx_clean_seconds / render_duration * 100:.1f}% of output.",
        )
    else:
        _emit(log, "Style FX Coverage: full effects.")

    _preflight_ffmpeg_decoded_stills(timeline_segments, settings.output_size, log)

    preset = get_preset(settings.preset_name)
    if preset.get("profile") == "public_access_v1":
        _emit(log, "PUBLIC ACCESS renderer: camcorder dub, RF noise, tracking wear; ANSI coverage controls still apply.")
    chunky_blocks = settings.chunky_blocks or preset.get("render_mode") == "chunky_blocks"
    layout = make_text_layout(settings.width_chars, settings.output_size, chunky_blocks=chunky_blocks)
    frame_count = max(1, math.ceil(render_duration * settings.fps))
    absolute_frame_offset = max(
        0,
        int(round(settings.output_time_offset * settings.fps)),
    )
    source_transition_targets = _datamosh_transition_targets(
        timeline_segments,
        playback,
        settings,
        frame_count,
        absolute_frame_offset,
    )
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

    frame_pipe_enabled, frame_pipe_state, frame_pipe_reason = _frame_pipe_transport_status(settings)
    if frame_pipe_enabled:
        _emit(log, f"Frame pipe transport: enabled ({frame_pipe_reason}).")
    else:
        _emit(log, f"Frame pipe transport: {frame_pipe_state} ({frame_pipe_reason}); using PNG frame staging.")

    with tempfile.TemporaryDirectory(prefix="wzrd_vid_render_") as temp_root:
        temp_root_path = Path(temp_root)
        silent_video = temp_root_path / "silent.mp4"

        if frame_pipe_enabled:
            try:
                datamosh_activity = _render_silent_video_with_pipe(
                    settings=settings,
                    preset=preset,
                    layout=layout,
                    timeline_segments=timeline_segments,
                    playback=playback,
                    render_duration=render_duration,
                    frame_count=frame_count,
                    source_transitions=source_transition_targets,
                    bypass_intervals=bypass_intervals,
                    style_fx_clean_intervals=style_fx_clean_intervals,
                    silent_video=silent_video,
                    target_bitrate=target_bitrate,
                    progress=progress,
                    log=log,
                )
            except FramePipeTransportError as exc:
                _emit(log, f"Frame pipe transport failed before audio muxing ({frame_pipe_reason}): {exc}")
                _emit(log, "Falling back to PNG frame staging.")
                try:
                    silent_video.unlink(missing_ok=True)
                except OSError:
                    pass
                _emit_progress(progress, 5)
                datamosh_activity = _render_silent_video_with_png_frames(
                    settings=settings,
                    preset=preset,
                    layout=layout,
                    timeline_segments=timeline_segments,
                    playback=playback,
                    render_duration=render_duration,
                    frame_count=frame_count,
                    source_transitions=source_transition_targets,
                    bypass_intervals=bypass_intervals,
                    style_fx_clean_intervals=style_fx_clean_intervals,
                    frames_dir=temp_root_path / "frames",
                    silent_video=silent_video,
                    target_bitrate=target_bitrate,
                    progress=progress,
                    log=log,
                )
        else:
            datamosh_activity = _render_silent_video_with_png_frames(
                settings=settings,
                preset=preset,
                layout=layout,
                timeline_segments=timeline_segments,
                playback=playback,
                render_duration=render_duration,
                frame_count=frame_count,
                source_transitions=source_transition_targets,
                bypass_intervals=bypass_intervals,
                style_fx_clean_intervals=style_fx_clean_intervals,
                frames_dir=temp_root_path / "frames",
                silent_video=silent_video,
                target_bitrate=target_bitrate,
                progress=progress,
                log=log,
            )

        datamosh_mode_keys = normalize_codec_layer_order(settings.codec_layer_order)
        enabled_datamosh_modes = tuple(
            key for key in datamosh_mode_keys if _effect_on(settings.effects, key)
        )
        if enabled_datamosh_modes:
            eligible_start_frame = _datamosh_eligible_start_frame(settings, frame_count)
            protected_intervals = _style_fx_clean_frame_intervals(
                style_fx_clean_intervals,
                settings.fps,
                frame_count,
            )
            if eligible_start_frame >= frame_count or _frames_fully_protected(
                eligible_start_frame,
                frame_count,
                protected_intervals,
            ):
                _emit(
                    log,
                    "DATAMOSHING: no Style-FX-eligible frame remains in this render window; "
                    "skipping the codec stage and leaving its silent visual output clean.",
                )
            else:
                _emit_progress(progress, 92)
                transition_targets = tuple(
                    target
                    for target in source_transition_targets
                    if target.frame > eligible_start_frame
                    and not _frame_in_intervals(target.frame, protected_intervals)
                    and not _frame_in_intervals(target.frame - 1, protected_intervals)
                )
                _emit(
                    log,
                    "DATAMOSH MODES: authentic MPEG-4 Part 2 prediction manipulation enabled "
                    f"for {', '.join(enabled_datamosh_modes)}; "
                    f"clean anchor at local frame {eligible_start_frame}, "
                    f"absolute frame {absolute_frame_offset + eligible_start_frame}; "
                    f"{len(transition_targets)} eligible source transition target(s).",
                )
                for target in transition_targets:
                    _emit(
                        log,
                        "DATAMOSHING transition target: "
                        f"local frame {target.frame}, absolute frame {target.absolute_frame}, "
                        f"{target.from_kind}->{target.to_kind}, {target.visual_transition}.",
                    )
                operations = _datamosh_operations(
                    settings,
                    enabled_datamosh_modes,
                    eligible_start_frame,
                    frame_count,
                    absolute_frame_offset,
                    transition_targets,
                    datamosh_activity,
                    protected_intervals,
                )
                datamosh_result = datamosh.apply_datamosh(
                    silent_video,
                    temp_root_path / "datamoshed_silent.mp4",
                    temp_root_path / "datamosh",
                    fps=settings.fps,
                    frame_count=frame_count,
                    effect_intensity=settings.effect_intensity,
                    weird_seed=(
                        settings.weird_seed
                        if settings.weird_seed is not None
                        else settings.random_seed
                    ),
                    eligible_start_frame=eligible_start_frame,
                    absolute_frame_offset=absolute_frame_offset,
                    loop_friendly=settings.loop_friendly,
                    loop_protected_tail_start=_preview_loop_protected_tail_start(
                        full_output_duration,
                        absolute_frame_offset,
                        frame_count,
                        settings.fps,
                    ),
                    video_crf=settings.video_crf,
                    video_bitrate=target_bitrate,
                    transitions=transition_targets,
                    operations=operations,
                    log=log,
                )
                if datamosh_result.applied:
                    silent_video = datamosh_result.output_path

        source_audio_path: Path | None = None
        fade_out_duration, fade_out_start = _preview_audio_fade(
            settings,
            full_output_duration,
            render_duration,
        )
        if source_audio:
            _emit(log, "Building selected source timeline audio.")
            source_audio_started = time.perf_counter()
            try:
                source_audio_path = ffmpeg_utils.build_timeline_audio(
                    timeline_segments,
                    playback.timeline_start + settings.output_time_offset,
                    render_duration,
                    temp_root_path / "source_audio.m4a",
                    temp_root_path / "source_audio_parts",
                    audio_bitrate=settings.audio_bitrate,
                    fade_out_duration=fade_out_duration,
                    fade_out_start=fade_out_start,
                    log=log,
                )
                _emit_elapsed(log, "Source audio stage", source_audio_started)
            except Exception as exc:  # noqa: BLE001 - random slices must fail soft for source audio.
                if not settings.random_clip_assembly:
                    raise
                _emit(log, f"Random clip assembly: source audio could not be preserved safely ({exc}). Continuing without source audio.")
                source_audio = False
                source_audio_path = None

        if external_audio and source_audio_path is not None and audio_mode == AUDIO_MIX and not settings.match_timeline_to_audio:
            _emit(log, "Mixing external audio with selected source audio.")
            _emit_progress(progress, 95)
            audio_mix_started = time.perf_counter()
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
            _emit_elapsed(log, "External/source audio mix stage", audio_mix_started)
            audio_mux_started = time.perf_counter()
            ffmpeg_utils.mux_audio(
                silent_video,
                mixed_audio,
                output_path,
                0.0,
                None,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=0.0,
                audio_label="Mixed audio",
                log=log,
            )
            _emit_elapsed(log, "Audio mux stage", audio_mux_started)
        elif external_audio:
            _emit(log, "Muxing selected external audio into final MP4.")
            _emit_progress(progress, 95)
            audio_mux_started = time.perf_counter()
            ffmpeg_utils.mux_audio(
                silent_video,
                settings.audio_path,
                output_path,
                audio_start,
                audio_end,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=fade_out_duration,
                fade_out_start=fade_out_start,
                audio_offset=settings.audio_timeline_start,
                audio_output_end=settings.audio_timeline_end,
                worky_music_mode=settings.worky_music_mode,
                audio_label="External audio",
                log=log,
            )
            _emit_elapsed(log, "External audio mux stage", audio_mux_started)
        elif source_audio_path is not None:
            _emit(log, "Muxing selected source timeline audio into final MP4.")
            _emit_progress(progress, 95)
            audio_mux_started = time.perf_counter()
            ffmpeg_utils.mux_audio(
                silent_video,
                source_audio_path,
                output_path,
                0.0,
                None,
                render_duration,
                audio_bitrate=settings.audio_bitrate,
                fade_out_duration=0.0,
                audio_label="Source audio",
                log=log,
            )
            _emit_elapsed(log, "Source audio mux stage", audio_mux_started)
        else:
            if source_audio:
                _emit(log, "No selected source audio found. Writing silent MP4.")
            else:
                _emit(log, "Writing silent MP4.")
            _emit_progress(progress, 95)
            silent_mux_started = time.perf_counter()
            ffmpeg_utils.write_silent_output(silent_video, output_path, log=log)
            _emit_elapsed(log, "Silent output stage", silent_mux_started)

        final_output_path = output_path
        if settings.optimize_enabled:
            optimized_path = _optimized_output_path(output_path, settings.optimize_target_mb)
            _emit(log, f"Optimizing final video to <= {settings.optimize_target_mb:.1f} MB.")
            _emit(log, f"Keeping unoptimized intermediate: {output_path}")
            _emit_progress(progress, 97)
            optimize_started = time.perf_counter()
            result = ffmpeg_utils.optimize_mp4_to_target(
                output_path,
                optimized_path,
                settings.optimize_target_mb,
                settings.audio_bitrate,
                log=log,
            )
            _emit_elapsed(log, "Optimization stage", optimize_started)
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


FRAME_PIPE_ENV_VAR = "WZRDVID_EXPERIMENTAL_FRAME_PIPE"
FRAME_PIPE_FORCE_PNG_ENV_VAR = "WZRDVID_FORCE_PNG_STAGING"
FRAME_PIPE_TRUTHY = {"1", "true", "yes", "on"}


def _frame_pipe_transport_status(settings: RenderSettings) -> tuple[bool, str, str]:
    width, height = settings.output_size
    if width <= 0 or height <= 0:
        return False, "unavailable", f"invalid output size {width}x{height}"
    if settings.force_legacy_png_staging:
        return False, "forced legacy PNG", "desktop developer setting is on"

    force_png_value = os.environ.get(FRAME_PIPE_FORCE_PNG_ENV_VAR)
    if force_png_value is not None and force_png_value.strip().lower() in FRAME_PIPE_TRUTHY:
        return False, "forced legacy PNG", f"{FRAME_PIPE_FORCE_PNG_ENV_VAR}={force_png_value!r}"

    if settings.experimental_frame_pipe:
        return True, "enabled", "legacy desktop developer pipe setting is on"

    raw_value = os.environ.get(FRAME_PIPE_ENV_VAR)
    if raw_value is not None and raw_value.strip().lower() in FRAME_PIPE_TRUTHY:
        return True, "enabled", f"{FRAME_PIPE_ENV_VAR}={raw_value!r}"
    return True, "enabled", "default desktop transport"


def _render_silent_video_with_png_frames(
    *,
    settings: RenderSettings,
    preset: dict[str, Any],
    layout: TextLayout,
    timeline_segments: list[TimelineSegment],
    playback: PlaybackPlan,
    render_duration: float,
    frame_count: int,
    source_transitions: tuple[datamosh.DatamoshTransition, ...],
    bypass_intervals: list[Interval],
    style_fx_clean_intervals: list[Interval],
    frames_dir: Path,
    silent_video: Path,
    target_bitrate: int | None,
    progress: ProgressCallback,
    log: LogCallback,
) -> tuple[datamosh.DatamoshActivity, ...]:
    frames_dir.mkdir()
    activity_samples: list[datamosh.DatamoshActivity] = []

    def write_png_frame(index: int, output_frame: Image.Image) -> None:
        output_frame.save(frames_dir / f"frame_{index:06d}.png", optimize=False)

    frame_stage_started = time.perf_counter()
    _render_frames(
        settings=settings,
        preset=preset,
        layout=layout,
        timeline_segments=timeline_segments,
        playback=playback,
        render_duration=render_duration,
        frame_count=frame_count,
        source_transitions=source_transitions,
        bypass_intervals=bypass_intervals,
        style_fx_clean_intervals=style_fx_clean_intervals,
        write_frame=write_png_frame,
        write_frame_label="PNG frame save",
        progress=progress,
        log=log,
        activity_samples=(
            activity_samples
            if any(_effect_on(settings.effects, key) for key in ("overflow", "skrrt", "scatter"))
            else None
        ),
    )
    _emit_elapsed(log, "Frame render stage", frame_stage_started)

    _emit(log, "Encoding rendered frames to MP4.")
    _emit_progress(progress, 90)
    encode_started = time.perf_counter()
    ffmpeg_utils.encode_frames_to_mp4(
        frames_dir / "frame_%06d.png",
        settings.fps,
        silent_video,
        log=log,
        crf=settings.video_crf,
        video_bitrate=target_bitrate,
    )
    _emit_elapsed(log, "Frame encode stage", encode_started)
    return tuple(activity_samples)


def _render_silent_video_with_pipe(
    *,
    settings: RenderSettings,
    preset: dict[str, Any],
    layout: TextLayout,
    timeline_segments: list[TimelineSegment],
    playback: PlaybackPlan,
    render_duration: float,
    frame_count: int,
    source_transitions: tuple[datamosh.DatamoshTransition, ...],
    bypass_intervals: list[Interval],
    style_fx_clean_intervals: list[Interval],
    silent_video: Path,
    target_bitrate: int | None,
    progress: ProgressCallback,
    log: LogCallback,
) -> tuple[datamosh.DatamoshActivity, ...]:
    width, height = settings.output_size
    frames_written = 0
    activity_samples: list[datamosh.DatamoshActivity] = []

    def stream_frames(stdin: Any) -> None:
        nonlocal frames_written

        def write_raw_frame(index: int, output_frame: Image.Image) -> None:
            nonlocal frames_written
            if output_frame.size != (width, height):
                raise RenderError(
                    "Frame pipe transport received a frame with "
                    f"{output_frame.size[0]}x{output_frame.size[1]} pixels; expected {width}x{height}."
                )
            rgb_frame = output_frame if output_frame.mode == "RGB" else output_frame.convert("RGB")
            stdin.write(rgb_frame.tobytes())
            frames_written = index + 1

        _render_frames(
            settings=settings,
            preset=preset,
            layout=layout,
            timeline_segments=timeline_segments,
            playback=playback,
            render_duration=render_duration,
            frame_count=frame_count,
            source_transitions=source_transitions,
            bypass_intervals=bypass_intervals,
            style_fx_clean_intervals=style_fx_clean_intervals,
            write_frame=write_raw_frame,
            write_frame_label="frame pipe write",
            progress=progress,
            log=log,
            activity_samples=(
                activity_samples
                if any(_effect_on(settings.effects, key) for key in ("overflow", "skrrt", "scatter"))
                else None
            ),
        )

    _emit(log, "Frame pipe transport: streaming rendered frames directly to ffmpeg.")
    pipe_started = time.perf_counter()
    try:
        ffmpeg_utils.encode_raw_rgb_frames_to_mp4(
            stream_frames,
            width,
            height,
            settings.fps,
            silent_video,
            log=log,
            crf=settings.video_crf,
            video_bitrate=target_bitrate,
        )
    except Exception as exc:  # noqa: BLE001 - classify before optional PNG fallback.
        source_error = _find_exception_in_chain(exc, SourceMediaError)
        if source_error is not None:
            if source_error is exc:
                raise
            raise source_error from exc
        render_error = _find_exception_in_chain(exc, RenderError)
        if render_error is not None:
            if render_error is exc:
                raise
            raise render_error from exc
        raise FramePipeTransportError(str(exc)) from exc
    elapsed = max(0.0, time.perf_counter() - pipe_started)
    throughput = frames_written / elapsed if elapsed > 0 else 0.0
    _emit(log, f"Frame pipe render/encode stage completed in {elapsed:.2f}s ({throughput:.2f} fps).")
    _emit_progress(progress, 90)
    return tuple(activity_samples)


def _emit_elapsed(log: LogCallback, label: str, started_at: float) -> None:
    elapsed = max(0.0, time.perf_counter() - started_at)
    _emit(log, f"{label} completed in {elapsed:.2f}s.")


def _iter_exception_chain(exc: BaseException) -> Iterable[BaseException]:
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        yield current
        seen.add(id(current))
        current = current.__cause__ or current.__context__


def _find_exception_in_chain(exc: BaseException, expected_type: type[BaseException]) -> BaseException | None:
    for current in _iter_exception_chain(exc):
        if isinstance(current, expected_type):
            return current
    return None


def _exception_text(exc: BaseException) -> str:
    parts: list[str] = []
    for current in _iter_exception_chain(exc):
        message = str(current).strip()
        if message:
            parts.append(message)
        for attr in ("stderr", "stdout", "output"):
            value = getattr(current, attr, None)
            if not value:
                continue
            if isinstance(value, bytes):
                value = value.decode(errors="replace")
            value = str(value).strip()
            if value:
                parts.append(value)
    deduped: list[str] = []
    for part in parts:
        if part not in deduped:
            deduped.append(part)
    return "\n".join(deduped)


def _brief_exception_detail(exc: BaseException, *, limit: int = 700) -> str:
    detail = _exception_text(exc).strip()
    if len(detail) <= limit:
        return detail
    return detail[-limit:]


def _is_access_denied_error(exc: BaseException) -> bool:
    if any(isinstance(current, PermissionError) for current in _iter_exception_chain(exc)):
        return True
    text = _exception_text(exc).lower()
    return any(
        marker in text
        for marker in (
            "operation not permitted",
            "permission denied",
            "errno 1",
            "eacces",
        )
    )


def _photo_source_error(path: str | Path, exc: BaseException) -> SourceMediaError:
    source = Path(path).expanduser()
    filename = source.name or str(source)
    detail = _brief_exception_detail(exc)
    suffix = source.suffix.lower()

    if suffix in HEIC_EXTENSIONS:
        if _is_access_denied_error(exc):
            message = (
                f"Cannot access HEIC/HEIF source before render: {filename}\n"
                f"Path: {source}\n"
                "macOS denied ffmpeg access to this file. If it is in Messages, Photos, "
                "or another privacy-protected location, copy or export the file to a normal "
                "folder such as Desktop or Pictures, remove the old item, and re-add that copy "
                "in WZRD.VID."
            )
        else:
            message = (
                f"HEIC/HEIF image support is not available for this source: {filename}\n"
                f"Path: {source}\n"
                "ffmpeg could not decode this HEIC/HEIF file. Install or update ffmpeg, "
                "or convert/export the photo to PNG/JPEG and add it again."
            )
    elif _is_access_denied_error(exc):
        message = (
            f"Cannot access photo source before render: {filename}\n"
            f"Path: {source}\n"
            "The file could not be opened. If it is in a privacy-protected location, copy or "
            "export it to a normal folder, remove the old item, and re-add that copy in WZRD.VID."
        )
    else:
        message = (
            f"Could not decode photo source before render: {filename}\n"
            f"Path: {source}\n"
            "Convert/export the photo to PNG/JPEG and add it again."
        )

    if detail:
        message = f"{message}\nDetails: {detail}"
    return SourceMediaError(message)


def _video_source_error(path: str | Path, message: str) -> SourceMediaError:
    source = Path(path).expanduser()
    filename = source.name or str(source)
    return SourceMediaError(
        f"Could not read video source before render: {filename}\n"
        f"Path: {source}\n"
        f"{message}"
    )


def _requires_ffmpeg_still_decode(path: str | Path) -> bool:
    return still_cache.is_heic_path(path)


def _preflight_ffmpeg_decoded_stills(
    timeline_segments: list[TimelineSegment],
    output_size: tuple[int, int],
    log: LogCallback,
) -> None:
    paths: list[str] = []
    seen: set[str] = set()
    for segment in timeline_segments:
        if segment.kind != "photo" or not _requires_ffmpeg_still_decode(segment.path):
            continue
        path = str(Path(segment.path).expanduser())
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)

    if not paths:
        return

    _emit(log, f"Preflight: validating {len(paths)} HEIC/HEIF still source(s) before frame render.")
    started = time.perf_counter()
    max_dimension = _still_proxy_max_dimension(output_size)
    for path in paths:
        try:
            still = still_cache.load_still_image(path, max_dimension=max_dimension, log=log)
            still.image.load()
        except Exception as exc:  # noqa: BLE001 - normalize source decode/access failures.
            raise _photo_source_error(path, exc) from exc
    _emit_elapsed(log, "HEIC/HEIF still preflight", started)


def _emit_long_media_warnings(
    timeline_segments: list[TimelineSegment],
    playback: PlaybackPlan,
    *,
    external_audio_duration: float | None,
    selected_audio_clip_duration: float | None,
    settings: RenderSettings,
    log: LogCallback,
) -> None:
    warned_video = False
    seen_paths: set[str] = set()
    for segment in timeline_segments:
        if segment.kind != "video" or segment.path in seen_paths:
            continue
        seen_paths.add(segment.path)
        try:
            source_duration = ffmpeg_utils.get_duration(segment.path)
        except Exception:  # noqa: BLE001 - warning-only path should never block render.
            continue
        if source_duration < LONG_MEDIA_WARNING_SECONDS:
            continue
        warned_video = True
        threshold = "over 1 hour" if source_duration >= VERY_LONG_MEDIA_WARNING_SECONDS else "over 30 minutes"
        _emit(
            log,
            "Long source warning: "
            f"{Path(segment.path).name} is {ffmpeg_utils.format_duration(source_duration)} ({threshold}). "
            "WZRD.VID samples the requested output frames, but long files can still make seeking and source-audio extraction slower.",
        )

    if warned_video and settings.random_clip_assembly:
        _emit(
            log,
            "Random clip assembly warning: random segments from long videos can trigger many seeks. "
            "If this render is slow, lower Max video length, FPS, or source count.",
        )

    if external_audio_duration is not None and external_audio_duration >= LONG_MEDIA_WARNING_SECONDS:
        selected = ffmpeg_utils.format_duration(selected_audio_clip_duration)
        threshold = "over 1 hour" if external_audio_duration >= VERY_LONG_MEDIA_WARNING_SECONDS else "over 30 minutes"
        _emit(
            log,
            "Long audio warning: "
            f"external audio is {ffmpeg_utils.format_duration(external_audio_duration)} ({threshold}); "
            f"selected audio clip is {selected}. WZRD.VID trims only the active output span before muxing/worky processing, "
            "but long containers can still add probe and seek time.",
        )

    if playback.source_duration >= LONG_MEDIA_WARNING_SECONDS and settings.max_video_length is not None:
        _emit(
            log,
            "Long timeline note: Max video length caps the output duration, not the cost of every source seek or selected source-audio extraction.",
        )


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
    if settings.max_video_length is not None and settings.max_video_length <= 0:
        raise ValueError("Max video length must be greater than 0.")
    if settings.style_begin_time < 0:
        raise ValueError("Style begins at must be non-negative.")
    if settings.output_time_offset < 0:
        raise ValueError("Output timeline offset must be non-negative.")
    if settings.preview_duration is not None and settings.preview_duration <= 0:
        raise ValueError("Preview duration must be greater than 0.")
    if settings.random_clip_assembly and settings.match_timeline_to_audio:
        raise ValueError("Random clip assembly cannot be used with Match video length to music.")
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
        style_fx_coverage_mode=normalize_style_fx_coverage_mode(
            settings.style_fx_coverage_mode
        ),
        style_fx_manual_blocks=(
            settings.style_fx_manual_blocks
            if isinstance(settings.style_fx_manual_blocks, list)
            else []
        ),
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


def _render_window_duration(settings: RenderSettings, full_output_duration: float) -> float:
    """Return the local render length after canonical full-output planning."""
    if settings.preview_duration is None:
        return full_output_duration
    available = full_output_duration - settings.output_time_offset
    if available <= 0.05:
        raise ValueError("Preview start is outside the planned output timeline.")
    return min(float(settings.preview_duration), available)


def _preview_audio_execution_settings(
    settings: RenderSettings,
    audio_start: float,
    audio_end: float | None,
    full_output_duration: float,
    render_duration: float,
) -> tuple[RenderSettings, float, float | None, bool]:
    """Rebase configured external audio only after global Preview planning is valid."""
    if settings.preview_duration is None or not _uses_external_audio(settings):
        return settings, audio_start, audio_end, _uses_external_audio(settings)

    resolved_audio_end = float(audio_start if audio_end is None else audio_end)
    source_duration = max(0.0, resolved_audio_end - audio_start)
    placement_start = max(0.0, float(settings.audio_timeline_start or 0.0))
    placement_end = placement_start + source_duration
    if settings.audio_timeline_end is not None:
        placement_end = min(placement_end, float(settings.audio_timeline_end))
    placement_end = min(full_output_duration, placement_end)

    window_start = settings.output_time_offset
    window_end = window_start + render_duration
    overlap_start = max(window_start, placement_start)
    overlap_end = min(window_end, placement_end)
    if overlap_end <= overlap_start:
        return (
            replace(
                settings,
                audio_path=None,
                audio_start=0.0,
                audio_end=None,
                audio_timeline_start=0.0,
                audio_timeline_end=None,
            ),
            0.0,
            None,
            False,
        )

    local_audio_start = audio_start + overlap_start - placement_start
    local_audio_end = min(
        resolved_audio_end,
        local_audio_start + overlap_end - overlap_start,
    )
    local_placement_start = overlap_start - window_start
    local_placement_end = local_placement_start + local_audio_end - local_audio_start
    return (
        replace(
            settings,
            audio_start=local_audio_start,
            audio_end=local_audio_end,
            audio_timeline_start=local_placement_start,
            audio_timeline_end=local_placement_end,
        ),
        local_audio_start,
        local_audio_end,
        True,
    )


def _preview_audio_fade(
    settings: RenderSettings,
    full_output_duration: float,
    render_duration: float,
) -> tuple[float, float | None]:
    """Return the canonical fade duration and its Preview-local start."""
    fade_duration = _audio_fade_duration(settings, full_output_duration)
    if fade_duration <= 0.05:
        return 0.0, None
    local_start = full_output_duration - fade_duration - settings.output_time_offset
    if local_start >= render_duration or local_start + fade_duration <= 0.0:
        return 0.0, None
    return fade_duration, local_start


def _preview_loop_protected_tail_start(
    full_output_duration: float,
    absolute_frame_offset: int,
    frame_count: int,
    fps: int,
) -> int:
    """Rebase the canonical Loop-protected frame tail into the render window."""
    full_frame_count = max(1, math.ceil(full_output_duration * fps))
    canonical_start = datamosh._loop_protected_tail_start(full_frame_count, fps)
    return max(0, min(frame_count, canonical_start - absolute_frame_offset))


def _randomized_timeline_segments(
    segments: list[TimelineSegment],
    playback: PlaybackPlan,
    target_duration: float,
    settings: RenderSettings,
) -> list[TimelineSegment]:
    candidates = _random_candidates_from_selection(segments, playback.timeline_start, playback.timeline_end)
    if not candidates:
        raise ValueError("Random clip assembly needs at least one usable timeline segment.")
    target_duration = max(0.001, float(target_duration))
    rng = random.Random(settings.random_seed if settings.random_seed is not None else 0)
    min_len = max(0.05, float(settings.random_min_len or RANDOM_CHUNK_MIN))
    max_len = max(min_len, float(settings.random_max_len or RANDOM_CHUNK_MAX))
    randomized: list[TimelineSegment] = []
    cursor = 0.0
    guard = 0
    while cursor < target_duration - 0.001 and guard < 2000:
        guard += 1
        candidate = candidates[rng.randrange(len(candidates))]
        remaining = target_duration - cursor
        usable_duration = max(0.001, float(candidate.duration))
        upper = min(max_len, remaining, usable_duration)
        if upper <= 0.001:
            continue
        lower = min(min_len, upper)
        chunk_duration = upper if upper <= lower else rng.uniform(lower, upper)
        chunk_duration = min(chunk_duration, remaining)
        if candidate.kind == "video":
            source_end = candidate.source_end if candidate.source_end is not None else candidate.source_start + usable_duration
            source_span = max(0.001, float(source_end) - candidate.source_start)
            source_max = max(0.0, source_span - chunk_duration)
            source_start = candidate.source_start + (rng.random() * source_max if source_max > 0 else 0.0)
            segment_source_end = min(float(source_end), source_start + chunk_duration)
        else:
            source_start = 0.0
            segment_source_end = chunk_duration
        randomized.append(
            TimelineSegment(
                path=candidate.path,
                kind=candidate.kind,
                timeline_start=cursor,
                duration=chunk_duration,
                source_start=source_start,
                source_end=segment_source_end,
                has_audio=candidate.has_audio,
                include_audio=candidate.include_audio,
            )
        )
        cursor += chunk_duration

    if not randomized:
        raise ValueError("Random clip assembly could not build a usable timeline.")
    final = randomized[-1]
    final_duration = max(0.001, target_duration - final.timeline_start)
    if abs(final_duration - final.duration) > 0.001:
        randomized[-1] = replace(
            final,
            duration=final_duration,
            source_end=(final.source_start + final_duration if final.kind == "video" else final_duration),
        )
    return randomized


def _random_candidates_from_selection(
    segments: list[TimelineSegment],
    timeline_start: float,
    timeline_end: float,
) -> list[TimelineSegment]:
    candidates: list[TimelineSegment] = []
    for segment in segments:
        overlap_start = max(float(timeline_start), segment.timeline_start)
        overlap_end = min(float(timeline_end), segment.timeline_end)
        duration = overlap_end - overlap_start
        if duration <= 0.001:
            continue
        if segment.kind == "video":
            local_start = overlap_start - segment.timeline_start
            source_start = segment.source_start + local_start
            source_end = source_start + duration
            if segment.source_end is not None:
                source_end = min(float(segment.source_end), source_end)
            duration = source_end - source_start
            if duration <= 0.001:
                continue
        else:
            source_start = 0.0
            source_end = duration
        candidates.append(
            TimelineSegment(
                path=segment.path,
                kind=segment.kind,
                timeline_start=0.0,
                duration=duration,
                source_start=source_start,
                source_end=source_end,
                has_audio=segment.has_audio,
                include_audio=segment.include_audio,
            )
        )
    return candidates


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

    if settings.max_video_length is not None:
        output_duration = min(output_duration, max(0.001, float(settings.max_video_length)))

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
        _load_photo_image(path, max_dimension=1024).load()
    except Exception as exc:  # noqa: BLE001 - Pillow support varies by local install.
        raise _photo_source_error(path, exc) from exc


def _load_photo_image(path: str, *, max_dimension: int | None = None, log: LogCallback = None) -> Image.Image:
    return still_cache.load_still_image(path, max_dimension=max_dimension, log=log).image


class _TimelineFrameSource:
    def __init__(self, segments: list[TimelineSegment], *, output_size: tuple[int, int], log: LogCallback) -> None:
        self.segments = segments
        self.captures: dict[str, cv2.VideoCapture] = {}
        self.photo_cache: dict[str, _PhotoFrameRecord] = {}
        self.last_frames: dict[str, np.ndarray] = {}
        self.still_proxy_max_dimension = _still_proxy_max_dimension(output_size)
        self.log = log
        self.photo_load_count = 0
        self.photo_cache_hits = 0
        self.photo_load_seconds = 0.0
        self.heic_count = 0
        self.heic_motion_frames = 0
        self.heic_motion_seconds = 0.0

    def frame_at(self, timeline_t: float) -> np.ndarray | Image.Image:
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
                raise _video_source_error(segment.path, "OpenCV could not open this video file.")
            self.captures[segment.path] = capture

        source_t = segment.source_start + local_t
        if segment.source_end is not None:
            source_t = min(source_t, max(segment.source_start, segment.source_end - 0.001))
        capture.set(cv2.CAP_PROP_POS_MSEC, source_t * 1000.0)
        ok, frame_bgr = capture.read()
        if not ok:
            last_frame = self.last_frames.get(segment.path)
            if last_frame is None:
                raise _video_source_error(segment.path, f"OpenCV could not decode a frame at {source_t:.3f}s.")
            frame_bgr = last_frame
        else:
            self.last_frames[segment.path] = frame_bgr
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    def _photo_frame(self, path: str, local_t: float = 0.0, duration: float = 3.0) -> np.ndarray | Image.Image:
        record = self.photo_cache.get(path)
        if record is None:
            started = time.perf_counter()
            try:
                still = still_cache.load_still_image(
                    path,
                    max_dimension=self.still_proxy_max_dimension,
                    log=self.log,
                )
            except Exception as exc:  # noqa: BLE001
                raise _photo_source_error(path, exc) from exc
            is_heic = Path(path).suffix.lower() in HEIC_EXTENSIONS
            record = _PhotoFrameRecord(
                image=still.image,
                array=np.asarray(still.image),
                is_heic=is_heic,
            )
            self.photo_cache[path] = record
            self.photo_load_count += 1
            self.photo_load_seconds += max(0.0, time.perf_counter() - started)
            if still.cache_hit:
                self.photo_cache_hits += 1
            if is_heic:
                self.heic_count += 1
            if still.downscaled and self.log:
                self.log(
                    f"Still proxy prepared: {Path(path).name} "
                    f"{still.source_size[0]}x{still.source_size[1]} -> "
                    f"{still.proxy_size[0]}x{still.proxy_size[1]}."
                )
        if record.is_heic:
            started = time.perf_counter()
            frame = _heic_motion_loop_frame(record.image, local_t, duration)
            self.heic_motion_frames += 1
            self.heic_motion_seconds += max(0.0, time.perf_counter() - started)
            return frame
        return record.array

    def still_timing_summary(self) -> str | None:
        if self.photo_load_count <= 0 and self.heic_motion_frames <= 0:
            return None
        return (
            f"Still/proxy load detail: loaded {self.photo_load_count} still(s), "
            f"{self.heic_count} HEIC/HEIF, {self.photo_cache_hits} cache hit(s), "
            f"load/decode/proxy {self.photo_load_seconds:.2f}s, "
            f"HEIC motion frame generation {self.heic_motion_frames} frame(s) in {self.heic_motion_seconds:.2f}s."
        )


def _still_proxy_max_dimension(output_size: tuple[int, int]) -> int:
    return max(960, min(3840, max(output_size) * 2))


def _heic_motion_loop_frame(image: Image.Image, local_t: float, duration: float) -> Image.Image:
    """Apply restrained automatic motion to HEIC/HEIF stills."""
    loop_duration = max(0.75, min(3.0, float(duration or 3.0)))
    phase = (float(local_t or 0.0) % loop_duration) / loop_duration
    wave = math.sin(phase * math.tau)
    zoom = 1.018 + 0.016 * (0.5 + 0.5 * math.sin(phase * math.tau - math.pi / 2.0))
    center_x = 0.5 + 0.018 * wave
    center_y = 0.5 + 0.012 * math.cos(phase * math.tau)
    moved = _zoom_crop(image, zoom=zoom, center_x=center_x, center_y=center_y)
    shimmer = 1.0 + 0.018 * math.sin(phase * math.tau * 2.0)
    moved = ImageEnhance.Contrast(moved).enhance(shimmer)
    return moved


def _render_frames(
    settings: RenderSettings,
    preset: dict[str, Any],
    layout: TextLayout,
    timeline_segments: list[TimelineSegment],
    playback: PlaybackPlan,
    render_duration: float,
    frame_count: int,
    source_transitions: tuple[datamosh.DatamoshTransition, ...],
    bypass_intervals: list[Interval],
    style_fx_clean_intervals: list[Interval],
    write_frame: FrameWriter,
    write_frame_label: str,
    progress: ProgressCallback,
    log: LogCallback,
    activity_samples: list[datamosh.DatamoshActivity] | None = None,
) -> None:
    source = _TimelineFrameSource(timeline_segments, output_size=settings.output_size, log=log)
    full_output_duration = playback.output_duration
    audio_hit_started = time.perf_counter()
    audio_hits = _audio_hit_levels(settings, render_duration, frame_count, log)
    if _effect_on(settings.effects, "audio_reactive") and _uses_external_audio(settings):
        _emit_elapsed(log, "Audio Reactive Hits analysis", audio_hit_started)
    framing_kwargs = _frame_framing_kwargs(settings)
    public_access_profile = preset.get("profile") == "public_access_v1"
    chunky_blocks = settings.chunky_blocks or preset.get("render_mode") == "chunky_blocks"
    glyph_masks = _glyph_masks_for_layout(layout, str(preset["charset"])) if not chunky_blocks else None
    if glyph_masks is not None:
        _emit(log, f"Text glyph mask cache: enabled for {len(glyph_masks)} ASCII glyph(s).")
    bypass_index = 0
    bypass_count = len(bypass_intervals)
    held_frame: np.ndarray | Image.Image | None = None
    hold_until = -1
    previous_output: Image.Image | None = None
    phase2_choreographer = _FrameEffectChoreographer(
        settings.effects,
        settings.effect_intensity,
        settings.fps,
        settings.weird_seed if settings.weird_seed is not None else settings.random_seed,
        source_transitions,
    )
    first_output: Image.Image | None = None
    last_source_t = _source_time_for_output(
        playback,
        max(0.0, full_output_duration - (1.0 / max(1, settings.fps))),
    )
    source_frame_seconds = 0.0
    normal_render_seconds = 0.0
    public_source_seconds = 0.0
    ansi_prepare_seconds = 0.0
    text_render_seconds = 0.0
    transition_seconds = 0.0
    write_seconds = 0.0
    timing_detail = _FrameTimingDetail()
    codec_previous_luma: np.ndarray | None = None
    style_fx_clean_index = 0
    style_fx_was_clean = False

    try:
        for index in range(frame_count):
            output_t = min(index / settings.fps, max(0.0, render_duration - 0.0001))
            absolute_output_t = settings.output_time_offset + output_t
            absolute_frame_index = _absolute_output_frame(settings, index)
            style_active = absolute_output_t >= settings.style_begin_time
            timeline_t = _source_time_for_output(playback, absolute_output_t)
            while (
                style_fx_clean_index < len(style_fx_clean_intervals)
                and output_t >= style_fx_clean_intervals[style_fx_clean_index][1]
            ):
                style_fx_clean_index += 1
            style_fx_clean = (
                style_active
                and style_fx_clean_index < len(style_fx_clean_intervals)
                and style_fx_clean_intervals[style_fx_clean_index][0]
                <= output_t
                < style_fx_clean_intervals[style_fx_clean_index][1]
            )
            if style_fx_clean != style_fx_was_clean:
                held_frame = None
                hold_until = -1
                codec_previous_luma = None
                phase2_choreographer.reset_temporal_state()
                style_fx_was_clean = style_fx_clean
            frame_effects = dict(settings.effects) if style_active and not style_fx_clean else {}
            hit_level = audio_hits[index] if index < len(audio_hits) else 0.0
            if frame_effects and hit_level > 0.01:
                frame_effects["_reactive_hit"] = True
                frame_effects["_hit_level"] = hit_level

            if style_active and _ending_freezes_source(
                settings,
                full_output_duration,
                absolute_output_t,
            ):
                source_started = time.perf_counter()
                frame_rgb = source.frame_at(last_source_t)
                source_frame_seconds += max(0.0, time.perf_counter() - source_started)
            elif style_active and _effect_on(frame_effects, "stutter_hold") and held_frame is not None and index < hold_until:
                frame_rgb = held_frame.copy()
            else:
                source_started = time.perf_counter()
                frame_rgb = source.frame_at(timeline_t)
                source_frame_seconds += max(0.0, time.perf_counter() - source_started)
                if (
                    style_active
                    and _effect_on(frame_effects, "stutter_hold")
                    and _starts_stutter_hold(absolute_frame_index, settings)
                ):
                    held_frame = frame_rgb.copy()
                    hold_until = index + _stutter_hold_length(
                        absolute_frame_index,
                        settings,
                    )

            if not style_active:
                normal_started = time.perf_counter()
                output_frame = fit_frame_to_output(frame_rgb, settings.output_size, **framing_kwargs)
                normal_render_seconds += max(0.0, time.perf_counter() - normal_started)
            else:
                while bypass_index < bypass_count and output_t >= bypass_intervals[bypass_index][1]:
                    bypass_index += 1
                is_normal_bypass = (
                    bypass_index < bypass_count
                    and bypass_intervals[bypass_index][0] <= output_t < bypass_intervals[bypass_index][1]
                )

                public_source: Image.Image | None = None
                if public_access_profile:
                    public_started = time.perf_counter()
                    public_source = prepare_public_access_source(
                        frame_rgb,
                        output_size=settings.output_size,
                        preset=preset,
                        effects=frame_effects,
                        intensity=settings.effect_intensity,
                        frame_index=index,
                        fps=settings.fps,
                        framing=framing_kwargs,
                        seed=settings.weird_seed or settings.random_seed,
                        timing=timing_detail,
                    )
                    public_source_seconds += max(0.0, time.perf_counter() - public_started)

                if is_normal_bypass:
                    if public_source is not None:
                        output_frame = public_source
                    else:
                        normal_started = time.perf_counter()
                        output_frame = render_normal_frame(
                            frame_rgb,
                            output_size=settings.output_size,
                            effects=frame_effects,
                            intensity=settings.effect_intensity,
                            frame_index=index,
                            fps=settings.fps,
                            framing=framing_kwargs,
                            timing=timing_detail,
                        )
                        normal_render_seconds += max(0.0, time.perf_counter() - normal_started)
                    phase2_material = output_frame
                else:
                    if public_source is not None:
                        ansi_source = public_source
                    else:
                        ansi_started = time.perf_counter()
                        ansi_source = prepare_ansi_source(
                            frame_rgb,
                            output_size=settings.output_size,
                            effects=frame_effects,
                            intensity=settings.effect_intensity,
                            frame_index=index,
                            fps=settings.fps,
                            framing=framing_kwargs,
                            timing=timing_detail,
                        )
                        ansi_prepare_seconds += max(0.0, time.perf_counter() - ansi_started)
                    phase2_material = ansi_source
                    text_started = time.perf_counter()
                    output_frame = render_text_art_frame(
                        np.asarray(ansi_source),
                        preset=preset,
                        layout=layout,
                        frame_index=index,
                        output_size=settings.output_size,
                        effects=frame_effects,
                        intensity=settings.effect_intensity,
                        fps=settings.fps,
                        chunky_blocks=chunky_blocks,
                        dither_mode=settings.dither_mode,
                        glyph_masks=glyph_masks,
                        timing=timing_detail,
                    )
                    text_render_seconds += max(0.0, time.perf_counter() - text_started)

                if activity_samples is not None and not style_fx_clean:
                    material_analysis = _FrameMaterialAnalysis(
                        rgb=_phase2_rgb_copy(phase2_material),
                        previous_luma=codec_previous_luma,
                    )
                    motion_x, motion_y, direction_confidence = (
                        material_analysis.motion_direction()
                        if _effect_on(settings.effects, "skrrt")
                        else (0.0, 0.0, 0.0)
                    )
                    scatter_regions = (
                        material_analysis.scatter_regions()
                        if _effect_on(settings.effects, "scatter")
                        else ()
                    )
                    activity_samples.append(
                        datamosh.DatamoshActivity(
                            frame=index,
                            absolute_frame=absolute_frame_index,
                            motion_activity=material_analysis.motion_activity,
                            motion_x=motion_x,
                            motion_y=motion_y,
                            direction_confidence=direction_confidence,
                            texture_activity=(
                                material_analysis.texture_activity
                                if scatter_regions
                                else 0.0
                            ),
                            edge_activity=(
                                material_analysis.edge_activity
                                if scatter_regions
                                else 0.0
                            ),
                            spatial_regions=scatter_regions,
                        )
                    )
                    codec_previous_luma = material_analysis.luma.copy()

                if first_output is None:
                    first_output = output_frame.copy()

                transition_started = time.perf_counter()
                output_frame = _apply_transition_effect(
                    output_frame,
                    previous_output,
                    output_t,
                    source_transitions,
                    settings,
                    absolute_frame_index,
                )
                output_frame = _apply_global_artifact_effects(
                    output_frame,
                    previous_output,
                    frame_effects,
                    settings.effect_intensity,
                    index,
                    settings.fps,
                    settings.weird_seed,
                    output_frame_index=absolute_frame_index,
                    phase2_choreographer=phase2_choreographer,
                    phase2_material=phase2_material,
                    zones=settings.zones,
                    effect_zone_assignments=settings.effect_zone_assignments,
                )
                output_frame = _apply_ending_effect(
                    output_frame,
                    first_output,
                    full_output_duration,
                    absolute_output_t,
                    settings,
                    absolute_frame_index,
                )
                if settings.loop_friendly and first_output is not None:
                    output_frame = _apply_loop_friendly(
                        output_frame,
                        first_output,
                        full_output_duration,
                        absolute_output_t,
                    )
                transition_seconds += max(0.0, time.perf_counter() - transition_started)

            write_started = time.perf_counter()
            write_frame(index, output_frame)
            write_seconds += max(0.0, time.perf_counter() - write_started)
            previous_output = output_frame.copy()

            if index % max(1, settings.fps) == 0 or index == frame_count - 1:
                _emit(log, f"Rendered frame {index + 1}/{frame_count}.")
            frame_progress = 5 + int(((index + 1) / frame_count) * 84)
            _emit_progress(progress, min(frame_progress, 89))
    finally:
        still_summary = source.still_timing_summary()
        if still_summary:
            _emit(log, still_summary)
        _emit(
            log,
            "Frame timing detail: "
            f"source/still {source_frame_seconds:.2f}s, "
            f"normal {normal_render_seconds:.2f}s, "
            f"public source {public_source_seconds:.2f}s, "
            f"ANSI prep {ansi_prepare_seconds:.2f}s, "
            f"text render {text_render_seconds:.2f}s, "
            f"transitions/effects/endings {transition_seconds:.2f}s, "
            f"{write_frame_label} {write_seconds:.2f}s.",
        )
        _emit(
            log,
            "Frame timing hot paths: "
            f"resize/framing {timing_detail.resize_framing_seconds:.2f}s, "
            f"ANSI prep effects {timing_detail.ansi_effect_seconds:.2f}s, "
            f"text sample/luma {timing_detail.text_prepare_seconds:.2f}s, "
            f"ImageDraw.text/glyph draw {timing_detail.image_draw_text_seconds:.2f}s, "
            f"ANSI output effects {timing_detail.ansi_output_effect_seconds:.2f}s.",
        )
        source.close()


def _absolute_output_frame(settings: RenderSettings, local_frame: int) -> int:
    """Map a render-window frame to its canonical full-output clock."""
    return max(
        0,
        int(round(settings.output_time_offset * settings.fps)) + int(local_frame),
    )


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


def _datamosh_operations(
    settings: RenderSettings,
    enabled_modes: tuple[str, ...],
    eligible_start_frame: int,
    frame_count: int,
    absolute_frame_offset: int,
    transitions: tuple[datamosh.DatamoshTransition, ...],
    activity: tuple[datamosh.DatamoshActivity, ...],
    protected_intervals: tuple[tuple[int, int], ...] = (),
) -> tuple[datamosh.DatamoshOperation, ...]:
    """Build an explicit deterministic operation spec for the shared codec pass."""
    seed = settings.weird_seed if settings.weird_seed is not None else settings.random_seed
    mode_salts = {
        "datamoshing": datamosh.DATAMOSH_SEED_SALT,
        "overflow": datamosh.OVERFLOW_SEED_SALT,
        "skrrt": datamosh.SKRRT_SEED_SALT,
        "scatter": datamosh.SCATTER_SEED_SALT,
        "bleed": datamosh.BLEED_SEED_SALT,
    }
    ordered_modes = tuple(
        mode
        for mode in normalize_codec_layer_order(settings.codec_layer_order)
        if mode in enabled_modes
    )
    normalized_zones, normalized_assignments, _ = normalize_zone_state(
        list(settings.zones),
        settings.effect_zone_assignments,
    )
    zone_by_id = {zone.id: zone for zone in normalized_zones}
    skrrt_zone_id = normalized_assignments.get(datamosh.DATAMOSH_MODE_SKRRT)
    skrrt_zone_box = (
        rasterize_zone(zone_by_id[skrrt_zone_id], settings.output_size)
        if skrrt_zone_id is not None
        else None
    )
    return tuple(
        datamosh.DatamoshOperation(
            mode=mode,
            enabled=True,
            intensity=settings.effect_intensity,
            seed=seed,
            salt=salt,
            order=layer_index * 10,
            start_frame=eligible_start_frame,
            end_frame=frame_count,
            absolute_frame_offset=absolute_frame_offset,
            transitions=transitions,
            protected_intervals=protected_intervals,
            activity=activity if mode in {"overflow", "skrrt", "scatter"} else (),
            parameters=(
                ("fps", settings.fps),
                ("width", settings.output_size[0]),
                ("height", settings.output_size[1]),
            ),
            zone_box=(
                skrrt_zone_box
                if mode == datamosh.DATAMOSH_MODE_SKRRT
                else None
            ),
        )
        for layer_index, mode in enumerate(ordered_modes, start=1)
        for salt in (mode_salts[mode],)
    )


def _style_fx_clean_frame_intervals(
    intervals: list[Interval],
    fps: int,
    frame_count: int,
) -> tuple[tuple[int, int], ...]:
    """Map half-open output-time coverage to the rendered frame indices it contains."""
    mapped: list[tuple[int, int]] = []
    for start, end in intervals:
        start_frame = max(0, min(frame_count, int(math.ceil(start * fps - 1e-9))))
        end_frame = max(start_frame, min(frame_count, int(math.ceil(end * fps - 1e-9))))
        if end_frame > start_frame:
            mapped.append((start_frame, end_frame))
    return tuple(mapped)


def _frames_fully_protected(
    start_frame: int,
    end_frame: int,
    intervals: tuple[tuple[int, int], ...],
) -> bool:
    cursor = start_frame
    for protected_start, protected_end in intervals:
        if protected_end <= cursor:
            continue
        if protected_start > cursor:
            return False
        cursor = max(cursor, protected_end)
        if cursor >= end_frame:
            return True
    return cursor >= end_frame


def _frame_in_intervals(
    frame: int,
    intervals: tuple[tuple[int, int], ...],
) -> bool:
    return any(start <= frame < end for start, end in intervals)


def _datamosh_transition_targets(
    segments: list[TimelineSegment],
    playback: PlaybackPlan,
    settings: RenderSettings,
    frame_count: int,
    absolute_frame_offset: int,
) -> tuple[datamosh.DatamoshTransition, ...]:
    """Map canonical source cuts into a full render or rebased Preview window."""
    source_boundaries = [
        (
            segment.timeline_start - playback.timeline_start,
            segments[index - 1].kind,
            segment.kind,
        )
        for index, segment in enumerate(segments[1:], start=1)
        if 0.0 < segment.timeline_start - playback.timeline_start < playback.source_duration
    ]
    mapped: list[tuple[float, str, str]] = []
    if playback.loop_timeline:
        loop = max(0.001, playback.source_duration)
        first_kind = _segment_kind_at(segments, playback.timeline_start)
        last_kind = _segment_kind_at(segments, max(playback.timeline_start, playback.timeline_end - 0.001))
        cycle = 0
        while cycle * loop < playback.output_duration:
            cycle_start = cycle * loop
            if cycle > 0:
                mapped.append((cycle_start, last_kind, first_kind))
            for boundary, from_kind, to_kind in source_boundaries:
                output_boundary = cycle_start + boundary
                if 0.0 < output_boundary < playback.output_duration:
                    mapped.append((output_boundary, from_kind, to_kind))
            cycle += 1
    else:
        mapped.extend(
            (
                boundary / max(0.0001, playback.speed_factor),
                from_kind,
                to_kind,
            )
            for boundary, from_kind, to_kind in source_boundaries
        )

    targets: list[datamosh.DatamoshTransition] = []
    seen_frames: set[int] = set()
    window_start_frame = max(0, int(absolute_frame_offset))
    window_end_frame = window_start_frame + frame_count
    full_frame_count = max(1, math.ceil(playback.output_duration * settings.fps))
    for transition_index, (output_t, from_kind, to_kind) in enumerate(sorted(mapped)):
        absolute_frame = int(math.ceil(output_t * settings.fps - 1e-9))
        if (
            absolute_frame <= 0
            or absolute_frame >= full_frame_count
            or absolute_frame < window_start_frame
            or absolute_frame >= window_end_frame
            or absolute_frame in seen_frames
        ):
            continue
        seen_frames.add(absolute_frame)
        targets.append(
            datamosh.DatamoshTransition(
                frame=absolute_frame - window_start_frame,
                absolute_frame=absolute_frame,
                from_kind=from_kind,
                to_kind=to_kind,
                visual_transition=_transition_name(settings, transition_index),
                transition_ordinal=transition_index,
                output_time=output_t,
            )
        )
    return tuple(targets)


def _segment_kind_at(segments: list[TimelineSegment], timeline_t: float) -> str:
    for segment in reversed(segments):
        if segment.timeline_start <= timeline_t < segment.timeline_end:
            return segment.kind
    return segments[0].kind if segments else "video"


def _transition_name(settings: RenderSettings, index: int) -> str:
    mode = settings.transition_mode or "Hard Cut"
    if mode == "None":
        mode = "Hard Cut"
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
    transitions: tuple[datamosh.DatamoshTransition, ...],
    settings: RenderSettings,
    frame_index: int,
) -> Image.Image:
    if settings.transition_mode in {"Hard Cut", "None"} or not transitions:
        return image
    duration = 0.10 + 0.34 * max(0.0, min(2.0, settings.transition_intensity))
    active_target: datamosh.DatamoshTransition | None = None
    progress = 0.0
    for target in transitions:
        boundary = (
            target.frame / max(1, settings.fps)
            if target.output_time is None
            else target.output_time - settings.output_time_offset
        )
        if boundary <= output_t < boundary + duration:
            active_target = target
            progress = (output_t - boundary) / duration
            break
    if active_target is None:
        return image
    transition_index = active_target.transition_ordinal
    mode = active_target.visual_transition
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
    output_frame_index: int | None = None,
    phase2_previous: Image.Image | None = None,
    phase2_choreographer: _FrameEffectChoreographer | None = None,
    phase2_material: np.ndarray | Image.Image | None = None,
    zones: tuple[ZoneDefinition, ...] = (),
    effect_zone_assignments: dict[str, str] | None = None,
) -> Image.Image:
    if _effect_on(effects, "motion_melt") and previous is not None:
        image = _apply_motion_melt(image, previous, frame_index, intensity)
    if _effect_on(effects, "terminal_scroll"):
        image = _apply_terminal_scroll(image, frame_index, intensity)
    if _effect_on(effects, "tape_damage"):
        image = _apply_tape_damage(image, frame_index, intensity, seed)
    if _effect_on(effects, "mosaic_collapse"):
        image = _apply_mosaic_collapse(image, frame_index, fps, intensity, seed)
    return _apply_phase2_frame_effects(
        image,
        effects,
        intensity,
        frame_index if output_frame_index is None else output_frame_index,
        fps,
        seed,
        previous=phase2_previous,
        choreographer=phase2_choreographer,
        material=phase2_material,
        zones=zones,
        effect_zone_assignments=effect_zone_assignments,
    )


def _phase2_effect_salt(effect: str) -> int:
    return {
        "pixel_sorting": _PIXEL_SORTING_SALT,
        "databending": _DATABENDING_SALT,
        "circuit_bending": _CIRCUIT_BENDING_SALT,
        "hex_editing": _HEX_EDITING_SALT,
        "random_noise_bw": _RANDOM_NOISE_BW_SALT,
    }[effect]


def _phase2_effect_seed(seed: int | None, salt: int, frame_index: int) -> int:
    mask = (1 << 64) - 1
    mixed = (int(seed or 0) & mask) ^ (int(salt) & mask)
    mixed ^= ((int(frame_index) & mask) + 0x9E3779B97F4A7C15) & mask
    mixed = (mixed * 0xBF58476D1CE4E5B9) & mask
    mixed ^= mixed >> 30
    mixed = (mixed * 0x94D049BB133111EB) & mask
    mixed ^= mixed >> 31
    return mixed


def _phase2_effect_rng(seed: int | None, salt: int, frame_index: int) -> np.random.Generator:
    """Return an independent deterministic RNG stream for one frame effect."""
    return np.random.default_rng(_phase2_effect_seed(seed, salt, frame_index))


def _phase2_rgb_copy(frame: np.ndarray | Image.Image) -> np.ndarray:
    if isinstance(frame, Image.Image):
        arr = np.array(frame.convert("RGB"), dtype=np.uint8, copy=True)
    else:
        arr = np.array(frame, dtype=np.uint8, copy=True)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("Frame effects require an RGB frame with shape (height, width, 3).")
    return np.ascontiguousarray(arr, dtype=np.uint8)


def _phase2_effect_amount(intensity: float) -> float:
    return max(0.0, min(1.0, float(intensity) / 2.0))


def _phase2_luma(source: np.ndarray) -> np.ndarray:
    return (
        source[:, :, 0].astype(np.float32) * 0.2126
        + source[:, :, 1].astype(np.float32) * 0.7152
        + source[:, :, 2].astype(np.float32) * 0.0722
    )


def _normalized_signal(values: np.ndarray) -> np.ndarray:
    signal = np.asarray(values, dtype=np.float32)
    low = float(np.min(signal))
    high = float(np.max(signal))
    if high - low < 1e-6:
        return np.zeros_like(signal, dtype=np.float32)
    return (signal - low) / (high - low)


def _sort_content_line_runs(
    line: np.ndarray,
    luma: np.ndarray,
    edge: np.ndarray,
    amount: float,
    descending: bool,
) -> None:
    length = int(line.shape[0])
    if length < 5 or float(np.ptp(luma)) < 1.0:
        return
    lower = float(np.percentile(luma, max(2.0, 32.0 - 24.0 * amount)))
    upper = float(np.percentile(luma, min(98.0, 68.0 + 24.0 * amount)))
    eligible = (luma >= lower) & (luma <= upper)
    positive_edges = edge[edge > 0.5]
    if positive_edges.size:
        edge_cut = float(np.percentile(positive_edges, 72.0 + 27.0 * amount))
        eligible[1:] &= edge[1:] <= edge_cut
    padded = np.pad(eligible.astype(np.int8), (1, 1))
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    min_run = max(4, int(length * (0.008 + 0.012 * (1.0 - amount))))
    for start, end in zip(starts, ends):
        if end - start < min_run:
            continue
        order = np.argsort(luma[start:end], kind="stable")
        if descending:
            order = order[::-1]
        line[start:end] = line[start:end][order]


def _apply_pixel_sorting_frame(
    frame: np.ndarray | Image.Image,
    intensity: float,
    frame_index: int,
    seed: int | None,
    analysis: _FrameMaterialAnalysis | None = None,
    control: _FrameEffectControl | None = None,
) -> np.ndarray:
    arr = _phase2_rgb_copy(frame)
    amount = _phase2_effect_amount(intensity)
    height, width = arr.shape[:2]
    if amount <= 0.0 or height < 1 or width < 4:
        return arr
    rng = (
        np.random.default_rng(control.event_seed)
        if control is not None
        else _phase2_effect_rng(seed, _PIXEL_SORTING_SALT, frame_index)
    )
    luma = analysis.luma if analysis is not None and analysis.luma.shape == arr.shape[:2] else _phase2_luma(arr)
    if analysis is not None and analysis.luma.shape == arr.shape[:2]:
        edge_x, edge_y = analysis.directional_edges()
    else:
        edge_x = np.abs(cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3))
        edge_y = np.abs(cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3))
    row_energy = edge_x.mean(axis=1) + luma.std(axis=1) * 0.55
    if control is not None and control.focus_y is not None and control.event_strength > 0.0:
        row_positions = np.linspace(0.0, 1.0, height, dtype=np.float32)
        focus_weight = np.exp(-((row_positions - float(control.focus_y)) ** 2) / 0.035)
        row_energy *= 1.0 + focus_weight * (0.35 + control.event_strength)
    row_energy += rng.random(height, dtype=np.float32) * max(0.001, float(row_energy.max())) * 0.025
    row_count = min(height, max(1, int(round(height * (0.008 + 0.27 * amount)))))
    rows = np.argpartition(row_energy, -row_count)[-row_count:]
    for row in np.sort(rows):
        _sort_content_line_runs(
            arr[int(row)],
            luma[int(row)],
            edge_x[int(row)],
            amount,
            bool((int(row) + frame_index + int(control.event_seed if control else seed or 0)) & 1),
        )
    if height >= 4 and amount >= 0.50:
        column_energy = edge_y.mean(axis=0) + luma.std(axis=0) * 0.45
        column_count = min(width, max(1, int(round(width * (0.004 + 0.026 * amount)))))
        columns = np.argpartition(column_energy, -column_count)[-column_count:]
        for column in np.sort(columns):
            _sort_content_line_runs(
                arr[:, int(column), :],
                luma[:, int(column)],
                edge_y[:, int(column)],
                amount * 0.85,
                bool((int(column) + frame_index) & 1),
            )
    return arr


def _apply_databending_frame(
    frame: np.ndarray | Image.Image,
    intensity: float,
    frame_index: int,
    fps: int,
    seed: int | None,
    analysis: _FrameMaterialAnalysis | None = None,
    control: _FrameEffectControl | None = None,
) -> np.ndarray:
    source = _phase2_rgb_copy(frame)
    amount = _phase2_effect_amount(intensity)
    height, width = source.shape[:2]
    if amount <= 0.0 or height < 1 or width < 2:
        return source
    params = (
        np.random.default_rng(control.event_seed)
        if control is not None
        else _phase2_effect_rng(seed, _DATABENDING_SALT, frame_index // max(1, fps // 3))
    )
    luma = analysis.luma if analysis is not None and analysis.luma.shape == source.shape[:2] else _phase2_luma(source)
    row_mean = luma.mean(axis=1)
    row_texture = luma.std(axis=1)
    row_signature = np.floor(row_mean * 0.37 + row_texture * 0.63).astype(np.int64)
    x = np.arange(width, dtype=np.int64)[None, :]
    row_index = np.arange(height, dtype=np.int64)[:, None]
    max_shift = max(2, int(width * (0.012 + 0.08 * amount)))
    temporal_frame = control.event_frame if control is not None else frame_index
    temporal_word = int(temporal_frame // max(1, fps // 4))
    seed_word = int(params.integers(0, 1 << 30))
    row_offsets = ((row_signature ^ temporal_word ^ seed_word) % (max_shift * 2 + 1)) - max_shift
    texture_gate = float(np.percentile(row_texture, max(15.0, 68.0 - 38.0 * amount)))
    active_rows = row_texture >= texture_gate
    active_rows |= np.abs(row_mean - float(luma.mean())) > (58.0 - 32.0 * amount)
    row_offsets = np.where(active_rows, row_offsets, 0)
    out = np.empty_like(source)
    channel_source = analysis.rgb if analysis is not None and analysis.rgb.shape == source.shape else source
    channel_order = np.argsort(channel_source.reshape(-1, 3).mean(axis=0))
    channel_offsets = (channel_order.astype(np.int64) - 1) * max(1, max_shift // 3)
    channel_offsets += params.integers(-max(1, max_shift // 5), max(2, max_shift // 5 + 1), size=3)
    for channel in range(3):
        active_channel_offset = np.where(active_rows, int(channel_offsets[channel]), 0)
        indices = (x - row_offsets[:, None] - active_channel_offset[:, None]) % width
        out[:, :, channel] = source[row_index, indices, channel]

    block_w = max(8, width // 18)
    block_h = max(4, height // 14)
    coarse_size = (max(1, math.ceil(width / block_w)), max(1, math.ceil(height / block_h)))
    coarse_luma = cv2.resize(luma, coarse_size, interpolation=cv2.INTER_AREA)
    if analysis is not None and analysis.luma.shape == source.shape[:2]:
        edge_x, _ = analysis.directional_edges()
    else:
        edge_x = np.abs(cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3))
    coarse_edge = cv2.resize(edge_x, coarse_size, interpolation=cv2.INTER_AREA)
    block_gate = (coarse_luma > np.percentile(coarse_luma, 58.0 - 22.0 * amount))
    block_gate &= coarse_edge > np.percentile(coarse_edge, max(12.0, 62.0 - 35.0 * amount))
    mask = cv2.resize(block_gate.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)
    rolled = np.roll(source, max(1, max_shift // 2), axis=1)
    reinterpret = np.stack((rolled[:, :, 1], source[:, :, 2], rolled[:, :, 0]), axis=2)
    out[mask] = reinterpret[mask]

    band_count = 1 + int(round(amount * 3.0))
    ranked_rows = np.argsort(row_texture + np.abs(np.diff(row_mean, prepend=row_mean[0])))[::-1]
    used: list[int] = []
    for center in ranked_rows:
        if any(abs(int(center) - prior) < block_h for prior in used):
            continue
        used.append(int(center))
        top = max(0, int(center) - block_h // 2)
        bottom = min(height, top + block_h)
        stride = 2 if amount > 0.65 and (len(used) + temporal_word) % 2 else 1
        offset = int(row_offsets[int(center)])
        indices = (np.arange(width, dtype=np.int64) * stride + offset) % width
        out[top:bottom, :, channel_order[0]] = source[top:bottom, indices, channel_order[-1]]
        if len(used) >= band_count:
            break
    return out


def _apply_circuit_bending_frame(
    frame: np.ndarray | Image.Image,
    intensity: float,
    frame_index: int,
    fps: int,
    seed: int | None,
    previous: np.ndarray | Image.Image | None = None,
    analysis: _FrameMaterialAnalysis | None = None,
    control: _FrameEffectControl | None = None,
) -> np.ndarray:
    source = _phase2_rgb_copy(frame)
    amount = _phase2_effect_amount(intensity)
    height, width = source.shape[:2]
    if amount <= 0.0 or height < 1 or width < 2:
        return source
    params = (
        np.random.default_rng(control.event_seed)
        if control is not None
        else _phase2_effect_rng(seed, _CIRCUIT_BENDING_SALT, 0)
    )
    temporal_frame = control.event_frame if control is not None else frame_index
    phase = temporal_frame / max(1.0, float(fps))
    base_phase = float(params.uniform(0.0, math.tau))
    oscillator_speed = float(params.uniform(1.0, 2.1))
    line_frequency = float(params.uniform(0.055, 0.13))
    luma = analysis.luma if analysis is not None and analysis.luma.shape == source.shape[:2] else _phase2_luma(source)
    edge = (
        analysis.edge_magnitude
        if analysis is not None and analysis.luma.shape == source.shape[:2]
        else cv2.magnitude(
            cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3),
            cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3),
        )
    )
    edge_response = _normalized_signal(cv2.GaussianBlur(edge, (0, 0), 1.2))
    motion_response = np.zeros_like(luma, dtype=np.float32)
    previous_arr: np.ndarray | None = None
    if analysis is not None and analysis.previous_luma is not None:
        motion_response = analysis.motion
    if previous is not None:
        if isinstance(previous, Image.Image):
            previous_arr = _phase2_rgb_copy(previous.resize((width, height)))
        else:
            previous_arr = _phase2_rgb_copy(previous)
            if previous_arr.shape[:2] != (height, width):
                previous_arr = cv2.resize(previous_arr, (width, height), interpolation=cv2.INTER_AREA)
        if analysis is None:
            motion_response = _normalized_signal(np.abs(luma - _phase2_luma(previous_arr)))
    bright_response = np.clip((luma - 150.0) / 105.0, 0.0, 1.0)
    response = np.clip(edge_response * 0.52 + motion_response * 0.32 + bright_response * 0.16, 0.0, 1.0)
    row_response = _normalized_signal(response.mean(axis=1) + response.max(axis=1) * 0.35)
    rows = np.arange(height, dtype=np.float32)
    amplitude = 1.0 + amount * max(4.0, width * 0.035)
    sync_shift = np.rint(
        (
            np.sin(rows * line_frequency + base_phase + phase * oscillator_speed)
            + np.sign(np.sin(rows * line_frequency * 0.31 - phase * 0.83)) * 0.24
        )
        * amplitude
        * (0.10 + row_response * 0.90)
    ).astype(np.int64)
    x = np.arange(width, dtype=np.int64)[None, :]
    row_index = np.arange(height, dtype=np.int64)[:, None]
    indices = (x - sync_shift[:, None]) % width
    out = source[row_index, indices, :].copy()

    energy_centroid = float((row_response * rows).sum() / max(1e-6, row_response.sum()))
    roll_amplitude = max(1, int(height * (0.004 + 0.026 * amount)))
    vertical_roll = int(round(((energy_centroid / max(1, height - 1)) - 0.5) * 2.0 * roll_amplitude))
    if amount > 0.35:
        out = np.roll(out, vertical_roll, axis=0)
    chroma_jump = max(1, int(round((1.0 + width * 0.018 * amount) * math.sin(base_phase + phase * 1.31))))
    chroma_gate = response > np.percentile(response, max(30.0, 84.0 - 42.0 * amount))
    shifted_red = np.roll(out[:, :, 0], chroma_jump, axis=1)
    shifted_blue = np.roll(out[:, :, 2], -chroma_jump, axis=1)
    out[:, :, 0] = np.where(chroma_gate, shifted_red, out[:, :, 0])
    out[:, :, 2] = np.where(chroma_gate, shifted_blue, out[:, :, 2])

    signal = out.astype(np.int16)
    if previous_arr is not None:
        feedback_shift = max(1, int(2 + width * 0.018 * amount))
        feedback = np.roll(previous_arr, feedback_shift, axis=1).astype(np.float32)
        feedback_mix = (0.08 + 0.30 * amount) * np.clip(response * 1.4, 0.0, 1.0)
        signal = np.rint(
            signal.astype(np.float32) * (1.0 - feedback_mix[:, :, None])
            + feedback * feedback_mix[:, :, None]
        ).astype(np.int16)
    gain = 1.0 + 0.35 * amount * math.sin(base_phase + phase * 2.2)
    bias = int(round(34.0 * amount * math.sin(base_phase * 1.9 - phase * 1.4)))
    signal = np.clip(np.rint(signal.astype(np.float32) * gain + bias), 0, 255).astype(np.int16)
    low_clip = int(12 + 28 * amount)
    high_clip = int(243 - 34 * amount)
    signal[signal <= low_clip] = 0
    signal[signal >= high_clip] = 255
    out = signal.astype(np.uint8)

    bar_count = 1 + int(round(amount * 3.0))
    peak_rows = np.argsort(row_response)[::-1]
    selected_rows: list[int] = []
    for center in peak_rows:
        if any(abs(int(center) - prior) < max(2, height // 24) for prior in selected_rows):
            continue
        selected_rows.append(int(center))
        bar_height = max(1, int(height * (0.002 + 0.012 * amount)))
        top = max(0, int(center) - bar_height // 2)
        bottom = min(height, top + bar_height)
        source_level = float(luma[int(center)].mean())
        out[top:bottom, :, :] = 255 if source_level >= 127.5 else 0
        if len(selected_rows) >= bar_count:
            break
    if amount > 0.55 and math.sin(base_phase + phase * 0.91) > 0.88 - 0.12 * amount:
        out = np.subtract(255, out, dtype=np.uint8)
    return np.ascontiguousarray(out, dtype=np.uint8)


def _apply_hex_editing_frame(
    frame: np.ndarray | Image.Image,
    intensity: float,
    frame_index: int,
    seed: int | None,
    analysis: _FrameMaterialAnalysis | None = None,
    control: _FrameEffectControl | None = None,
) -> np.ndarray:
    source = _phase2_rgb_copy(frame)
    arr = source.copy()
    amount = _phase2_effect_amount(intensity)
    height, width = arr.shape[:2]
    if amount <= 0.0 or height < 4 or width < 4:
        return arr
    rng = (
        np.random.default_rng(control.event_seed)
        if control is not None
        else _phase2_effect_rng(seed, _HEX_EDITING_SALT, frame_index)
    )
    luma = analysis.luma if analysis is not None and analysis.luma.shape == source.shape[:2] else _phase2_luma(source)
    edge = (
        analysis.edge_magnitude
        if analysis is not None and analysis.luma.shape == source.shape[:2]
        else cv2.magnitude(
            cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3),
            cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3),
        )
    )
    block = max(10, int(min(height, width) * (0.025 + 0.040 * amount)))
    grid_w = max(1, math.ceil(width / block))
    grid_h = max(1, math.ceil(height / block))
    coarse_luma = cv2.resize(luma, (grid_w, grid_h), interpolation=cv2.INTER_AREA)
    coarse_edge = cv2.resize(edge, (grid_w, grid_h), interpolation=cv2.INTER_AREA)
    score = _normalized_signal(coarse_edge) * 0.72
    score += _normalized_signal(np.abs(coarse_luma - float(luma.mean()))) * 0.28
    if control is not None and control.focus_x is not None and control.focus_y is not None:
        grid_y, grid_x = np.mgrid[0:grid_h, 0:grid_w]
        focus_x = float(control.focus_x) * max(1, grid_w - 1)
        focus_y = float(control.focus_y) * max(1, grid_h - 1)
        focus_distance = (
            ((grid_x - focus_x) / max(1.0, grid_w * 0.32)) ** 2
            + ((grid_y - focus_y) / max(1.0, grid_h * 0.32)) ** 2
        )
        score += np.exp(-focus_distance).astype(np.float32) * (0.18 + 0.34 * control.event_strength)
    score += rng.random(score.shape, dtype=np.float32) * 0.025
    ranked = np.argsort(score.ravel())[::-1]
    mutation_count = min(len(ranked), max(1, int(round(1.0 + 10.0 * amount))))
    candidate_pool = ranked[: min(len(ranked), max(mutation_count * 5, 8))]
    for mutation_index, flat_index in enumerate(ranked[:mutation_count]):
        target_y, target_x = np.unravel_index(int(flat_index), score.shape)
        source_flat = int(candidate_pool[(mutation_index * 3 + int(rng.integers(0, len(candidate_pool)))) % len(candidate_pool)])
        source_y, source_x = np.unravel_index(source_flat, score.shape)
        ty0, tx0 = int(target_y * block), int(target_x * block)
        sy0, sx0 = int(source_y * block), int(source_x * block)
        chunk_h = block * (1 + int(round(amount)))
        chunk_w = block * (2 + int(round(3.0 * amount)))
        bh = min(chunk_h, height - ty0, height - sy0)
        bw = min(chunk_w, width - tx0, width - sx0)
        if bh <= 0 or bw <= 0:
            continue
        operation = (mutation_index + int(rng.integers(0, 4))) % 4
        source_chunk = source[sy0 : sy0 + bh, sx0 : sx0 + bw].copy()
        if operation == 0:
            arr[ty0 : ty0 + bh, tx0 : tx0 + bw] = source_chunk
        elif operation == 1:
            repeat_width = max(2, bw // max(2, 5 - int(round(amount * 2))))
            word = source_chunk[:, :repeat_width]
            arr[ty0 : ty0 + bh, tx0 : tx0 + bw] = np.tile(
                word,
                (1, math.ceil(bw / repeat_width), 1),
            )[:, :bw]
        elif operation == 2:
            channel = mutation_index % 3
            damaged = source_chunk[:, :, channel].astype(np.uint16)
            arr[ty0 : ty0 + bh, tx0 : tx0 + bw, channel] = (
                ((damaged << 4) & 0xF0) | (damaged >> 4)
            ).astype(np.uint8)
        else:
            offset = max(1, int(round(bw * (0.18 + 0.30 * amount))))
            arr[ty0 : ty0 + bh, tx0 : tx0 + bw] = np.roll(source_chunk, offset, axis=1)
    return arr


def _apply_random_noise_bw_frame(
    frame: np.ndarray | Image.Image,
    intensity: float,
    frame_index: int,
    seed: int | None,
    analysis: _FrameMaterialAnalysis | None = None,
) -> np.ndarray:
    source = _phase2_rgb_copy(frame)
    amount = _phase2_effect_amount(intensity)
    luma = analysis.luma if analysis is not None and analysis.luma.shape == source.shape[:2] else _phase2_luma(source)
    if analysis is not None and analysis.luma.shape == source.shape[:2]:
        texture = analysis.texture
        edge = analysis.edge_magnitude
    else:
        local_mean = cv2.GaussianBlur(luma, (0, 0), 2.0)
        texture = _normalized_signal(np.abs(luma - local_mean))
        edge = cv2.magnitude(
            cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3),
            cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3),
        )
    material_activity = np.clip(texture * 0.60 + _normalized_signal(edge) * 0.40, 0.0, 1.0)
    rng = _phase2_effect_rng(seed, _RANDOM_NOISE_BW_SALT, frame_index)
    stochastic_threshold = rng.random(luma.shape, dtype=np.float32) * 255.0
    noise_weight = amount * (0.16 + material_activity * 0.84)
    threshold = 127.5 * (1.0 - noise_weight) + stochastic_threshold * noise_weight
    binary = np.where(luma >= threshold, np.uint8(255), np.uint8(0))
    return np.repeat(binary[:, :, None], 3, axis=2)


def _validate_zone_effect_candidate(
    candidate: object,
    expected_shape: tuple[int, int, int],
    effect: str,
) -> np.ndarray:
    if not isinstance(candidate, np.ndarray):
        raise RenderError(f"Zone {effect} candidate is not a NumPy RGB frame.")
    if candidate.dtype != np.uint8:
        raise RenderError(f"Zone {effect} candidate must use uint8 pixels.")
    if candidate.shape != expected_shape:
        raise RenderError(
            f"Zone {effect} candidate shape {candidate.shape!r} does not match {expected_shape!r}."
        )
    if not candidate.flags.writeable:
        raise RenderError(f"Zone {effect} candidate is not writable.")
    return candidate


def _apply_phase2_zone_effect(
    effect: str,
    frame: np.ndarray,
    rectangle: tuple[int, int, int, int],
    intensity: float,
    frame_index: int,
    fps: int,
    seed: int | None,
    analysis: _FrameMaterialAnalysis,
    control: _FrameEffectControl,
    previous: np.ndarray | None,
) -> None:
    """Run one existing effect against a copied ROI and replace only that ROI."""
    left, top, right, bottom = rectangle
    try:
        candidate_input = frame[top:bottom, left:right].copy()
        if effect == "pixel_sorting":
            candidate = _apply_pixel_sorting_frame(
                candidate_input,
                intensity * control.strength,
                frame_index,
                seed,
                analysis,
                control,
            )
        elif effect == "databending":
            candidate = _apply_databending_frame(
                candidate_input,
                intensity * control.strength,
                frame_index,
                fps,
                seed,
                analysis,
                control,
            )
        elif effect == "circuit_bending":
            candidate = _apply_circuit_bending_frame(
                candidate_input,
                intensity * control.strength,
                frame_index,
                fps,
                seed,
                previous,
                analysis,
                control,
            )
        elif effect == "hex_editing":
            candidate = _apply_hex_editing_frame(
                candidate_input,
                intensity * control.strength,
                frame_index,
                seed,
                analysis,
                control,
            )
        elif effect == "random_noise_bw":
            candidate = _apply_random_noise_bw_frame(
                candidate_input,
                intensity * control.strength,
                frame_index,
                seed,
                analysis,
            )
        else:
            raise RenderError(f"Unsupported Zone effect: {effect}")
        validated = _validate_zone_effect_candidate(candidate, candidate_input.shape, effect)
        frame[top:bottom, left:right] = validated
    except RenderError:
        raise
    except Exception as exc:
        raise RenderError(f"Zone {effect} processing failed: {exc}") from exc


def _apply_phase2_frame_effects(
    image: Image.Image,
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    seed: int | None,
    previous: Image.Image | None = None,
    choreographer: _FrameEffectChoreographer | None = None,
    material: np.ndarray | Image.Image | None = None,
    zones: tuple[ZoneDefinition, ...] = (),
    effect_zone_assignments: dict[str, str] | None = None,
) -> Image.Image:
    if not any(_effect_on(effects, key) for key in PHASE2_FRAME_EFFECT_ORDER):
        return image
    local_choreographer = choreographer
    if local_choreographer is None:
        local_choreographer = _FrameEffectChoreographer(effects, intensity, fps, seed)
        if previous is not None:
            previous_rgb = _phase2_rgb_copy(previous.resize(image.size))
            local_choreographer.previous_rgb = previous_rgb
            local_choreographer.previous_luma = _phase2_luma(previous_rgb)
    normalized_zones, normalized_assignments, _ = normalize_zone_state(
        list(zones) if isinstance(zones, (list, tuple)) else zones,
        effect_zone_assignments,
    )
    zone_by_id = {zone.id: zone for zone in normalized_zones}
    effect_rectangles: dict[str, tuple[int, int, int, int]] = {}
    for effect, zone_id in normalized_assignments.items():
        if not _effect_on(effects, effect):
            continue
        rectangle = rasterize_zone(zone_by_id[zone_id], image.size)
        if rectangle is not None:
            effect_rectangles[effect] = rectangle

    # Full Frame is the compatibility oracle: keep the pre-Zones path byte-for-byte.
    if not effect_rectangles:
        analysis = local_choreographer.analysis_for(image if material is None else material)
        controls = local_choreographer.controls_for(analysis, frame_index)
        effect_seed = local_choreographer.seed
        frame: np.ndarray | Image.Image = _phase2_rgb_copy(image)
        if _effect_on(effects, "pixel_sorting"):
            control = controls["pixel_sorting"]
            frame = _apply_pixel_sorting_frame(
                frame,
                intensity * control.strength,
                frame_index,
                effect_seed,
                analysis,
                control,
            )
        if _effect_on(effects, "databending"):
            control = controls["databending"]
            frame = _apply_databending_frame(
                frame,
                intensity * control.strength,
                frame_index,
                fps,
                effect_seed,
                analysis,
                control,
            )
        if _effect_on(effects, "circuit_bending"):
            control = controls["circuit_bending"]
            frame = _apply_circuit_bending_frame(
                frame,
                intensity * control.strength,
                frame_index,
                fps,
                effect_seed,
                local_choreographer.previous_rgb,
                analysis,
                control,
            )
        if _effect_on(effects, "hex_editing"):
            control = controls["hex_editing"]
            frame = _apply_hex_editing_frame(
                frame,
                intensity * control.strength,
                frame_index,
                effect_seed,
                analysis,
                control,
            )
        if _effect_on(effects, "random_noise_bw"):
            control = controls["random_noise_bw"]
            frame = _apply_random_noise_bw_frame(
                frame,
                intensity * control.strength,
                frame_index,
                effect_seed,
                analysis,
            )
        local_choreographer.commit(analysis, image)
        return Image.fromarray(_phase2_rgb_copy(frame), mode="RGB")

    effect_input = _phase2_rgb_copy(image)
    material_input = _phase2_rgb_copy(image if material is None else material)
    if material_input.shape[:2] != effect_input.shape[:2]:
        material_input = cv2.resize(
            material_input,
            (effect_input.shape[1], effect_input.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    analysis = local_choreographer.analysis_for(image if material is None else material)
    zone_analyses: dict[tuple[int, int, int, int], _FrameMaterialAnalysis] = {}
    effect_analyses: dict[str, _FrameMaterialAnalysis] = {}
    for effect, rectangle in effect_rectangles.items():
        if rectangle not in zone_analyses:
            if len(zone_analyses) >= MAX_ZONES:
                raise RenderError("Zone analysis cache exceeded the three-Zone limit.")
            zone_analyses[rectangle] = local_choreographer.analysis_for_zone(
                material_input,
                rectangle,
            )
        effect_analyses[effect] = zone_analyses[rectangle]
    controls = local_choreographer.controls_for(analysis, frame_index, effect_analyses)
    effect_seed = local_choreographer.seed
    frame = effect_input.copy()
    for effect in PHASE2_FRAME_EFFECT_ORDER:
        if not _effect_on(effects, effect):
            continue
        rectangle = effect_rectangles.get(effect)
        control = controls[effect]
        if rectangle is not None:
            previous_zone = (
                local_choreographer.zone_previous_rgb.get(rectangle)
                if effect == "circuit_bending"
                else None
            )
            _apply_phase2_zone_effect(
                effect,
                frame,
                rectangle,
                intensity,
                frame_index,
                fps,
                effect_seed,
                effect_analyses[effect],
                control,
                previous_zone,
            )
        elif effect == "pixel_sorting":
            frame = _apply_pixel_sorting_frame(
                frame, intensity * control.strength, frame_index, effect_seed, analysis, control
            )
        elif effect == "databending":
            frame = _apply_databending_frame(
                frame, intensity * control.strength, frame_index, fps, effect_seed, analysis, control
            )
        elif effect == "circuit_bending":
            frame = _apply_circuit_bending_frame(
                frame,
                intensity * control.strength,
                frame_index,
                fps,
                effect_seed,
                local_choreographer.previous_rgb,
                analysis,
                control,
            )
        elif effect == "hex_editing":
            frame = _apply_hex_editing_frame(
                frame, intensity * control.strength, frame_index, effect_seed, analysis, control
            )
        else:
            frame = _apply_random_noise_bw_frame(
                frame, intensity * control.strength, frame_index, effect_seed, analysis
            )
    local_choreographer.commit(analysis, image)
    local_choreographer.commit_zones(zone_analyses, effect_input)
    return Image.fromarray(_phase2_rgb_copy(frame), mode="RGB")


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
        x_positions=tuple(x_offset + (col * char_width) for col in range(width_chars)),
        y_positions=tuple(y_offset + (row * line_height) for row in range(rows)),
    )


def _glyph_masks_for_layout(layout: TextLayout, charset: str) -> dict[str, Image.Image] | None:
    if not charset.isascii():
        return None
    mask_width = max(8, layout.char_width * 3)
    mask_height = max(8, layout.line_height * 3)
    masks: dict[str, Image.Image] = {}
    for character in set(charset):
        mask = Image.new("L", (mask_width, mask_height), 0)
        ImageDraw.Draw(mask).text((0, 0), character, font=layout.font, fill=255)
        if mask.getbbox() is not None:
            masks[character] = mask
    return masks


def prepare_ansi_source(
    frame_rgb: np.ndarray | Image.Image,
    output_size: tuple[int, int],
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    framing: dict[str, Any] | None = None,
    timing: _FrameTimingDetail | None = None,
) -> Image.Image:
    framing_started = time.perf_counter()
    image = fit_frame_to_output(frame_rgb, output_size, **(framing or {}))
    if timing is not None:
        timing.resize_framing_seconds += max(0.0, time.perf_counter() - framing_started)
    effects_started = time.perf_counter()
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
    if timing is not None:
        timing.ansi_effect_seconds += max(0.0, time.perf_counter() - effects_started)
    return image


def prepare_public_access_source(
    frame_rgb: np.ndarray | Image.Image,
    output_size: tuple[int, int],
    preset: dict[str, Any],
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    framing: dict[str, Any] | None = None,
    seed: int | None = None,
    timing: _FrameTimingDetail | None = None,
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
        timing=timing,
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
    frame_rgb: np.ndarray | Image.Image,
    output_size: tuple[int, int],
    effects: dict[str, bool],
    intensity: float,
    frame_index: int,
    fps: int,
    framing: dict[str, Any] | None = None,
    timing: _FrameTimingDetail | None = None,
) -> Image.Image:
    framing_started = time.perf_counter()
    image = fit_frame_to_output(frame_rgb, output_size, **(framing or {}))
    if timing is not None:
        timing.resize_framing_seconds += max(0.0, time.perf_counter() - framing_started)
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
    glyph_masks: dict[str, Image.Image] | None = None,
    timing: _FrameTimingDetail | None = None,
) -> Image.Image:
    effects = effects or {}
    intensity = max(0.0, float(intensity))
    rng = random.Random((frame_index + 1) * 7919)
    prepare_started = time.perf_counter()
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
    if timing is not None:
        timing.text_prepare_seconds += max(0.0, time.perf_counter() - prepare_started)

    image = Image.new("RGB", output_size, tuple(preset["background"]))
    draw = ImageDraw.Draw(image)
    charset = str(preset["charset"])
    x_positions = layout.x_positions
    y_positions = layout.y_positions
    jitter_base = 1.0 if chunky_blocks else 2.0
    row_jitter = int(round((jitter_base if _effect_on(effects, "glitch") else 0.0) * intensity))
    noise = float(preset["base_noise"])
    if _effect_on(effects, "char_noise"):
        noise += 0.035 * intensity

    draw_started = time.perf_counter()
    for row in range(layout.rows):
        row_shift = rng.randint(-row_jitter, row_jitter) if row_jitter else 0
        for col in range(layout.cols):
            brightness = float(luma[row, col])
            character = _character_for_brightness(charset, brightness)
            if noise and rng.random() < noise:
                character = rng.choice(charset[1:] or charset)

            x = x_positions[col] + row_shift
            y = y_positions[row]
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
            mask = glyph_masks.get(character) if glyph_masks is not None else None
            if mask is not None:
                draw.bitmap((x, y), mask, fill=color)
            else:
                if glyph_masks is None:
                    draw.text((x, y), character, font=layout.font, fill=color)

    if timing is not None:
        timing.image_draw_text_seconds += max(0.0, time.perf_counter() - draw_started)

    output_effect_started = time.perf_counter()
    image = _apply_ansi_output_effects(image, preset, frame_index, rng, layout, effects, intensity, fps)
    if timing is not None:
        timing.ansi_output_effect_seconds += max(0.0, time.perf_counter() - output_effect_started)
    return image


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


def _ensure_writable_frame_array(frame_arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(frame_arr, dtype=np.uint8)
    if not arr.flags.writeable:
        arr = arr.copy()
    return arr


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

    arr = _ensure_writable_frame_array(np.asarray(image, dtype=np.uint8))

    if _effect_on(effects, "scanlines"):
        gap = max(2, layout.line_height // 2)
        strength = min(0.78, float(preset.get("scanline_strength", 0.2)) * max(0.2, intensity))
        arr = _ensure_writable_frame_array(
            np.asarray(_apply_scanlines(Image.fromarray(arr), gap, strength), dtype=np.uint8)
        )

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
    hue = hsv[:, :, 0].astype(np.int32)
    shift = int(amount) % 256
    shifted = (hue + shift) % 256
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


def _datamosh_eligible_start_frame(settings: RenderSettings, frame_count: int) -> int:
    local_style_time = max(0.0, settings.style_begin_time - settings.output_time_offset)
    frame = math.ceil(local_style_time * settings.fps - 1e-9)
    return max(0, min(frame_count, frame))


def _emit(log: LogCallback, message: str) -> None:
    if log:
        log(message)


def _emit_progress(progress: ProgressCallback, value: int) -> None:
    if progress:
        progress(max(0, min(100, value)))
