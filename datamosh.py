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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

import ffmpeg_utils
import numpy as np
import timeline_math


LogCallback = Callable[[str], None] | None
START_PREFIX = b"\x00\x00\x01"
VOP_START_CODE = 0xB6
VOP_NAMES = {0: "I", 1: "P", 2: "B", 3: "S"}
DATAMOSH_SEED_SALT = 0x44_41_54_41_4D_4F_53_48
OVERFLOW_SEED_SALT = 0x4F_56_45_52_46_4C_4F_57
BLEED_SEED_SALT = 0x42_4C_45_45_44_4D_4F_44
SKRRT_SEED_SALT = 0x53_4B_52_52_54_4D_4F_44
SCATTER_SEED_SALT = 0x53_43_41_54_54_45_52
DATAMOSH_MODE_GENERAL = "datamoshing"
DATAMOSH_MODE_OVERFLOW = "overflow"
DATAMOSH_MODE_SKRRT = "skrrt"
DATAMOSH_MODE_SCATTER = "scatter"
DATAMOSH_MODE_BLEED = "bleed"
DATAMOSH_MODE_ORDER = (
    DATAMOSH_MODE_GENERAL,
    DATAMOSH_MODE_OVERFLOW,
    DATAMOSH_MODE_SKRRT,
    DATAMOSH_MODE_SCATTER,
    DATAMOSH_MODE_BLEED,
)
AUXILIARY_SCENE_CHANGE_THRESHOLD = 2_147_483_647
AUXILIARY_PREDICTION_POLICY = (
    "mpeg4/bf=0/g=N+1/sc_threshold=2147483647/strict_gop/threads=1"
)


class DatamoshError(RuntimeError):
    """Raised when the authentic compressed-video DATAMOSHING stage fails."""


def normalize_datamosh_mode_order(value: object) -> tuple[str, ...]:
    """Return one complete, duplicate-free Layer order of known codec modes."""
    if not isinstance(value, (list, tuple)):
        return DATAMOSH_MODE_ORDER

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_mode in value:
        if not isinstance(raw_mode, str):
            continue
        mode = raw_mode.strip().lower()
        if mode in DATAMOSH_MODE_ORDER and mode not in seen:
            normalized.append(mode)
            seen.add(mode)
    normalized.extend(mode for mode in DATAMOSH_MODE_ORDER if mode not in seen)
    return tuple(normalized)


@dataclass(frozen=True)
class DatamoshSpatialRegion:
    """One anonymous normalized material-led region for bounded Scatter preparation."""

    x: float
    y: float
    width: float
    height: float
    weight: float

    def as_dict(self) -> dict[str, object]:
        return {
            "region": [
                round(float(self.x), 6),
                round(float(self.y), 6),
                round(float(self.width), 6),
                round(float(self.height), 6),
            ],
            "weight": round(float(self.weight), 6),
        }


@dataclass(frozen=True)
class DatamoshActivity:
    """Anonymous scalar material activity aligned to one rendered output frame."""

    frame: int
    absolute_frame: int
    motion_activity: float
    motion_x: float = 0.0
    motion_y: float = 0.0
    direction_confidence: float = 0.0
    texture_activity: float = 0.0
    edge_activity: float = 0.0
    spatial_regions: tuple[DatamoshSpatialRegion, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "absolute_frame": self.absolute_frame,
            "motion_activity": round(float(self.motion_activity), 6),
            "motion_x": round(float(self.motion_x), 6),
            "motion_y": round(float(self.motion_y), 6),
            "direction_confidence": round(float(self.direction_confidence), 6),
            "texture_activity": round(float(self.texture_activity), 6),
            "edge_activity": round(float(self.edge_activity), 6),
            "spatial_regions": [region.as_dict() for region in self.spatial_regions],
        }


@dataclass(frozen=True)
class SkrrtPreparedWindow:
    """Bounded reverse prediction material held only for one render operation."""

    episode_start_frame: int
    episode_end_frame: int
    source_start_frame: int
    source_end_frame: int
    source_chronological_order: tuple[int, ...]
    source_reversed_order: tuple[int, ...]
    target_frames: tuple[int, ...]
    recovery_frame: int
    replacement_stride: int
    motion_activity: float
    motion_x: float
    motion_y: float
    direction_confidence: float
    reverse_stream_sha256: str
    prediction_vops: tuple[bytes, ...]
    reverse_vop_count: int
    reverse_decode_seconds: float
    auxiliary_encode_seconds: float
    structural_validation_seconds: float
    temporary_disk_bytes: int
    zone_box: tuple[int, int, int, int] | None = None
    current_frame_sha256s: tuple[str, ...] = ()
    reverse_source_frame_sha256s: tuple[str, ...] = ()
    prepared_frame_sha256s: tuple[str, ...] = ()
    prepared_inside_exact: bool = False
    prepared_outside_exact: bool = False

    def as_dict(self, *, absolute_frame_offset: int = 0) -> dict[str, object]:
        result = {
            "episode_bounds": [self.episode_start_frame, self.episode_end_frame],
            "absolute_episode_bounds": [
                absolute_frame_offset + self.episode_start_frame,
                absolute_frame_offset + self.episode_end_frame,
            ],
            "source_prep_range": [self.source_start_frame, self.source_end_frame],
            "source_chronological_order": list(self.source_chronological_order),
            "source_reversed_order": list(self.source_reversed_order),
            "main_vop_targets": list(self.target_frames),
            "recovery_frame": self.recovery_frame,
            "absolute_recovery_frame": absolute_frame_offset + self.recovery_frame,
            "replacement_stride": self.replacement_stride,
            "motion_activity": round(float(self.motion_activity), 6),
            "motion_x": round(float(self.motion_x), 6),
            "motion_y": round(float(self.motion_y), 6),
            "direction_confidence": round(float(self.direction_confidence), 6),
            "reverse_stream_sha256": self.reverse_stream_sha256,
            "reverse_vop_count": self.reverse_vop_count,
            "prediction_vop_count": len(self.prediction_vops),
            "reverse_decode_seconds": round(float(self.reverse_decode_seconds), 6),
            "auxiliary_encode_seconds": round(float(self.auxiliary_encode_seconds), 6),
            "structural_validation_seconds": round(
                float(self.structural_validation_seconds),
                6,
            ),
            "temporary_disk_bytes": self.temporary_disk_bytes,
        }
        if self.zone_box is not None:
            result.update(
                {
                    "zone_box": list(self.zone_box),
                    "current_frame_sha256s": list(self.current_frame_sha256s),
                    "reverse_source_frame_sha256s": list(
                        self.reverse_source_frame_sha256s
                    ),
                    "prepared_frame_sha256s": list(self.prepared_frame_sha256s),
                    "prepared_inside_exact": self.prepared_inside_exact,
                    "prepared_outside_exact": self.prepared_outside_exact,
                }
            )
        return result


@dataclass(frozen=True)
class ScatterTemporalFragment:
    """One material-led region sourced from a non-current nearby output time."""

    fragment_id: int
    region: DatamoshSpatialRegion
    temporal_offset: int
    resolve_after_frame: int
    source_frame_sha256: str | None = None
    source_region_sha256: str | None = None
    prepared_region_sha256: str | None = None
    provenance_mean_absolute_delta: float | None = None

    def as_dict(
        self,
        *,
        provenance_frame: int,
        absolute_frame_offset: int = 0,
    ) -> dict[str, object]:
        result = self.region.as_dict()
        result.update(
            {
                "fragment_id": self.fragment_id,
                "temporal_offset": self.temporal_offset,
                "source_frame": provenance_frame + self.temporal_offset,
                "absolute_source_frame": (
                    absolute_frame_offset + provenance_frame + self.temporal_offset
                ),
                "resolve_after_frame": self.resolve_after_frame,
            }
        )
        if self.source_frame_sha256 is not None:
            result["source_frame_sha256"] = self.source_frame_sha256
        if self.source_region_sha256 is not None:
            result["source_region_sha256"] = self.source_region_sha256
        if self.prepared_region_sha256 is not None:
            result["prepared_region_sha256"] = self.prepared_region_sha256
        if self.provenance_mean_absolute_delta is not None:
            result["provenance_mean_absolute_delta"] = round(
                float(self.provenance_mean_absolute_delta),
                6,
            )
        return result


@dataclass(frozen=True)
class ScatterPreparedWindow:
    """Bounded multi-time fragment prediction held only for one render operation."""

    episode_start_frame: int
    episode_end_frame: int
    source_start_frame: int
    source_end_frame: int
    target_frames: tuple[int, ...]
    recovery_frame: int
    replacement_stride: int
    fragments: tuple[ScatterTemporalFragment, ...]
    provenance_frame: int
    motion_activity: float
    texture_activity: float
    edge_activity: float
    prepared_stream_sha256: str
    prepared_frame_sha256s: tuple[str, ...]
    prediction_vops: tuple[bytes, ...]
    prepared_vop_count: int
    extraction_seconds: float
    fragment_assembly_seconds: float
    auxiliary_encode_seconds: float
    structural_validation_seconds: float
    temporary_disk_bytes: int

    def as_dict(self, *, absolute_frame_offset: int = 0) -> dict[str, object]:
        return {
            "episode_bounds": [self.episode_start_frame, self.episode_end_frame],
            "absolute_episode_bounds": [
                absolute_frame_offset + self.episode_start_frame,
                absolute_frame_offset + self.episode_end_frame,
            ],
            "source_prep_range": [self.source_start_frame, self.source_end_frame],
            "main_vop_targets": list(self.target_frames),
            "recovery_frame": self.recovery_frame,
            "absolute_recovery_frame": absolute_frame_offset + self.recovery_frame,
            "replacement_stride": self.replacement_stride,
            "provenance_frame": self.provenance_frame,
            "absolute_provenance_frame": absolute_frame_offset + self.provenance_frame,
            "fragments": [
                fragment.as_dict(
                    provenance_frame=self.provenance_frame,
                    absolute_frame_offset=absolute_frame_offset,
                )
                for fragment in self.fragments
            ],
            "distinct_temporal_offsets": sorted(
                {fragment.temporal_offset for fragment in self.fragments}
            ),
            "motion_activity": round(float(self.motion_activity), 6),
            "texture_activity": round(float(self.texture_activity), 6),
            "edge_activity": round(float(self.edge_activity), 6),
            "prepared_stream_sha256": self.prepared_stream_sha256,
            "prepared_frame_sha256s": list(self.prepared_frame_sha256s),
            "prepared_vop_count": self.prepared_vop_count,
            "prediction_vop_count": len(self.prediction_vops),
            "extraction_seconds": round(float(self.extraction_seconds), 6),
            "fragment_assembly_seconds": round(float(self.fragment_assembly_seconds), 6),
            "auxiliary_encode_seconds": round(float(self.auxiliary_encode_seconds), 6),
            "structural_validation_seconds": round(
                float(self.structural_validation_seconds),
                6,
            ),
            "temporary_disk_bytes": self.temporary_disk_bytes,
        }


@dataclass(frozen=True)
class DatamoshOperation:
    """One deterministic operation in the shared MPEG-4 prediction pipeline."""

    mode: str
    enabled: bool
    intensity: float
    seed: int | None
    salt: int
    order: int
    start_frame: int
    end_frame: int
    absolute_frame_offset: int
    transitions: tuple[DatamoshTransition, ...] = ()
    activity: tuple[DatamoshActivity, ...] = ()
    protected_intervals: tuple[tuple[int, int], ...] = ()
    parameters: tuple[tuple[str, int | float | str], ...] = ()
    zone_box: tuple[int, int, int, int] | None = None
    prepared_windows: tuple[SkrrtPreparedWindow, ...] = ()
    prepared_scatter_windows: tuple[ScatterPreparedWindow, ...] = ()
    planned_events: tuple[DatamoshEvent, ...] = ()
    planned_source_vops: tuple[tuple[int, bytes], ...] = ()
    planning_source_sha256: str | None = None

    def as_dict(self) -> dict[str, object]:
        result = {
            "mode": self.mode,
            "enabled": self.enabled,
            "intensity": self.intensity,
            "seed": self.seed,
            "salt": self.salt,
            "order": self.order,
            "temporal_range": [self.start_frame, self.end_frame],
            "absolute_frame_offset": self.absolute_frame_offset,
            "transition_count": len(self.transitions),
            "activity_sample_count": len(self.activity),
            "protected_intervals": [list(interval) for interval in self.protected_intervals],
            "parameters": dict(self.parameters),
            "prepared_windows": [
                window.as_dict(absolute_frame_offset=self.absolute_frame_offset)
                for window in self.prepared_windows
            ],
            "prepared_scatter_windows": [
                window.as_dict(absolute_frame_offset=self.absolute_frame_offset)
                for window in self.prepared_scatter_windows
            ],
            "planned_event_count": len(self.planned_events),
            "planned_source_vops": [
                {
                    "frame": frame,
                    "sha256": _sha256(payload),
                }
                for frame, payload in self.planned_source_vops
            ],
            "planning_source_sha256": self.planning_source_sha256,
        }
        if self.zone_box is not None:
            result["zone_box"] = list(self.zone_box)
        return result


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
    transition_absolute_frame: int | None = None
    transition_from_kind: str | None = None
    transition_to_kind: str | None = None
    visual_transition: str | None = None
    mode: str = DATAMOSH_MODE_GENERAL
    motion_activity: float | None = None
    motion_x: float | None = None
    motion_y: float | None = None
    direction_confidence: float | None = None
    source_frame_order: tuple[int, ...] = ()
    reversed_source_frame_order: tuple[int, ...] = ()
    reverse_stream_sha256: str | None = None
    scatter_fragments: tuple[ScatterTemporalFragment, ...] = ()
    scatter_provenance_frame: int | None = None
    scatter_stream_sha256: str | None = None
    scatter_prepared_frame_sha256: str | None = None
    recovery_frame: int | None = None
    flow_cascade: int | None = None
    flow_chain_depth: int | None = None
    flow_refresh_interval: int | None = None
    operation_input_sha256: str | None = None
    operation_output_sha256: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "operation": self.operation,
            "mode": self.mode,
            "frame": self.frame,
            "absolute_frame": self.absolute_frame,
            "source_p_frame": self.source_p_frame,
        }
        if self.repeated_at_frames:
            result["repeated_at_frames"] = list(self.repeated_at_frames)
            result["repeat_count"] = len(self.repeated_at_frames)
        if self.transition_absolute_frame is not None:
            result["transition_absolute_frame"] = self.transition_absolute_frame
            result["transition"] = {
                "from_kind": self.transition_from_kind,
                "to_kind": self.transition_to_kind,
                "visual_transition": self.visual_transition,
            }
        if self.motion_activity is not None:
            result["motion_activity"] = round(float(self.motion_activity), 6)
        if self.motion_x is not None:
            result["motion_x"] = round(float(self.motion_x), 6)
        if self.motion_y is not None:
            result["motion_y"] = round(float(self.motion_y), 6)
        if self.direction_confidence is not None:
            result["direction_confidence"] = round(float(self.direction_confidence), 6)
        if self.source_frame_order:
            result["source_frame_order"] = list(self.source_frame_order)
        if self.reversed_source_frame_order:
            result["reversed_source_frame_order"] = list(self.reversed_source_frame_order)
        if self.reverse_stream_sha256 is not None:
            result["reverse_stream_sha256"] = self.reverse_stream_sha256
        if self.scatter_fragments and self.scatter_provenance_frame is not None:
            result["scatter_provenance_frame"] = self.scatter_provenance_frame
            result["scatter_fragments"] = [
                fragment.as_dict(
                    provenance_frame=self.scatter_provenance_frame,
                    absolute_frame_offset=self.absolute_frame - self.frame,
                )
                for fragment in self.scatter_fragments
            ]
        if self.scatter_stream_sha256 is not None:
            result["scatter_stream_sha256"] = self.scatter_stream_sha256
        if self.scatter_prepared_frame_sha256 is not None:
            result["scatter_prepared_frame_sha256"] = self.scatter_prepared_frame_sha256
        if self.recovery_frame is not None:
            result["recovery_frame"] = self.recovery_frame
        if self.flow_cascade is not None:
            result["flow_cascade"] = self.flow_cascade
        if self.flow_chain_depth is not None:
            result["flow_chain_depth"] = self.flow_chain_depth
        if self.flow_refresh_interval is not None:
            result["flow_refresh_interval"] = self.flow_refresh_interval
        if self.operation_input_sha256 is not None:
            result["operation_input_sha256"] = self.operation_input_sha256
        if self.operation_output_sha256 is not None:
            result["operation_output_sha256"] = self.operation_output_sha256
        return result


@dataclass(frozen=True)
class DatamoshTransition:
    """Anonymous rendered-output source boundary used only by the codec stage."""

    frame: int
    absolute_frame: int
    from_kind: str
    to_kind: str
    visual_transition: str
    transition_ordinal: int = 0
    output_time: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "absolute_frame": self.absolute_frame,
            "from_kind": self.from_kind,
            "to_kind": self.to_kind,
            "visual_transition": self.visual_transition,
        }


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
    operations: tuple[DatamoshOperation, ...] = ()
    operation_transform_seconds: tuple[tuple[str, float], ...] = ()

    @property
    def i_reset_count(self) -> int:
        return sum("I_RESET_SUPPRESSED" in event.operation for event in self.events)

    @property
    def p_persistence_count(self) -> int:
        return sum(bool(event.repeated_at_frames) for event in self.events)


@dataclass(frozen=True)
class DatamoshResult:
    output_path: Path
    applied: bool
    frame_count: int
    duration: float
    gop_size: int
    eligible_start_frame: int
    protected_tail_start_frame: int
    effect_intensity: float
    weird_seed: int | None
    transition_targets: tuple[DatamoshTransition, ...]
    events: tuple[DatamoshEvent, ...]
    original_counts: dict[str, int]
    mutated_counts: dict[str, int]
    input_stream_size: int
    manipulated_stream_size: int
    temporary_disk_bytes: int
    intermediate_encode_seconds: float
    reverse_preparation_seconds: float
    reverse_decode_seconds: float
    skrrt_zone_composition_seconds: float
    auxiliary_reverse_encode_seconds: float
    auxiliary_reverse_encode_count: int
    auxiliary_reverse_validation_seconds: float
    reverse_temporary_disk_bytes: int
    scatter_preparation_seconds: float
    scatter_decode_seconds: float
    scatter_fragment_assembly_seconds: float
    auxiliary_scatter_encode_seconds: float
    auxiliary_scatter_encode_count: int
    auxiliary_scatter_validation_seconds: float
    scatter_temporary_disk_bytes: int
    transform_seconds: float
    safe_transcode_seconds: float
    manipulated_stream_sha256: str | None
    operations: tuple[DatamoshOperation, ...] = ()
    operation_transform_seconds: tuple[tuple[str, float], ...] = ()

    def evidence(self) -> dict[str, object]:
        result = {
            "applied": self.applied,
            "frame_count": self.frame_count,
            "duration": self.duration,
            "gop_size": self.gop_size,
            "eligible_start_frame": self.eligible_start_frame,
            "protected_tail_start_frame": self.protected_tail_start_frame,
            "effect_intensity": self.effect_intensity,
            "weird_seed": self.weird_seed,
            "operations": [operation.as_dict() for operation in self.operations],
            "operation_transform_seconds": dict(self.operation_transform_seconds),
            "transition_targets": [target.as_dict() for target in self.transition_targets],
            "events": [event.as_dict() for event in self.events],
            "original_counts": self.original_counts,
            "mutated_counts": self.mutated_counts,
            "input_stream_size": self.input_stream_size,
            "manipulated_stream_size": self.manipulated_stream_size,
            "temporary_disk_bytes": self.temporary_disk_bytes,
            "intermediate_encode_seconds": self.intermediate_encode_seconds,
            "reverse_preparation_seconds": self.reverse_preparation_seconds,
            "reverse_decode_seconds": self.reverse_decode_seconds,
            "auxiliary_reverse_encode_seconds": self.auxiliary_reverse_encode_seconds,
            "auxiliary_reverse_encode_count": self.auxiliary_reverse_encode_count,
            "auxiliary_reverse_validation_seconds": (
                self.auxiliary_reverse_validation_seconds
            ),
            "reverse_temporary_disk_bytes": self.reverse_temporary_disk_bytes,
            "scatter_preparation_seconds": self.scatter_preparation_seconds,
            "scatter_decode_seconds": self.scatter_decode_seconds,
            "scatter_fragment_assembly_seconds": self.scatter_fragment_assembly_seconds,
            "auxiliary_scatter_encode_seconds": self.auxiliary_scatter_encode_seconds,
            "auxiliary_scatter_encode_count": self.auxiliary_scatter_encode_count,
            "auxiliary_scatter_validation_seconds": (
                self.auxiliary_scatter_validation_seconds
            ),
            "scatter_temporary_disk_bytes": self.scatter_temporary_disk_bytes,
            "transform_seconds": self.transform_seconds,
            "safe_transcode_seconds": self.safe_transcode_seconds,
            "manipulated_stream_sha256": self.manipulated_stream_sha256,
        }
        if self.skrrt_zone_composition_seconds > 0.0:
            result["skrrt_zone_composition_seconds"] = (
                self.skrrt_zone_composition_seconds
            )
        return result


@dataclass(frozen=True)
class _SkrrtWindowPlan:
    episode_start_frame: int
    episode_end_frame: int
    source_start_frame: int
    source_end_frame: int
    target_frames: tuple[int, ...]
    recovery_frame: int
    replacement_stride: int
    motion_activity: float
    motion_x: float
    motion_y: float
    direction_confidence: float


@dataclass(frozen=True)
class _SkrrtPreparationTiming:
    preparation_seconds: float = 0.0
    reverse_decode_seconds: float = 0.0
    zone_composition_seconds: float = 0.0
    auxiliary_encode_seconds: float = 0.0
    auxiliary_encode_count: int = 0
    structural_validation_seconds: float = 0.0
    temporary_disk_bytes: int = 0


@dataclass(frozen=True)
class _ScatterWindowPlan:
    episode_start_frame: int
    episode_end_frame: int
    source_start_frame: int
    source_end_frame: int
    target_frames: tuple[int, ...]
    recovery_frame: int
    replacement_stride: int
    fragments: tuple[ScatterTemporalFragment, ...]
    motion_activity: float
    texture_activity: float
    edge_activity: float


@dataclass(frozen=True)
class _ScatterPreparationTiming:
    preparation_seconds: float = 0.0
    decode_seconds: float = 0.0
    fragment_assembly_seconds: float = 0.0
    auxiliary_encode_seconds: float = 0.0
    auxiliary_encode_count: int = 0
    structural_validation_seconds: float = 0.0
    temporary_disk_bytes: int = 0


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


def _validate_auxiliary_prediction_structure(
    data: bytes,
    *,
    expected_count: int,
    mode_label: str,
    window_number: int,
    source_start_frame: int,
    source_end_frame: int,
) -> tuple[Mpeg4Unit, ...]:
    """Require one initial I-VOP followed only by the requested P-VOPs."""
    try:
        units = parse_mpeg4_units(data)
        vops = vop_units(units)
        counts = vop_type_counts(units)
    except DatamoshError as exc:
        raise DatamoshError(
            f"{mode_label} auxiliary prediction structure is unreadable: "
            f"window {window_number}, source range "
            f"[{source_start_frame}, {source_end_frame}), "
            f"requested {expected_count} frame(s), policy {AUXILIARY_PREDICTION_POLICY}: {exc}"
        ) from exc

    i_indexes = tuple(
        index for index, unit in enumerate(vops) if unit.coding_type == 0
    )
    structure_is_valid = (
        expected_count > 0
        and len(vops) == expected_count
        and counts
        == {
            "I": 1,
            "P": expected_count - 1,
            "B": 0,
            "S": 0,
        }
        and vops[0].coding_type == 0
        and all(unit.coding_type == 1 for unit in vops[1:])
    )
    if not structure_is_valid:
        raise DatamoshError(
            f"{mode_label} auxiliary prediction structure is invalid: "
            f"window {window_number}, source range "
            f"[{source_start_frame}, {source_end_frame}), "
            f"requested {expected_count} frame(s), actual VOP count {len(vops)}, "
            f"I indexes {list(i_indexes)}, P={counts['P']}, B={counts['B']}, "
            f"S={counts['S']}, policy {AUXILIARY_PREDICTION_POLICY}."
        )
    return vops


def _auxiliary_prediction_codec_args(frame_count: int) -> list[str]:
    """Return the shared deterministic MPEG-4 I/P-only auxiliary policy."""
    return [
        "-c:v",
        "mpeg4",
        "-bf",
        "0",
        "-g",
        str(frame_count + 1),
        "-sc_threshold",
        str(AUXILIARY_SCENE_CHANGE_THRESHOLD),
        "-mpv_flags",
        "+strict_gop",
        "-q:v",
        "3",
        "-threads",
        "1",
    ]


def transform_mpeg4_part2(
    data: bytes,
    *,
    seed: int | None,
    intensity: float,
    eligible_start_frame: int,
    absolute_frame_offset: int,
    protect_final_gop: bool,
    transitions: tuple[DatamoshTransition, ...] = (),
    protected_tail_start: int | None = None,
    protected_intervals: tuple[tuple[int, int], ...] = (),
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

    effective_tail_start = len(vops)
    if protect_final_gop:
        if protected_tail_start is None:
            protected_tail_start = max(
                (position for position, unit in enumerate(vops) if unit.coding_type == 0),
                default=len(vops),
            )
        effective_tail_start = max(start_frame + 1, min(len(vops), int(protected_tail_start)))
    protected = _normalized_protected_intervals(
        protected_intervals,
        start_frame,
        effective_tail_start,
    )

    transition_by_frame = {
        target.frame: target
        for target in transitions
        if start_frame < target.frame < effective_tail_start
        and not _frame_is_protected(target.frame, protected)
        and not _frame_is_protected(target.frame - 1, protected)
    }
    transition_candidates = [
        position
        for position, target in sorted(transition_by_frame.items())
        if vops[position].coding_type == 0
        and position > 0
        and vops[position - 1].coding_type == 1
        and not _frame_is_protected(position, protected)
        and not _frame_is_protected(position - 1, protected)
    ]
    transition_limit = _transition_target_limit(intensity, len(transition_candidates))
    selected_transitions = sorted(
        sorted(
            transition_candidates,
            key=lambda position: _stable_score(seed, 10, absolute_frame_offset + position),
        )[:transition_limit]
    )

    i_candidates = [
        position
        for position, unit in enumerate(vops)
        if start_frame < position < effective_tail_start
        and unit.coding_type == 0
        and vops[position - 1].coding_type == 1
        and position not in transition_by_frame
        and not _frame_is_protected(position, protected)
        and not _frame_is_protected(position - 1, protected)
    ]
    p_candidates = [
        position
        for position, unit in enumerate(vops)
        if start_frame + 1 < position < effective_tail_start
        and unit.coding_type == 1
        and vops[position - 1].coding_type == 1
        and vops[position - 2].coding_type == 1
        and not _frame_is_protected(position, protected)
        and not _frame_is_protected(position - 1, protected)
        and not _frame_is_protected(position - 2, protected)
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
    occupied = set(selected_i) | set(selected_transitions)
    events: list[DatamoshEvent] = []
    for position in selected_transitions:
        target = transition_by_frame[position]
        source_position = position - 1
        replacements[vops[position].index] = vops[source_position].data
        events.append(
            DatamoshEvent(
                operation="TRANSITION_I_RESET_SUPPRESSED_WITH_P",
                frame=position,
                absolute_frame=absolute_frame_offset + position,
                source_p_frame=source_position,
                transition_absolute_frame=target.absolute_frame,
                transition_from_kind=target.from_kind,
                transition_to_kind=target.to_kind,
                visual_transition=target.visual_transition,
            )
        )

        requested, stride = _transition_persistence_policy(
            intensity,
            _stable_score(seed, 11, absolute_frame_offset + position),
        )
        next_reset = next(
            (
                later
                for later in range(position + 1, effective_tail_start)
                if vops[later].coding_type == 0
            ),
            effective_tail_start,
        )
        repeated: list[int] = []
        for later in range(position + 1, min(next_reset, position + 1 + requested)):
            if _frame_is_protected(later, protected):
                break
            if vops[later].coding_type != 1 or later in occupied:
                continue
            if (later - position - 1) % stride:
                continue
            replacements[vops[later].index] = vops[source_position].data
            occupied.add(later)
            repeated.append(later)
        if repeated:
            events.append(
                DatamoshEvent(
                    operation="TRANSITION_P_PERSISTENCE_REPEAT",
                    frame=repeated[0],
                    absolute_frame=absolute_frame_offset + repeated[0],
                    source_p_frame=source_position,
                    repeated_at_frames=tuple(repeated),
                    transition_absolute_frame=target.absolute_frame,
                    transition_from_kind=target.from_kind,
                    transition_to_kind=target.to_kind,
                    visual_transition=target.visual_transition,
                )
            )

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
        for position in range(start, min(effective_tail_start, start + requested)):
            if (
                position in occupied
                or vops[position].coding_type != 1
                or _frame_is_protected(position, protected)
            ):
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


def transform_mpeg4_operations(
    data: bytes,
    operations: tuple[DatamoshOperation, ...],
) -> DatamoshTransform:
    """Apply enabled prediction operations in order to one elementary stream."""
    initial_units = parse_mpeg4_units(data)
    initial_counts = vop_type_counts(initial_units)
    initial_vops = vop_units(initial_units)
    if not initial_vops:
        raise DatamoshError("DATAMOSH MODES found no MPEG-4 VOP units.")
    if initial_counts["B"] or initial_counts["S"]:
        raise DatamoshError(
            "DATAMOSH MODES controlled stream contains unsupported prediction types: "
            f"B={initial_counts['B']}, S={initial_counts['S']}."
        )
    if initial_vops[0].coding_type != 0:
        raise DatamoshError("DATAMOSH MODES controlled stream does not begin with an I-VOP anchor.")

    enabled = tuple(
        sorted(
            (operation for operation in operations if operation.enabled and operation.intensity > 0.0),
            key=lambda operation: (operation.order, operation.mode),
        )
    )
    if not enabled:
        return _unchanged_transform(data, initial_units, initial_counts)

    seen_modes: set[str] = set()
    for operation in enabled:
        if operation.mode not in DATAMOSH_MODE_ORDER:
            raise DatamoshError(f"Unknown DATAMOSH operation mode: {operation.mode}")
        if operation.mode in seen_modes:
            raise DatamoshError(
                f"Duplicate DATAMOSH operation mode in Layer order: {operation.mode}"
            )
        seen_modes.add(operation.mode)

    current = data
    events: list[DatamoshEvent] = []
    timings: list[tuple[str, float]] = []
    trace_ordered_inputs = (
        len(enabled) > 1
        and any(
            operation.mode in {DATAMOSH_MODE_SKRRT, DATAMOSH_MODE_SCATTER}
            for operation in enabled
        )
    )
    for operation in enabled:
        handler = _OPERATION_HANDLERS.get(operation.mode)
        if handler is None:
            raise DatamoshError(f"Unknown DATAMOSH operation mode: {operation.mode}")
        operation_input_sha256 = _sha256(current)
        started = time.perf_counter()
        try:
            transformed = handler(current, operation)
        except DatamoshError:
            raise
        except Exception as exc:  # noqa: BLE001 - identify the failing ordered operation.
            raise DatamoshError(
                f"DATAMOSH MODES {operation.mode} transform failed: {exc}"
            ) from exc
        timings.append((operation.mode, time.perf_counter() - started))
        current = transformed.data
        if trace_ordered_inputs:
            operation_output_sha256 = _sha256(current)
            events.extend(
                replace(
                    event,
                    operation_input_sha256=operation_input_sha256,
                    operation_output_sha256=operation_output_sha256,
                )
                for event in transformed.events
            )
        else:
            events.extend(transformed.events)

    final_units = parse_mpeg4_units(current)
    final_vops = vop_units(final_units)
    if len(final_vops) != len(initial_vops):
        raise DatamoshError(
            "DATAMOSH MODES VOP count changed unexpectedly: "
            f"{len(initial_vops)} input, {len(final_vops)} transformed."
        )
    final_counts = vop_type_counts(final_units)
    if final_counts["B"] or final_counts["S"]:
        raise DatamoshError("DATAMOSH MODES transformation introduced an unsupported VOP type.")
    return DatamoshTransform(
        data=current,
        events=tuple(sorted(events, key=lambda event: (event.frame, event.mode, event.operation))),
        original_counts=initial_counts,
        mutated_counts=final_counts,
        original_vop_count=len(initial_vops),
        mutated_vop_count=len(final_vops),
        input_sha256=_sha256(data),
        output_sha256=_sha256(current),
        operations=enabled,
        operation_transform_seconds=tuple(timings),
    )


def _apply_planned_operation(
    data: bytes,
    operation: DatamoshOperation,
) -> DatamoshTransform:
    """Apply a historically selected target plan to the then-current Layer stream."""
    units = parse_mpeg4_units(data)
    vops = vop_units(units)
    counts = vop_type_counts(units)
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    if not operation.planned_events:
        return _unchanged_transform(data, units, counts)

    replacements: dict[int, bytes] = {}
    fallback_sources = dict(operation.planned_source_vops)
    for event in operation.planned_events:
        if event.mode != operation.mode:
            raise DatamoshError(
                "DATAMOSH Layer plan mode mismatch: "
                f"expected {operation.mode}, found {event.mode}."
            )
        source_frame = int(event.source_p_frame)
        if not (0 <= source_frame < len(vops)):
            raise DatamoshError(
                f"DATAMOSH Layer plan has invalid {operation.mode} source frame: "
                f"{source_frame}."
            )
        if _frame_is_protected(source_frame, protected):
            raise DatamoshError(
                f"DATAMOSH Layer plan uses protected {operation.mode} source frame "
                f"{source_frame}."
            )
        source = vops[source_frame]
        recursive_source = (
            replacements.get(source.index)
            if event.operation.startswith("OVERFLOW_DECAYING_RECURSIVE_")
            else None
        )
        source_payload = recursive_source if recursive_source is not None else source.data
        if recursive_source is None and source.coding_type != 1:
            source_payload = fallback_sources.get(source_frame, b"")
            fallback_vops = vop_units(parse_mpeg4_units(source_payload))
            if len(fallback_vops) != 1 or fallback_vops[0].coding_type != 1:
                raise DatamoshError(
                    f"DATAMOSH Layer {operation.mode} source frame {source_frame} "
                    "has neither a then-current nor historically planned P-VOP."
                )
        targets = event.repeated_at_frames or (event.frame,)
        for raw_target in targets:
            target = int(raw_target)
            if not (start <= target < end):
                raise DatamoshError(
                    f"DATAMOSH Layer plan has out-of-bounds {operation.mode} target "
                    f"{target} for operation range [{start}, {end})."
                )
            if _frame_is_protected(target, protected):
                raise DatamoshError(
                    f"DATAMOSH Layer plan targets protected {operation.mode} frame "
                    f"{target}."
                )
            replacements[vops[target].index] = source_payload
    return _rewrite_prediction_stream(
        data,
        units,
        vops,
        counts,
        replacements,
        list(operation.planned_events),
    )


def _transform_general_operation(data: bytes, operation: DatamoshOperation) -> DatamoshTransform:
    if operation.planning_source_sha256 is not None:
        return _apply_planned_operation(data, operation)
    return transform_mpeg4_part2(
        data,
        seed=operation.seed,
        intensity=operation.intensity,
        eligible_start_frame=operation.start_frame,
        absolute_frame_offset=operation.absolute_frame_offset,
        protect_final_gop=operation.end_frame < len(vop_units(parse_mpeg4_units(data))),
        transitions=operation.transitions,
        protected_tail_start=operation.end_frame,
        protected_intervals=operation.protected_intervals,
    )


def _transform_overflow_operation(data: bytes, operation: DatamoshOperation) -> DatamoshTransform:
    """Accumulate selected motion-bearing P payloads into forward trails."""
    if operation.planning_source_sha256 is not None:
        return _apply_planned_operation(data, operation)
    units = parse_mpeg4_units(data)
    vops = vop_units(units)
    counts = vop_type_counts(units)
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    activity_by_frame = {
        sample.frame: max(0.0, min(1.0, float(sample.motion_activity)))
        for sample in operation.activity
        if start < sample.frame < end
        and not _frame_is_protected(sample.frame, protected)
    }
    raw_candidates = [
        frame
        for frame, motion in activity_by_frame.items()
        if motion >= 0.015
        and frame > start + 1
        and frame < end - 1
        and vops[frame].coding_type == 1
        and vops[frame - 1].coding_type == 1
        and not _frame_is_protected(frame - 1, protected)
    ]
    if not raw_candidates:
        return _unchanged_transform(data, units, counts)

    amount = max(0.0, min(1.0, operation.intensity / 2.0))
    motions = sorted(activity_by_frame[frame] for frame in raw_candidates)
    peak_motion = max(motions)
    motion_scale = max(0.0, min(1.0, (peak_motion - 0.015) / 0.285))
    quantile = max(0.35, 0.80 - 0.42 * amount)
    transitions = {
        target.frame
        for target in operation.transitions
        if start < target.frame < end
        and not _frame_is_protected(target.frame, protected)
        and not _frame_is_protected(target.frame - 1, protected)
    }

    def overflow_rank(frame: int) -> tuple[float, int]:
        return (
            -activity_by_frame[frame],
            _stable_score(
                operation.seed,
                20,
                operation.absolute_frame_offset + frame,
                salt=operation.salt,
            ),
        )

    shot_boundaries = [
        start,
        *sorted(set(transitions) | set(_protection_boundaries(protected, start, end))),
        end,
    ]
    local_peaks: list[int] = []
    eligible_candidates: set[int] = set()
    for left, right in zip(shot_boundaries, shot_boundaries[1:]):
        local = [frame for frame in raw_candidates if left < frame < right]
        if not local:
            continue
        local_motions = sorted(activity_by_frame[frame] for frame in local)
        local_threshold = max(0.015, _quantile(local_motions, quantile))
        local_eligible = [
            frame
            for frame in local
            if activity_by_frame[frame] >= local_threshold
        ]
        local_eligible.sort(key=overflow_rank)
        eligible_candidates.update(local_eligible)
        local_peaks.append(local_eligible[0])
    candidates = sorted(eligible_candidates, key=overflow_rank)
    fps = max(1, int(_operation_parameter(operation, "fps", 8)))
    duration_frames = max(1, end - start)
    max_episodes = min(
        len(candidates),
        max(
            1,
            int(
                math.ceil(
                    (duration_frames / fps)
                    * (0.10 + 0.36 * amount)
                    * (0.45 + 0.55 * motion_scale)
                )
            ),
        ),
    )
    minimum_spacing = max(2, int(round(fps * (1.5 - amount))))
    selected: list[int] = []
    for frame in sorted(local_peaks, key=overflow_rank):
        selected.append(frame)
        if len(selected) >= max_episodes:
            break
    for frame in candidates:
        if frame in selected:
            continue
        if any(abs(frame - prior) < minimum_spacing for prior in selected):
            continue
        selected.append(frame)
        if len(selected) >= max_episodes:
            break

    replacements: dict[int, bytes] = {}
    occupied: set[int] = set()
    reserved_recoveries: set[int] = set()
    events: list[DatamoshEvent] = []
    for frame in sorted(selected):
        score = _stable_score(
            operation.seed,
            21,
            operation.absolute_frame_offset + frame,
            salt=operation.salt,
        )
        if amount < 0.40:
            requested, stride = 2 + score % 3, 2
        elif amount < 0.75:
            requested, stride = 6 + score % 7, 1 + (score // 7) % 2
        else:
            requested, stride = 14 + score % 15, 1
        activity_scale = max(
            0.40,
            min(1.35, 0.40 + activity_by_frame[frame] * 1.70),
        )
        requested = max(1, int(round(requested * activity_scale)))
        flow_score = _stable_score(
            operation.seed,
            22,
            operation.absolute_frame_offset + frame,
            salt=operation.salt,
        )
        flow_probability = 0.0
        if amount >= 0.40:
            flow_probability = 0.48 + 0.52 * ((amount - 0.40) / 0.60)
        recursive_flow = (
            amount >= 0.40
            and frame not in occupied
            and frame not in reserved_recoveries
            and (flow_score % 1_000_000) / 1_000_000.0 < flow_probability
        )
        if amount >= 0.40 and (
            frame in occupied or frame in reserved_recoveries
        ):
            continue
        if recursive_flow:
            refresh_interval = (
                2 + (flow_score // 1_000_000) % 3
                if amount < 0.75
                else 4 + (flow_score // 1_000_000) % 4
            )
            source_frame = frame
            chain_depth = 0
            cascade = 0
            recursive_steps = 0
            recovery_frame = min(end - 1, frame + 1 + requested)
            episode_events: list[DatamoshEvent] = []
            for later in range(frame + 1, recovery_frame):
                if (
                    later in transitions
                    or later in occupied
                    or later in reserved_recoveries
                    or _frame_is_protected(later, protected)
                ):
                    recovery_frame = later
                    break
                coding_type = vops[later].coding_type
                if coding_type not in {0, 1}:
                    continue
                if coding_type == 1 and recursive_steps >= refresh_interval:
                    source_frame = later
                    chain_depth = 0
                    recursive_steps = 0
                    cascade += 1
                    continue
                source_payload = replacements.get(
                    vops[source_frame].index,
                    vops[source_frame].data,
                )
                replacements[vops[later].index] = source_payload
                occupied.add(later)
                chain_depth += 1
                recursive_steps += 1
                episode_events.append(
                    DatamoshEvent(
                        operation=(
                            "OVERFLOW_DECAYING_RECURSIVE_I_RESET_SUPPRESSED_P_FLOW"
                            if coding_type == 0
                            else "OVERFLOW_DECAYING_RECURSIVE_P_FLOW"
                        ),
                        mode=DATAMOSH_MODE_OVERFLOW,
                        frame=later,
                        absolute_frame=operation.absolute_frame_offset + later,
                        source_p_frame=source_frame,
                        repeated_at_frames=((later,) if coding_type == 1 else ()),
                        motion_activity=activity_by_frame[frame],
                        flow_cascade=cascade,
                        flow_chain_depth=chain_depth,
                        flow_refresh_interval=int(refresh_interval),
                    )
                )
                source_frame = later
            recovery_frame = next(
                (
                    later
                    for later in range(recovery_frame, end)
                    if vops[later].coding_type == 0
                    and later not in occupied
                    and later not in reserved_recoveries
                ),
                end,
            )
            if recovery_frame < end:
                reserved_recoveries.add(recovery_frame)
            events.extend(
                replace(event, recovery_frame=recovery_frame)
                for event in episode_events
            )
            continue
        source = vops[frame]
        repeated: list[int] = []
        reset_frames: list[int] = []
        for later in range(frame + 1, min(end, frame + 1 + requested)):
            if (
                later in transitions
                or later in occupied
                or later in reserved_recoveries
                or _frame_is_protected(later, protected)
            ):
                break
            if vops[later].coding_type == 0:
                replacements[vops[later].index] = source.data
                occupied.add(later)
                reset_frames.append(later)
                continue
            if vops[later].coding_type != 1 or (later - frame - 1) % stride:
                continue
            replacements[vops[later].index] = source.data
            occupied.add(later)
            repeated.append(later)
        if repeated:
            events.append(
                DatamoshEvent(
                    operation="OVERFLOW_P_MOTION_ACCUMULATION",
                    mode=DATAMOSH_MODE_OVERFLOW,
                    frame=frame,
                    absolute_frame=operation.absolute_frame_offset + frame,
                    source_p_frame=frame,
                    repeated_at_frames=tuple(repeated),
                    motion_activity=activity_by_frame[frame],
                )
            )
        for reset_frame in reset_frames:
            events.append(
                DatamoshEvent(
                    operation="OVERFLOW_I_RESET_SUPPRESSED_WITH_P",
                    mode=DATAMOSH_MODE_OVERFLOW,
                    frame=reset_frame,
                    absolute_frame=operation.absolute_frame_offset + reset_frame,
                    source_p_frame=frame,
                    motion_activity=activity_by_frame[frame],
                )
            )
    return _rewrite_prediction_stream(data, units, vops, counts, replacements, events)


def _transform_skrrt_operation(data: bytes, operation: DatamoshOperation) -> DatamoshTransform:
    """Inject bounded reverse-encoded P prediction into the ordered main stream."""
    units = parse_mpeg4_units(data)
    vops = vop_units(units)
    counts = vop_type_counts(units)
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    replacements: dict[int, bytes] = {}
    events: list[DatamoshEvent] = []
    occupied: set[int] = set()
    for window in operation.prepared_windows:
        if not window.prediction_vops:
            raise DatamoshError("SKRRT prepared a reverse window without P prediction material.")
        if not (
            start <= window.episode_start_frame < window.recovery_frame <= end
            and window.source_start_frame >= start
            and window.source_end_frame <= window.episode_start_frame + 1
        ):
            raise DatamoshError(
                "SKRRT prepared a reverse window outside its protected temporal bounds: "
                f"episode {window.episode_start_frame}:{window.recovery_frame}, "
                f"source {window.source_start_frame}:{window.source_end_frame}, "
                f"operation {start}:{end}."
            )
        if window.recovery_frame in window.target_frames:
            raise DatamoshError("SKRRT attempted to overwrite its clean recovery anchor.")
        if (
            _range_hits_protected(window.source_start_frame, window.source_end_frame, protected)
            or _range_hits_protected(
                window.episode_start_frame,
                window.recovery_frame,
                protected,
            )
        ):
            raise DatamoshError("SKRRT prepared a window across protected Style FX coverage.")

        applied_targets: list[int] = []
        suppressed_resets: list[int] = []
        for target in window.target_frames:
            if not (window.episode_start_frame < target < window.recovery_frame):
                raise DatamoshError(f"SKRRT prepared an invalid main-stream VOP target: {target}.")
            if target in occupied:
                continue
            prediction_index = (
                target - window.episode_start_frame - 1
            ) % len(window.prediction_vops)
            replacements[vops[target].index] = window.prediction_vops[prediction_index]
            occupied.add(target)
            applied_targets.append(target)
            if vops[target].coding_type == 0:
                suppressed_resets.append(target)
        if not applied_targets:
            continue

        source_p_frame = max(window.source_start_frame, window.source_end_frame - 2)
        events.append(
            DatamoshEvent(
                operation="SKRRT_REVERSE_PREDICTION_DRAG",
                mode=DATAMOSH_MODE_SKRRT,
                frame=window.episode_start_frame,
                absolute_frame=operation.absolute_frame_offset + window.episode_start_frame,
                source_p_frame=source_p_frame,
                repeated_at_frames=tuple(applied_targets),
                motion_activity=window.motion_activity,
                motion_x=window.motion_x,
                motion_y=window.motion_y,
                direction_confidence=window.direction_confidence,
                source_frame_order=window.source_chronological_order,
                reversed_source_frame_order=window.source_reversed_order,
                reverse_stream_sha256=window.reverse_stream_sha256,
                recovery_frame=window.recovery_frame,
            )
        )
        for reset_frame in suppressed_resets:
            events.append(
                DatamoshEvent(
                    operation="SKRRT_I_RESET_SUPPRESSED_WITH_REVERSE_P",
                    mode=DATAMOSH_MODE_SKRRT,
                    frame=reset_frame,
                    absolute_frame=operation.absolute_frame_offset + reset_frame,
                    source_p_frame=source_p_frame,
                    motion_activity=window.motion_activity,
                    motion_x=window.motion_x,
                    motion_y=window.motion_y,
                    direction_confidence=window.direction_confidence,
                    reverse_stream_sha256=window.reverse_stream_sha256,
                    recovery_frame=window.recovery_frame,
                )
            )
    return _rewrite_prediction_stream(data, units, vops, counts, replacements, events)


def _transform_scatter_operation(data: bytes, operation: DatamoshOperation) -> DatamoshTransform:
    """Inject bounded multi-time fragment prediction into the ordered main stream."""
    units = parse_mpeg4_units(data)
    vops = vop_units(units)
    counts = vop_type_counts(units)
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    replacements: dict[int, bytes] = {}
    events: list[DatamoshEvent] = []
    occupied: set[int] = set()
    for window in operation.prepared_scatter_windows:
        if not window.prediction_vops:
            raise DatamoshError("SCATTER prepared a fragment window without P prediction material.")
        offsets = {fragment.temporal_offset for fragment in window.fragments}
        if len(offsets) < 2 or 0 in offsets:
            raise DatamoshError(
                "SCATTER requires at least two distinct non-current temporal fragment offsets."
            )
        if not (
            start <= window.source_start_frame
            <= window.episode_start_frame
            < window.recovery_frame
            <= window.source_end_frame
            <= end
        ):
            raise DatamoshError(
                "SCATTER prepared a fragment window outside its protected temporal bounds: "
                f"episode {window.episode_start_frame}:{window.recovery_frame}, "
                f"source {window.source_start_frame}:{window.source_end_frame}, "
                f"operation {start}:{end}."
            )
        if window.recovery_frame in window.target_frames:
            raise DatamoshError("SCATTER attempted to overwrite its clean recovery anchor.")
        if (
            _range_hits_protected(window.source_start_frame, window.source_end_frame, protected)
            or _range_hits_protected(
                window.episode_start_frame,
                window.recovery_frame,
                protected,
            )
        ):
            raise DatamoshError("SCATTER prepared a window across protected Style FX coverage.")

        applied_targets: list[int] = []
        suppressed_resets: list[int] = []
        for target in window.target_frames:
            if not (window.episode_start_frame < target < window.recovery_frame):
                raise DatamoshError(f"SCATTER prepared an invalid main-stream VOP target: {target}.")
            if target in occupied:
                continue
            prediction_index = target - window.episode_start_frame - 1
            if prediction_index >= len(window.prediction_vops):
                raise DatamoshError(
                    "SCATTER prepared too few prediction VOPs for target frame "
                    f"{target}: {len(window.prediction_vops)} available."
                )
            replacements[vops[target].index] = window.prediction_vops[prediction_index]
            occupied.add(target)
            applied_targets.append(target)
            if vops[target].coding_type == 0:
                suppressed_resets.append(target)
        if not applied_targets:
            continue

        prepared_hash = (
            window.prepared_frame_sha256s[0]
            if window.prepared_frame_sha256s
            else None
        )
        events.append(
            DatamoshEvent(
                operation="SCATTER_MULTI_TIME_FRAGMENTATION",
                mode=DATAMOSH_MODE_SCATTER,
                frame=window.episode_start_frame,
                absolute_frame=operation.absolute_frame_offset + window.episode_start_frame,
                source_p_frame=window.provenance_frame,
                repeated_at_frames=tuple(applied_targets),
                motion_activity=window.motion_activity,
                scatter_fragments=window.fragments,
                scatter_provenance_frame=window.provenance_frame,
                scatter_stream_sha256=window.prepared_stream_sha256,
                scatter_prepared_frame_sha256=prepared_hash,
                recovery_frame=window.recovery_frame,
            )
        )
        for reset_frame in suppressed_resets:
            events.append(
                DatamoshEvent(
                    operation="SCATTER_I_RESET_SUPPRESSED_WITH_FRAGMENT_P",
                    mode=DATAMOSH_MODE_SCATTER,
                    frame=reset_frame,
                    absolute_frame=operation.absolute_frame_offset + reset_frame,
                    source_p_frame=window.provenance_frame,
                    motion_activity=window.motion_activity,
                    scatter_stream_sha256=window.prepared_stream_sha256,
                    recovery_frame=window.recovery_frame,
                )
            )
    return _rewrite_prediction_stream(data, units, vops, counts, replacements, events)


def _transform_bleed_operation(data: bytes, operation: DatamoshOperation) -> DatamoshTransform:
    """Carry outgoing prediction payloads into selected incoming clip ranges."""
    if operation.planning_source_sha256 is not None:
        return _apply_planned_operation(data, operation)
    units = parse_mpeg4_units(data)
    vops = vop_units(units)
    counts = vop_type_counts(units)
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    targets = tuple(
        target
        for target in operation.transitions
        if start < target.frame < end
        and target.frame > 0
        and vops[target.frame - 1].coding_type == 1
        and vops[target.frame].coding_type in (0, 1)
        and not _frame_is_protected(target.frame, protected)
        and not _frame_is_protected(target.frame - 1, protected)
    )
    limit = _bleed_target_limit(operation.intensity, len(targets))
    selected = sorted(
        sorted(
            targets,
            key=lambda target: _stable_score(
                operation.seed,
                30,
                target.absolute_frame,
                salt=operation.salt,
            ),
        )[:limit],
        key=lambda target: target.frame,
    )
    if not selected:
        return _unchanged_transform(data, units, counts)

    amount = max(0.0, min(1.0, operation.intensity / 2.0))
    all_transition_frames = sorted(
        {target.frame for target in operation.transitions}
        | set(_protection_boundaries(protected, start, end))
    )
    replacements: dict[int, bytes] = {}
    events: list[DatamoshEvent] = []
    for target in selected:
        frame = target.frame
        score = _stable_score(
            operation.seed,
            31,
            target.absolute_frame,
            salt=operation.salt,
        )
        if amount < 0.40:
            requested, stride = 2 + score % 3, 2
        elif amount < 0.75:
            requested, stride = 6 + score % 7, 1 + (score // 7) % 2
        else:
            requested, stride = 14 + score % 13, 1
        next_transition = next(
            (later for later in all_transition_frames if later > frame),
            end,
        )
        recovery_anchors = [
            later
            for later in range(frame + 1, next_transition)
            if vops[later].coding_type == 0
        ]
        recovery_anchor = recovery_anchors[-1] if recovery_anchors else next_transition
        window_end = min(end, next_transition, recovery_anchor, frame + requested + 1)
        source_position = frame - 1
        source = vops[source_position]
        replacements[vops[frame].index] = source.data
        events.append(
            DatamoshEvent(
                operation="BLEED_TRANSITION_I_RESET_SUPPRESSED_WITH_P",
                mode=DATAMOSH_MODE_BLEED,
                frame=frame,
                absolute_frame=operation.absolute_frame_offset + frame,
                source_p_frame=source_position,
                transition_absolute_frame=target.absolute_frame,
                transition_from_kind=target.from_kind,
                transition_to_kind=target.to_kind,
                visual_transition=target.visual_transition,
                recovery_frame=recovery_anchor,
            )
        )
        repeated: list[int] = []
        for later in range(frame + 1, window_end):
            if _frame_is_protected(later, protected):
                break
            if vops[later].coding_type == 0:
                replacements[vops[later].index] = source.data
                events.append(
                    DatamoshEvent(
                        operation="BLEED_RECOVERY_I_RESET_SUPPRESSED_WITH_P",
                        mode=DATAMOSH_MODE_BLEED,
                        frame=later,
                        absolute_frame=operation.absolute_frame_offset + later,
                        source_p_frame=source_position,
                        transition_absolute_frame=target.absolute_frame,
                        transition_from_kind=target.from_kind,
                        transition_to_kind=target.to_kind,
                        visual_transition=target.visual_transition,
                        recovery_frame=recovery_anchor,
                    )
                )
                continue
            if vops[later].coding_type != 1 or (later - frame - 1) % stride:
                continue
            replacements[vops[later].index] = source.data
            repeated.append(later)
        if repeated:
            events.append(
                DatamoshEvent(
                    operation="BLEED_TRANSITION_P_PERSISTENCE_REPEAT",
                    mode=DATAMOSH_MODE_BLEED,
                    frame=repeated[0],
                    absolute_frame=operation.absolute_frame_offset + repeated[0],
                    source_p_frame=source_position,
                    repeated_at_frames=tuple(repeated),
                    transition_absolute_frame=target.absolute_frame,
                    transition_from_kind=target.from_kind,
                    transition_to_kind=target.to_kind,
                    visual_transition=target.visual_transition,
                    recovery_frame=recovery_anchor,
                )
            )
    return _rewrite_prediction_stream(data, units, vops, counts, replacements, events)


def _rewrite_prediction_stream(
    data: bytes,
    units: tuple[Mpeg4Unit, ...],
    vops: tuple[Mpeg4Unit, ...],
    counts: dict[str, int],
    replacements: dict[int, bytes],
    events: list[DatamoshEvent],
) -> DatamoshTransform:
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
            "DATAMOSH operation changed VOP count unexpectedly: "
            f"{len(vops)} input, {len(transformed_vops)} transformed."
        )
    mutated_counts = vop_type_counts(transformed_units)
    if mutated_counts["B"] or mutated_counts["S"]:
        raise DatamoshError("DATAMOSH operation introduced an unsupported VOP type.")
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


def _operation_bounds(operation: DatamoshOperation, frame_count: int) -> tuple[int, int]:
    start = max(0, min(frame_count, int(operation.start_frame)))
    end = max(start + 1, min(frame_count, int(operation.end_frame)))
    return start, end


def _normalized_protected_intervals(
    intervals: tuple[tuple[int, int], ...],
    start: int,
    end: int,
) -> tuple[tuple[int, int], ...]:
    candidates: list[tuple[int, int]] = []
    for raw in intervals:
        try:
            left, right = int(raw[0]), int(raw[1])
        except (TypeError, ValueError, IndexError):
            continue
        left = max(start, min(end, left))
        right = max(left, min(end, right))
        if right <= left:
            continue
        candidates.append((left, right))
    normalized: list[tuple[int, int]] = []
    for left, right in sorted(candidates):
        if normalized and left <= normalized[-1][1]:
            normalized[-1] = (normalized[-1][0], max(normalized[-1][1], right))
        else:
            normalized.append((left, right))
    return tuple(normalized)


def _operation_protected_intervals(
    operation: DatamoshOperation,
    frame_count: int,
) -> tuple[tuple[int, int], ...]:
    start, end = _operation_bounds(operation, frame_count)
    return _normalized_protected_intervals(operation.protected_intervals, start, end)


def _frame_is_protected(
    frame: int,
    intervals: tuple[tuple[int, int], ...],
) -> bool:
    return any(start <= frame < end for start, end in intervals)


def _range_hits_protected(
    start: int,
    end: int,
    intervals: tuple[tuple[int, int], ...],
) -> bool:
    """Return whether half-open [start, end) overlaps a protected interval."""
    return any(start < protected_end and end > protected_start for protected_start, protected_end in intervals)


def _protection_boundaries(
    intervals: tuple[tuple[int, int], ...],
    start: int,
    end: int,
) -> tuple[int, ...]:
    return tuple(
        sorted(
            {
                boundary
                for interval in intervals
                for boundary in interval
                if start < boundary < end
            }
        )
    )


def _operation_parameter(
    operation: DatamoshOperation,
    name: str,
    default: int | float | str,
) -> int | float | str:
    return dict(operation.parameters).get(name, default)


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, int(round((len(values) - 1) * fraction))))
    return values[index]


def _bleed_target_limit(intensity: float, count: int) -> int:
    if count <= 0 or intensity <= 0.0:
        return 0
    amount = max(0.0, min(1.0, intensity / 2.0))
    coverage = 0.25 + 0.75 * amount
    return min(count, max(1, int(math.ceil(count * coverage))))


def _plan_skrrt_windows(
    operation: DatamoshOperation,
    vops: tuple[Mpeg4Unit, ...],
) -> tuple[_SkrrtWindowPlan, ...]:
    """Select bounded motion-led episodes before any reverse material is decoded."""
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    activity_by_frame = {
        sample.frame: sample
        for sample in operation.activity
        if start < sample.frame < end
        and not _frame_is_protected(sample.frame, protected)
    }
    raw_candidates = [
        frame
        for frame, sample in activity_by_frame.items()
        if sample.motion_activity >= 0.012
        and frame > start + 2
        and frame < end - 2
        and vops[frame].coding_type == 1
    ]
    if not raw_candidates:
        return ()

    amount = max(0.0, min(1.0, operation.intensity / 2.0))
    fps = max(1, int(_operation_parameter(operation, "fps", 8)))
    transition_frames = sorted(
        {
            target.frame
            for target in operation.transitions
            if start < target.frame < end
        }
    )
    boundaries = [
        start,
        *sorted(set(transition_frames) | set(_protection_boundaries(protected, start, end))),
        end,
    ]
    quantile = max(0.38, 0.84 - 0.46 * amount)

    def shot_bounds(frame: int) -> tuple[int, int]:
        left = max(boundary for boundary in boundaries if boundary <= frame)
        right = min(boundary for boundary in boundaries if boundary > frame)
        return left, right

    def rank(frame: int) -> tuple[float, int]:
        sample = activity_by_frame[frame]
        directional_preference = 0.85 + 0.15 * max(
            0.0,
            min(1.0, float(sample.direction_confidence)),
        )
        return (
            -float(sample.motion_activity) * directional_preference,
            _stable_score(
                operation.seed,
                40,
                sample.absolute_frame,
                salt=operation.salt,
            ),
        )

    eligible: list[int] = []
    shot_peaks: list[int] = []
    for left, right in zip(boundaries, boundaries[1:]):
        local = [frame for frame in raw_candidates if left < frame < right]
        if not local:
            continue
        threshold = max(
            0.012,
            _quantile(
                sorted(float(activity_by_frame[frame].motion_activity) for frame in local),
                quantile,
            ),
        )
        local_eligible = [
            frame
            for frame in local
            if float(activity_by_frame[frame].motion_activity) >= threshold
        ]
        if amount >= 0.75:
            local_eligible.sort(key=lambda frame: (frame, rank(frame)))
        else:
            local_eligible.sort(key=rank)
        if local_eligible:
            shot_peaks.append(local_eligible[0])
            eligible.extend(local_eligible)
    if not eligible:
        return ()

    motion_peak = max(float(activity_by_frame[frame].motion_activity) for frame in eligible)
    motion_scale = max(0.0, min(1.0, (motion_peak - 0.012) / 0.288))
    duration_frames = max(1, end - start)
    max_episodes = min(
        len(set(eligible)),
        max(
            1,
            int(
                math.ceil(
                    (duration_frames / fps)
                    * (0.08 + 0.28 * amount)
                    * (0.45 + 0.55 * motion_scale)
                )
            ),
        ),
    )

    def plan_for(frame: int) -> _SkrrtWindowPlan | None:
        sample = activity_by_frame[frame]
        score = _stable_score(
            operation.seed,
            41,
            sample.absolute_frame,
            salt=operation.salt,
        )
        if amount < 0.40:
            requested_depth = max(3, min(6, int(round(fps * 0.50))))
            requested_duration = requested_depth + max(2, int(round(fps * 0.30))) + score % 2
            stride = 2
        elif amount < 0.75:
            requested_depth = max(5, min(10, int(round(fps * 0.80))))
            requested_duration = requested_depth + max(3, int(round(fps * 0.75))) + score % max(2, fps // 3)
            stride = 1 + int(score % 4 == 0)
        else:
            requested_depth = max(7, min(18, int(round(fps * 1.25))))
            requested_duration = requested_depth + max(6, int(round(fps * 1.50))) + score % max(2, fps // 2)
            stride = 1

        left, right = shot_bounds(frame)
        source_start = frame - requested_depth + 1
        if source_start < left or frame - source_start + 1 < 3:
            return None
        source_end = frame + 1
        minimum_recovery = frame + max(3, requested_duration)
        recovery_candidates = [
            candidate
            for candidate in range(minimum_recovery, min(end, right) + 1)
            if candidate < len(vops) and vops[candidate].coding_type == 0
        ]
        if not recovery_candidates:
            shorter_recovery_candidates = [
                candidate
                for candidate in range(frame + 3, min(end, right) + 1)
                if candidate < len(vops) and vops[candidate].coding_type == 0
            ]
            if not shorter_recovery_candidates:
                return None
            recovery = shorter_recovery_candidates[-1]
        else:
            recovery = recovery_candidates[0]
        targets = tuple(
            candidate
            for candidate in range(frame + 1, recovery)
            if vops[candidate].coding_type == 0
            or (candidate - frame - 1) % stride == 0
        )
        if not targets:
            return None
        return _SkrrtWindowPlan(
            episode_start_frame=frame,
            episode_end_frame=recovery,
            source_start_frame=source_start,
            source_end_frame=source_end,
            target_frames=targets,
            recovery_frame=recovery,
            replacement_stride=stride,
            motion_activity=max(0.0, min(1.0, float(sample.motion_activity))),
            motion_x=max(-1.0, min(1.0, float(sample.motion_x))),
            motion_y=max(-1.0, min(1.0, float(sample.motion_y))),
            direction_confidence=max(0.0, min(1.0, float(sample.direction_confidence))),
        )

    ordered_candidates = [
        *sorted(set(shot_peaks), key=rank),
        *sorted((frame for frame in set(eligible) if frame not in shot_peaks), key=rank),
    ]
    selected: list[_SkrrtWindowPlan] = []
    cooldown = max(2, int(round(fps * (0.80 - 0.30 * amount))))
    for frame in ordered_candidates:
        plan = plan_for(frame)
        if plan is None:
            continue
        if any(
            not (
                plan.episode_start_frame >= prior.episode_end_frame + cooldown
                or prior.episode_start_frame >= plan.episode_end_frame + cooldown
            )
            for prior in selected
        ):
            continue
        selected.append(plan)
        if len(selected) >= max_episodes:
            break
    return tuple(sorted(selected, key=lambda plan: plan.episode_start_frame))


def _scale_scatter_region(
    region: DatamoshSpatialRegion,
    *,
    scale: float,
) -> DatamoshSpatialRegion:
    center_x = float(region.x) + float(region.width) * 0.5
    center_y = float(region.y) + float(region.height) * 0.5
    width = max(0.08, min(0.46, float(region.width) * scale))
    height = max(0.08, min(0.46, float(region.height) * scale))
    x = max(0.0, min(1.0 - width, center_x - width * 0.5))
    y = max(0.0, min(1.0 - height, center_y - height * 0.5))
    return DatamoshSpatialRegion(
        x=x,
        y=y,
        width=width,
        height=height,
        weight=max(0.0, min(1.0, float(region.weight))),
    )


def _plan_scatter_windows(
    operation: DatamoshOperation,
    vops: tuple[Mpeg4Unit, ...],
) -> tuple[_ScatterWindowPlan, ...]:
    """Select sparse material-led windows before bounded fragment preparation."""
    start, end = _operation_bounds(operation, len(vops))
    protected = _operation_protected_intervals(operation, len(vops))
    activity_by_frame = {
        sample.frame: sample
        for sample in operation.activity
        if start < sample.frame < end
        and len(sample.spatial_regions) >= 2
        and not _frame_is_protected(sample.frame, protected)
    }
    raw_candidates = [
        frame
        for frame, sample in activity_by_frame.items()
        if sample.motion_activity >= 0.012
        and frame > start + 2
        and frame < end - 2
        and vops[frame].coding_type == 1
    ]
    if not raw_candidates:
        return ()

    amount = max(0.0, min(1.0, operation.intensity / 2.0))
    fps = max(1, int(_operation_parameter(operation, "fps", 8)))
    transition_frames = sorted(
        {
            target.frame
            for target in operation.transitions
            if start < target.frame < end
        }
    )
    boundaries = [
        start,
        *sorted(set(transition_frames) | set(_protection_boundaries(protected, start, end))),
        end,
    ]

    def shot_bounds(frame: int) -> tuple[int, int]:
        left = max(boundary for boundary in boundaries if boundary <= frame)
        right = min(boundary for boundary in boundaries if boundary > frame)
        return left, right

    def material_score(frame: int) -> float:
        sample = activity_by_frame[frame]
        structure = 0.58 + 0.24 * float(sample.texture_activity) + 0.18 * float(sample.edge_activity)
        return float(sample.motion_activity) * structure

    def rank(frame: int) -> tuple[float, int]:
        sample = activity_by_frame[frame]
        return (
            -material_score(frame),
            _stable_score(
                operation.seed,
                50,
                sample.absolute_frame,
                salt=operation.salt,
            ),
        )

    quantile = max(0.40, 0.86 - 0.44 * amount)
    eligible: list[int] = []
    shot_peaks: list[int] = []
    for left, right in zip(boundaries, boundaries[1:]):
        local = [frame for frame in raw_candidates if left < frame < right]
        if not local:
            continue
        threshold = max(
            0.012,
            _quantile(sorted(material_score(frame) for frame in local), quantile),
        )
        local_eligible = [frame for frame in local if material_score(frame) >= threshold]
        local_eligible.sort(key=rank)
        if local_eligible:
            shot_peaks.append(local_eligible[0])
            eligible.extend(local_eligible)
    if not eligible:
        return ()

    peak = max(material_score(frame) for frame in eligible)
    activity_scale = max(0.0, min(1.0, (peak - 0.012) / 0.288))
    max_episodes = min(
        len(set(eligible)),
        max(
            1,
            int(
                math.ceil(
                    ((end - start) / fps)
                    * (0.06 + 0.22 * amount)
                    * (0.45 + 0.55 * activity_scale)
                )
            ),
        ),
    )

    def plan_for(frame: int) -> _ScatterWindowPlan | None:
        sample = activity_by_frame[frame]
        score = _stable_score(
            operation.seed,
            51,
            sample.absolute_frame,
            salt=operation.salt,
        )
        if amount < 0.40:
            fragment_count = 2
            depth = max(2, min(4, int(round(fps * 0.38))))
            duration = max(4, int(round(fps * 0.62))) + score % 2
            stride = 2
            region_scale = 0.72
        elif amount < 0.75:
            fragment_count = 3
            depth = max(4, min(7, int(round(fps * 0.75))))
            duration = max(8, int(round(fps * 1.10))) + score % max(2, fps // 3)
            stride = 1 + int(score % 5 == 0)
            region_scale = 0.86
        else:
            fragment_count = min(5, len(sample.spatial_regions))
            depth = max(6, min(11, int(round(fps * 1.15))))
            duration = max(12, int(round(fps * 1.75))) + score % max(2, fps // 2)
            stride = 1
            region_scale = 1.00

        left, right = shot_bounds(frame)
        positive = max(1, depth // 2)
        offset_palette = (-depth, positive, -max(1, depth // 2), max(1, positive // 2), -1)
        rotation = score % len(offset_palette)
        rotated = offset_palette[rotation:] + offset_palette[:rotation]
        offsets: list[int] = []
        for offset in rotated:
            if offset and offset not in offsets:
                offsets.append(offset)
            if len(offsets) >= fragment_count:
                break
        if len(offsets) < 2 or not any(offset > 0 for offset in offsets) or not any(offset < 0 for offset in offsets):
            return None
        minimum_offset = min(offsets)
        maximum_offset = max(offsets)
        if frame + minimum_offset < left:
            return None

        minimum_recovery = frame + max(4, duration)
        maximum_recovery = min(end - 1, right - maximum_offset)
        recovery_candidates = [
            candidate
            for candidate in range(minimum_recovery, maximum_recovery + 1)
            if candidate < len(vops) and vops[candidate].coding_type == 0
        ]
        if not recovery_candidates:
            shorter_candidates = [
                candidate
                for candidate in range(frame + 4, maximum_recovery + 1)
                if candidate < len(vops) and vops[candidate].coding_type == 0
            ]
            if not shorter_candidates:
                return None
            recovery = shorter_candidates[-1]
        else:
            recovery = recovery_candidates[0]
        episode_frames = recovery - frame
        if episode_frames < 4:
            return None

        ranked_regions = sorted(
            sample.spatial_regions,
            key=lambda region: (
                -float(region.weight),
                _stable_score(
                    operation.seed,
                    52,
                    sample.absolute_frame + int(round(region.x * 1000.0)) + int(round(region.y * 1000.0)),
                    salt=operation.salt,
                ),
            ),
        )[:fragment_count]
        if len(ranked_regions) < 2:
            return None
        fragments = tuple(
            ScatterTemporalFragment(
                fragment_id=index,
                region=_scale_scatter_region(region, scale=region_scale),
                temporal_offset=offsets[index],
                resolve_after_frame=max(
                    2,
                    min(
                        episode_frames,
                        int(
                            round(
                                episode_frames
                                * (0.58 + 0.34 * amount - 0.08 * index / max(1, fragment_count - 1))
                            )
                        ),
                    ),
                ),
            )
            for index, region in enumerate(ranked_regions)
        )
        targets = tuple(
            candidate
            for candidate in range(frame + 1, recovery)
            if vops[candidate].coding_type == 0
            or (candidate - frame - 1) % stride == 0
        )
        if not targets:
            return None
        return _ScatterWindowPlan(
            episode_start_frame=frame,
            episode_end_frame=recovery,
            source_start_frame=frame + minimum_offset,
            source_end_frame=recovery + maximum_offset,
            target_frames=targets,
            recovery_frame=recovery,
            replacement_stride=stride,
            fragments=fragments,
            motion_activity=max(0.0, min(1.0, float(sample.motion_activity))),
            texture_activity=max(0.0, min(1.0, float(sample.texture_activity))),
            edge_activity=max(0.0, min(1.0, float(sample.edge_activity))),
        )

    ordered_candidates = [
        *sorted(set(shot_peaks), key=rank),
        *sorted((frame for frame in set(eligible) if frame not in shot_peaks), key=rank),
    ]
    selected: list[_ScatterWindowPlan] = []
    cooldown = max(2, int(round(fps * (0.90 - 0.34 * amount))))
    for frame in ordered_candidates:
        plan = plan_for(frame)
        if plan is None:
            continue
        if any(
            not (
                plan.episode_start_frame >= prior.episode_end_frame + cooldown
                or prior.episode_start_frame >= plan.episode_end_frame + cooldown
            )
            for prior in selected
        ):
            continue
        selected.append(plan)
        if len(selected) >= max_episodes:
            break
    return tuple(sorted(selected, key=lambda plan: plan.episode_start_frame))


def _prepare_skrrt_operations(
    controlled_stream: Path,
    temporary: Path,
    controlled_vops: tuple[Mpeg4Unit, ...],
    operations: tuple[DatamoshOperation, ...],
    *,
    fps: int,
    log: LogCallback,
) -> tuple[tuple[DatamoshOperation, ...], _SkrrtPreparationTiming]:
    planning_started = time.perf_counter()
    plans_by_index: dict[int, tuple[_SkrrtWindowPlan, ...]] = {
        index: _plan_skrrt_windows(operation, controlled_vops)
        for index, operation in enumerate(operations)
        if operation.enabled
        and operation.intensity > 0.0
        and operation.mode == DATAMOSH_MODE_SKRRT
    }
    planned_count = sum(len(plans) for plans in plans_by_index.values())
    if not planned_count:
        return operations, _SkrrtPreparationTiming(
            preparation_seconds=time.perf_counter() - planning_started,
        )

    temporal_root = temporary / "temporal_preparation"
    reverse_root = temporal_root / "skrrt"
    reverse_root.mkdir(parents=True)
    try:
        indexed_source, index_created = _ensure_indexed_prediction_source(
            controlled_stream,
            temporal_root,
            fps=fps,
            log=log,
        )
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - identify the SKRRT preparation boundary.
        raise DatamoshError(f"SKRRT reverse-window extraction/preparation failed: {exc}") from exc
    preparation_seconds = time.perf_counter() - planning_started

    prepared_by_index: dict[int, tuple[SkrrtPreparedWindow, ...]] = {}
    reverse_decode_seconds = 0.0
    zone_composition_seconds = 0.0
    auxiliary_encode_seconds = 0.0
    auxiliary_encode_count = 0
    structural_validation_seconds = 0.0
    for operation_index, plans in plans_by_index.items():
        operation = operations[operation_index]
        width = int(_operation_parameter(operation, "width", 0))
        height = int(_operation_parameter(operation, "height", 0))
        if operation.zone_box is not None and (width <= 0 or height <= 0):
            raise DatamoshError(
                "SKRRT Zone preparation requires positive output dimensions, "
                f"found {width}x{height}."
            )
        prepared: list[SkrrtPreparedWindow] = []
        for window_index, plan in enumerate(plans):
            prefix = f"operation_{operation_index:02d}_window_{window_index:03d}"
            forward_window = reverse_root / f"{prefix}_forward.mkv"
            source_rgb = reverse_root / f"{prefix}_source.rgb"
            current_rgb = reverse_root / f"{prefix}_current.rgb"
            prepared_rgb = reverse_root / f"{prefix}_prepared.rgb"
            reverse_stream = reverse_root / f"{prefix}_reverse.m4v"
            spatial_evidence: dict[str, object] = {}
            decode_started = time.perf_counter()
            try:
                if operation.zone_box is None:
                    _extract_skrrt_reverse_window(
                        indexed_source,
                        forward_window,
                        plan,
                        fps=fps,
                        log=log,
                    )
                else:
                    frame_count = plan.source_end_frame - plan.source_start_frame
                    _extract_skrrt_rgb_window(
                        indexed_source,
                        source_rgb,
                        start_frame=plan.source_start_frame,
                        frame_count=frame_count,
                        width=width,
                        height=height,
                        fps=fps,
                        log=log,
                    )
                    _extract_skrrt_rgb_window(
                        indexed_source,
                        current_rgb,
                        start_frame=plan.episode_start_frame,
                        frame_count=frame_count,
                        width=width,
                        height=height,
                        fps=fps,
                        log=log,
                    )
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - identify the SKRRT extraction boundary.
                raise DatamoshError(
                    f"SKRRT reverse-window extraction/preparation failed: {exc}"
                ) from exc
            decode_seconds = time.perf_counter() - decode_started
            reverse_decode_seconds += decode_seconds

            if operation.zone_box is not None:
                composition_started = time.perf_counter()
                spatial_evidence = _compose_skrrt_zone_frames(
                    current_rgb,
                    source_rgb,
                    prepared_rgb,
                    frame_count=plan.source_end_frame - plan.source_start_frame,
                    width=width,
                    height=height,
                    zone_box=operation.zone_box,
                )
                zone_composition_seconds += time.perf_counter() - composition_started

            encode_started = time.perf_counter()
            try:
                if operation.zone_box is None:
                    _encode_skrrt_reverse_prediction(
                        forward_window,
                        reverse_stream,
                        plan,
                        fps=fps,
                        log=log,
                    )
                else:
                    _encode_skrrt_zone_prediction(
                        prepared_rgb,
                        reverse_stream,
                        plan,
                        width=width,
                        height=height,
                        fps=fps,
                        log=log,
                    )
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - identify the SKRRT auxiliary encode boundary.
                raise DatamoshError(f"SKRRT auxiliary reverse encode failed: {exc}") from exc
            encode_seconds = time.perf_counter() - encode_started
            auxiliary_encode_seconds += encode_seconds
            auxiliary_encode_count += 1

            validation_started = time.perf_counter()
            try:
                reverse_data = reverse_stream.read_bytes()
                expected_count = plan.source_end_frame - plan.source_start_frame
                reverse_vops = _validate_auxiliary_prediction_structure(
                    reverse_data,
                    expected_count=expected_count,
                    mode_label="SKRRT reverse",
                    window_number=window_index + 1,
                    source_start_frame=plan.source_start_frame,
                    source_end_frame=plan.source_end_frame,
                )
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - normalize reverse-material validation errors.
                raise DatamoshError(f"SKRRT auxiliary reverse encode failed: {exc}") from exc
            validation_seconds = time.perf_counter() - validation_started
            structural_validation_seconds += validation_seconds

            chronological = tuple(range(plan.source_start_frame, plan.source_end_frame))
            prepared.append(
                SkrrtPreparedWindow(
                    episode_start_frame=plan.episode_start_frame,
                    episode_end_frame=plan.episode_end_frame,
                    source_start_frame=plan.source_start_frame,
                    source_end_frame=plan.source_end_frame,
                    source_chronological_order=chronological,
                    source_reversed_order=tuple(reversed(chronological)),
                    target_frames=plan.target_frames,
                    recovery_frame=plan.recovery_frame,
                    replacement_stride=plan.replacement_stride,
                    motion_activity=plan.motion_activity,
                    motion_x=plan.motion_x,
                    motion_y=plan.motion_y,
                    direction_confidence=plan.direction_confidence,
                    reverse_stream_sha256=_sha256(reverse_data),
                    prediction_vops=tuple(unit.data for unit in reverse_vops[1:]),
                    reverse_vop_count=len(reverse_vops),
                    reverse_decode_seconds=decode_seconds,
                    auxiliary_encode_seconds=encode_seconds,
                    structural_validation_seconds=validation_seconds,
                    temporary_disk_bytes=sum(
                        path.stat().st_size
                        for path in (
                            forward_window,
                            source_rgb,
                            current_rgb,
                            prepared_rgb,
                            reverse_stream,
                        )
                        if path.is_file()
                    ),
                    zone_box=operation.zone_box,
                    current_frame_sha256s=tuple(
                        spatial_evidence.get("current_frame_sha256s", ())
                    ),
                    reverse_source_frame_sha256s=tuple(
                        spatial_evidence.get("reverse_source_frame_sha256s", ())
                    ),
                    prepared_frame_sha256s=tuple(
                        spatial_evidence.get("prepared_frame_sha256s", ())
                    ),
                    prepared_inside_exact=bool(
                        spatial_evidence.get("prepared_inside_exact", False)
                    ),
                    prepared_outside_exact=bool(
                        spatial_evidence.get("prepared_outside_exact", False)
                    ),
                )
            )
        prepared_by_index[operation_index] = tuple(prepared)

    prepared_operations = tuple(
        replace(operation, prepared_windows=prepared_by_index.get(index, ()))
        for index, operation in enumerate(operations)
    )
    temporary_disk_bytes = sum(
        path.stat().st_size
        for path in reverse_root.rglob("*")
        if path.is_file()
    )
    if index_created:
        temporary_disk_bytes += indexed_source.stat().st_size
    _log(
        log,
        "SKRRT reverse preparation: "
        f"{planned_count} bounded episode(s), {auxiliary_encode_count} auxiliary encode(s), "
        f"{temporary_disk_bytes} temporary byte(s).",
    )
    return prepared_operations, _SkrrtPreparationTiming(
        preparation_seconds=preparation_seconds,
        reverse_decode_seconds=reverse_decode_seconds,
        zone_composition_seconds=zone_composition_seconds,
        auxiliary_encode_seconds=auxiliary_encode_seconds,
        auxiliary_encode_count=auxiliary_encode_count,
        structural_validation_seconds=structural_validation_seconds,
        temporary_disk_bytes=temporary_disk_bytes,
    )


def _ensure_indexed_prediction_source(
    controlled_stream: Path,
    temporal_root: Path,
    *,
    fps: int,
    log: LogCallback,
) -> tuple[Path, bool]:
    temporal_root.mkdir(parents=True, exist_ok=True)
    destination = temporal_root / "indexed_prediction_source.mp4"
    if destination.is_file():
        return destination, False
    _index_temporal_prediction_source(
        controlled_stream,
        destination,
        fps=fps,
        log=log,
    )
    return destination, True


def _index_temporal_prediction_source(
    controlled_stream: Path,
    destination: Path,
    *,
    fps: int,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "m4v",
                "-r",
                str(fps),
                "-i",
                str(controlled_stream),
                "-map",
                "0:v:0",
                "-an",
                "-c:v",
                "copy",
                "-movflags",
                "+faststart",
                str(destination),
            ],
            log,
        )
    except Exception as exc:  # noqa: BLE001 - caller identifies the temporal preparation mode.
        raise RuntimeError(f"bounded temporal index failed: {exc}") from exc


def _extract_skrrt_reverse_window(
    indexed_source: Path,
    destination: Path,
    plan: _SkrrtWindowPlan,
    *,
    fps: int,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    expected_count = plan.source_end_frame - plan.source_start_frame
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{plan.source_start_frame / fps:.9f}",
                "-i",
                str(indexed_source),
                "-map",
                "0:v:0",
                "-an",
                "-frames:v",
                str(expected_count),
                "-c:v",
                "ffv1",
                "-level",
                "3",
                "-pix_fmt",
                "yuv420p",
                "-fps_mode",
                "cfr",
                str(destination),
            ],
            log,
        )
        decoded_count = _probe_decoded_frame_count(destination)
        if decoded_count != expected_count:
            raise DatamoshError(
                "SKRRT reverse-window extraction frame count mismatch: "
                f"expected {expected_count}, found {decoded_count}."
            )
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert tool failure at the extraction boundary.
        raise DatamoshError(f"SKRRT reverse-window extraction/preparation failed: {exc}") from exc


def _extract_skrrt_rgb_window(
    indexed_source: Path,
    destination: Path,
    *,
    start_frame: int,
    frame_count: int,
    width: int,
    height: int,
    fps: int,
    log: LogCallback,
) -> None:
    """Decode one bounded controlled-stream window as exact full-size RGB frames."""
    if start_frame < 0 or frame_count <= 0 or width <= 0 or height <= 0:
        raise DatamoshError(
            "SKRRT Zone extraction received invalid bounded RGB parameters: "
            f"start {start_frame}, count {frame_count}, size {width}x{height}."
        )
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{start_frame / fps:.9f}",
                "-i",
                str(indexed_source),
                "-map",
                "0:v:0",
                "-an",
                "-frames:v",
                str(frame_count),
                "-pix_fmt",
                "rgb24",
                "-fps_mode",
                "cfr",
                "-f",
                "rawvideo",
                str(destination),
            ],
            log,
        )
        expected_size = frame_count * width * height * 3
        actual_size = destination.stat().st_size
        if actual_size != expected_size:
            raise DatamoshError(
                "SKRRT Zone RGB extraction size mismatch: "
                f"expected {expected_size}, found {actual_size}."
            )
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize bounded RGB extraction failures.
        raise DatamoshError(
            f"SKRRT reverse-window extraction/preparation failed: {exc}"
        ) from exc


def _compose_skrrt_zone_frames(
    current_source: Path,
    reverse_source: Path,
    destination: Path,
    *,
    frame_count: int,
    width: int,
    height: int,
    zone_box: tuple[int, int, int, int],
) -> dict[str, object]:
    """Envelope authentic reverse-source pixels inside one resolved output Zone."""
    if (
        not isinstance(zone_box, tuple)
        or len(zone_box) != 4
        or any(isinstance(value, bool) or not isinstance(value, int) for value in zone_box)
    ):
        raise DatamoshError(f"SKRRT received invalid resolved Zone geometry: {zone_box!r}.")
    left, top, right, bottom = zone_box
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise DatamoshError(
            "SKRRT received invalid resolved Zone geometry: "
            f"{zone_box!r} for {width}x{height}."
        )
    expected_shape = (frame_count, height, width, 3)
    expected_size = frame_count * height * width * 3
    try:
        current_bytes = current_source.read_bytes()
        reverse_bytes = reverse_source.read_bytes()
        if len(current_bytes) != expected_size or len(reverse_bytes) != expected_size:
            raise DatamoshError(
                "SKRRT Zone source-frame size mismatch: "
                f"expected {expected_size}, current {len(current_bytes)}, "
                f"reverse {len(reverse_bytes)}."
            )
        current = np.frombuffer(current_bytes, dtype=np.uint8).reshape(expected_shape).copy()
        chronological_source = (
            np.frombuffer(reverse_bytes, dtype=np.uint8).reshape(expected_shape).copy()
        )
        if (
            current.dtype != np.uint8
            or chronological_source.dtype != np.uint8
            or current.shape != expected_shape
            or chronological_source.shape != expected_shape
            or not current.flags.writeable
            or not chronological_source.flags.writeable
        ):
            raise DatamoshError("SKRRT Zone sources are not writable uint8 RGB frames.")

        current_hashes = tuple(_sha256(frame.tobytes()) for frame in current)
        chronological_hashes = tuple(
            _sha256(frame.tobytes()) for frame in chronological_source
        )
        reverse_ordered = chronological_source[::-1]
        prepared = current.copy()
        if np.shares_memory(prepared, current) or np.shares_memory(
            prepared,
            chronological_source,
        ):
            raise DatamoshError("SKRRT Zone prepared frames alias their source arrays.")
        prepared[:, top:bottom, left:right, :] = reverse_ordered[
            :, top:bottom, left:right, :
        ]
        if (
            prepared.dtype != np.uint8
            or prepared.shape != expected_shape
            or not prepared.flags.writeable
        ):
            raise DatamoshError("SKRRT Zone prepared frames are not writable uint8 RGB.")

        outside_mask = np.ones((height, width), dtype=bool)
        outside_mask[top:bottom, left:right] = False
        inside_exact = np.array_equal(
            prepared[:, top:bottom, left:right, :],
            reverse_ordered[:, top:bottom, left:right, :],
        )
        outside_exact = np.array_equal(
            prepared[:, outside_mask, :],
            current[:, outside_mask, :],
        )
        if not inside_exact or not outside_exact:
            raise DatamoshError(
                "SKRRT Zone prepared-frame containment validation failed: "
                f"inside_exact={inside_exact}, outside_exact={outside_exact}."
            )
        if current_hashes != tuple(_sha256(frame.tobytes()) for frame in current):
            raise DatamoshError("SKRRT Zone composition mutated current controlled frames.")
        if chronological_hashes != tuple(
            _sha256(frame.tobytes()) for frame in chronological_source
        ):
            raise DatamoshError("SKRRT Zone composition mutated reverse-source frames.")

        contiguous = np.ascontiguousarray(prepared)
        if contiguous.shape != expected_shape or contiguous.dtype != np.uint8:
            raise DatamoshError("SKRRT Zone prepared-frame normalization failed.")
        destination.write_bytes(contiguous.tobytes())
        if destination.stat().st_size != expected_size:
            raise DatamoshError("SKRRT Zone prepared-frame write was incomplete.")
        return {
            "current_frame_sha256s": current_hashes,
            "reverse_source_frame_sha256s": tuple(reversed(chronological_hashes)),
            "prepared_frame_sha256s": tuple(
                _sha256(frame.tobytes()) for frame in contiguous
            ),
            "prepared_inside_exact": True,
            "prepared_outside_exact": True,
        }
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize candidate and file failures.
        raise DatamoshError(f"SKRRT Zone prepared-frame validation failed: {exc}") from exc


def _encode_skrrt_reverse_prediction(
    source: Path,
    destination: Path,
    plan: _SkrrtWindowPlan,
    *,
    fps: int,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    frame_count = plan.source_end_frame - plan.source_start_frame
    try:
        ffmpeg_utils.run_command(
            [
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
                "-vf",
                (
                    "reverse,"
                    f"setpts=(N+{plan.episode_start_frame})/({fps}*TB),"
                    "format=yuv420p"
                ),
                *_auxiliary_prediction_codec_args(frame_count),
                "-frames:v",
                str(frame_count),
                "-r",
                str(fps),
                "-f",
                "m4v",
                str(destination),
            ],
            log,
        )
    except Exception as exc:  # noqa: BLE001 - convert tool failure at the auxiliary encode boundary.
        raise DatamoshError(f"SKRRT auxiliary reverse encode failed: {exc}") from exc


def _encode_skrrt_zone_prediction(
    source: Path,
    destination: Path,
    plan: _SkrrtWindowPlan,
    *,
    width: int,
    height: int,
    fps: int,
    log: LogCallback,
) -> None:
    """Encode validated full-size Zone-enveloped RGB frames with the shared policy."""
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    frame_count = plan.source_end_frame - plan.source_start_frame
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s:v",
                f"{width}x{height}",
                "-r",
                str(fps),
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-an",
                "-vf",
                "format=yuv420p",
                *_auxiliary_prediction_codec_args(frame_count),
                "-frames:v",
                str(frame_count),
                "-r",
                str(fps),
                "-f",
                "m4v",
                str(destination),
            ],
            log,
        )
    except Exception as exc:  # noqa: BLE001 - identify the Zone auxiliary boundary.
        raise DatamoshError(f"SKRRT auxiliary Zone encode failed: {exc}") from exc


def _prepare_scatter_operations(
    controlled_stream: Path,
    temporary: Path,
    controlled_vops: tuple[Mpeg4Unit, ...],
    operations: tuple[DatamoshOperation, ...],
    *,
    fps: int,
    log: LogCallback,
) -> tuple[tuple[DatamoshOperation, ...], _ScatterPreparationTiming]:
    planning_started = time.perf_counter()
    plans_by_index: dict[int, tuple[_ScatterWindowPlan, ...]] = {
        index: _plan_scatter_windows(operation, controlled_vops)
        for index, operation in enumerate(operations)
        if operation.enabled
        and operation.intensity > 0.0
        and operation.mode == DATAMOSH_MODE_SCATTER
    }
    planned_count = sum(len(plans) for plans in plans_by_index.values())
    if not planned_count:
        return operations, _ScatterPreparationTiming(
            preparation_seconds=time.perf_counter() - planning_started,
        )

    temporal_root = temporary / "temporal_preparation"
    scatter_root = temporal_root / "scatter"
    scatter_root.mkdir(parents=True)
    try:
        indexed_source, index_created = _ensure_indexed_prediction_source(
            controlled_stream,
            temporal_root,
            fps=fps,
            log=log,
        )
    except Exception as exc:  # noqa: BLE001 - identify the Scatter extraction boundary.
        raise DatamoshError(
            f"SCATTER bounded temporal extraction/preparation failed: {exc}"
        ) from exc
    preparation_seconds = time.perf_counter() - planning_started

    prepared_by_index: dict[int, tuple[ScatterPreparedWindow, ...]] = {}
    decode_seconds = 0.0
    fragment_assembly_seconds = 0.0
    auxiliary_encode_seconds = 0.0
    auxiliary_encode_count = 0
    structural_validation_seconds = 0.0
    provenance_temporary_bytes = 0
    for operation_index, plans in plans_by_index.items():
        operation = operations[operation_index]
        width = int(_operation_parameter(operation, "width", 0))
        height = int(_operation_parameter(operation, "height", 0))
        if width <= 0 or height <= 0:
            raise DatamoshError(
                f"SCATTER requires positive output dimensions, found {width}x{height}."
            )
        prepared: list[ScatterPreparedWindow] = []
        for window_index, plan in enumerate(plans):
            prefix = f"operation_{operation_index:02d}_window_{window_index:03d}"
            neighborhood = scatter_root / f"{prefix}_neighborhood.mkv"
            composite = scatter_root / f"{prefix}_fragments.mkv"
            scatter_stream = scatter_root / f"{prefix}_prediction.m4v"

            decode_started = time.perf_counter()
            try:
                _extract_scatter_neighborhood(
                    indexed_source,
                    neighborhood,
                    plan,
                    fps=fps,
                    log=log,
                )
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - identify the bounded extraction boundary.
                raise DatamoshError(
                    f"SCATTER bounded temporal extraction/preparation failed: {exc}"
                ) from exc
            window_decode_seconds = time.perf_counter() - decode_started
            decode_seconds += window_decode_seconds

            assembly_started = time.perf_counter()
            try:
                _assemble_scatter_fragments(
                    neighborhood,
                    composite,
                    plan,
                    fps=fps,
                    width=width,
                    height=height,
                    operation_number=operation_index + 1,
                    window_number=window_index + 1,
                    log=log,
                )
                frame_hashes = _probe_frame_sha256s(composite, mode_label="SCATTER")
                prepared_fragments, provenance_bytes = _verify_scatter_fragment_provenance(
                    neighborhood,
                    composite,
                    plan,
                    width=width,
                    height=height,
                    evidence_root=scatter_root,
                    prefix=prefix,
                    log=log,
                )
                provenance_temporary_bytes += provenance_bytes
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - identify fragment construction failures.
                raise DatamoshError(f"SCATTER fragment construction failed: {exc}") from exc
            window_assembly_seconds = time.perf_counter() - assembly_started
            fragment_assembly_seconds += window_assembly_seconds

            encode_started = time.perf_counter()
            try:
                _encode_scatter_prediction(
                    composite,
                    scatter_stream,
                    plan,
                    fps=fps,
                    log=log,
                )
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - identify the Scatter auxiliary boundary.
                raise DatamoshError(f"SCATTER auxiliary encode failed: {exc}") from exc
            window_encode_seconds = time.perf_counter() - encode_started
            auxiliary_encode_seconds += window_encode_seconds
            auxiliary_encode_count += 1

            validation_started = time.perf_counter()
            try:
                scatter_data = scatter_stream.read_bytes()
                expected_count = plan.recovery_frame - plan.episode_start_frame
                if len(frame_hashes) != expected_count:
                    raise DatamoshError(
                        "SCATTER prepared-frame hash count mismatch: "
                        f"expected {expected_count}, found {len(frame_hashes)}."
                    )
                scatter_vops = _validate_auxiliary_prediction_structure(
                    scatter_data,
                    expected_count=expected_count,
                    mode_label="SCATTER",
                    window_number=window_index + 1,
                    source_start_frame=plan.source_start_frame,
                    source_end_frame=plan.source_end_frame,
                )
            except DatamoshError:
                raise
            except Exception as exc:  # noqa: BLE001 - normalize auxiliary validation failures.
                raise DatamoshError(f"SCATTER auxiliary encode failed: {exc}") from exc
            validation_seconds = time.perf_counter() - validation_started
            structural_validation_seconds += validation_seconds

            prepared.append(
                ScatterPreparedWindow(
                    episode_start_frame=plan.episode_start_frame,
                    episode_end_frame=plan.episode_end_frame,
                    source_start_frame=plan.source_start_frame,
                    source_end_frame=plan.source_end_frame,
                    target_frames=plan.target_frames,
                    recovery_frame=plan.recovery_frame,
                    replacement_stride=plan.replacement_stride,
                    fragments=prepared_fragments,
                    provenance_frame=plan.episode_start_frame,
                    motion_activity=plan.motion_activity,
                    texture_activity=plan.texture_activity,
                    edge_activity=plan.edge_activity,
                    prepared_stream_sha256=_sha256(scatter_data),
                    prepared_frame_sha256s=frame_hashes,
                    prediction_vops=tuple(unit.data for unit in scatter_vops[1:]),
                    prepared_vop_count=len(scatter_vops),
                    extraction_seconds=window_decode_seconds,
                    fragment_assembly_seconds=window_assembly_seconds,
                    auxiliary_encode_seconds=window_encode_seconds,
                    structural_validation_seconds=validation_seconds,
                    temporary_disk_bytes=(
                        neighborhood.stat().st_size
                        + composite.stat().st_size
                        + scatter_stream.stat().st_size
                        + provenance_bytes
                    ),
                )
            )
        prepared_by_index[operation_index] = tuple(prepared)

    prepared_operations = tuple(
        replace(
            operation,
            prepared_scatter_windows=prepared_by_index.get(index, ()),
        )
        for index, operation in enumerate(operations)
    )
    temporary_disk_bytes = sum(
        path.stat().st_size
        for path in scatter_root.rglob("*")
        if path.is_file()
    )
    if index_created:
        temporary_disk_bytes += indexed_source.stat().st_size
    temporary_disk_bytes += provenance_temporary_bytes
    _log(
        log,
        "SCATTER fragment preparation: "
        f"{planned_count} bounded episode(s), {auxiliary_encode_count} auxiliary encode(s), "
        f"{temporary_disk_bytes} temporary byte(s).",
    )
    return prepared_operations, _ScatterPreparationTiming(
        preparation_seconds=preparation_seconds,
        decode_seconds=decode_seconds,
        fragment_assembly_seconds=fragment_assembly_seconds,
        auxiliary_encode_seconds=auxiliary_encode_seconds,
        auxiliary_encode_count=auxiliary_encode_count,
        structural_validation_seconds=structural_validation_seconds,
        temporary_disk_bytes=temporary_disk_bytes,
    )


def _extract_scatter_neighborhood(
    indexed_source: Path,
    destination: Path,
    plan: _ScatterWindowPlan,
    *,
    fps: int,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    expected_count = plan.source_end_frame - plan.source_start_frame
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{plan.source_start_frame / fps:.9f}",
                "-i",
                str(indexed_source),
                "-map",
                "0:v:0",
                "-an",
                "-frames:v",
                str(expected_count),
                "-c:v",
                "ffv1",
                "-level",
                "3",
                "-pix_fmt",
                "yuv420p",
                "-fps_mode",
                "cfr",
                str(destination),
            ],
            log,
        )
        decoded_count = _probe_decoded_frame_count(destination, mode_label="SCATTER")
        if decoded_count != expected_count:
            raise DatamoshError(
                "SCATTER bounded temporal extraction frame count mismatch: "
                f"expected {expected_count}, found {decoded_count}."
            )
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert tool failures at the extraction boundary.
        raise DatamoshError(
            f"SCATTER bounded temporal extraction/preparation failed: {exc}"
        ) from exc


def _scatter_pixel_box(
    region: DatamoshSpatialRegion,
    *,
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    x = max(0, min(width - 2, int(round(float(region.x) * width))))
    y = max(0, min(height - 2, int(round(float(region.y) * height))))
    x -= x % 2
    y -= y % 2
    box_width = max(2, int(round(float(region.width) * width)))
    box_height = max(2, int(round(float(region.height) * height)))
    box_width -= box_width % 2
    box_height -= box_height % 2
    box_width = max(2, min(width - x, box_width))
    box_height = max(2, min(height - y, box_height))
    box_width -= box_width % 2
    box_height -= box_height % 2
    return x, y, max(2, box_width), max(2, box_height)


def _assemble_scatter_fragments(
    neighborhood: Path,
    destination: Path,
    plan: _ScatterWindowPlan,
    *,
    fps: int,
    width: int,
    height: int,
    operation_number: int | None = None,
    window_number: int | None = None,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    frame_count = plan.recovery_frame - plan.episode_start_frame
    base_start = plan.episode_start_frame - plan.source_start_frame
    labels = ["base", *[f"fragment{index}" for index in range(len(plan.fragments))]]
    filters = [
        f"[0:v]split={len(labels)}" + "".join(f"[{label}in]" for label in labels),
        (
            f"[basein]trim=start_frame={base_start}:end_frame={base_start + frame_count},"
            f"settb=expr=1/{fps},setpts=N[base]"
        ),
    ]
    pixel_boxes: list[tuple[int, int, int, int]] = []
    for index, fragment in enumerate(plan.fragments):
        x, y, box_width, box_height = _scatter_pixel_box(
            fragment.region,
            width=width,
            height=height,
        )
        pixel_boxes.append((x, y, box_width, box_height))
        fragment_start = base_start + fragment.temporal_offset
        filters.append(
            f"[fragment{index}in]trim=start_frame={fragment_start}:"
            f"end_frame={fragment_start + frame_count},"
            f"settb=expr=1/{fps},setpts=N,"
            f"crop={box_width}:{box_height}:{x}:{y}[fragment{index}]"
        )
    previous = "base"
    for index, (fragment, box) in enumerate(zip(plan.fragments, pixel_boxes)):
        output_label = "out" if index == len(plan.fragments) - 1 else f"overlay{index}"
        x, y, _, _ = box
        filters.append(
            f"[{previous}][fragment{index}]overlay={x}:{y}:shortest=1:eof_action=pass:"
            f"enable=lt(n\\,{fragment.resolve_after_frame})[{output_label}]"
        )
        previous = output_label
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(neighborhood),
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[out]",
                "-an",
                "-frames:v",
                str(frame_count),
                "-r",
                str(fps),
                "-c:v",
                "ffv1",
                "-level",
                "3",
                "-pix_fmt",
                "yuv420p",
                str(destination),
            ],
            log,
        )
        assembled_count = _probe_decoded_frame_count(destination, mode_label="SCATTER")
        if assembled_count != frame_count:
            trim_ranges = [f"base={base_start}:{base_start + frame_count}"]
            trim_ranges.extend(
                f"fragment{index}={base_start + fragment.temporal_offset}:"
                f"{base_start + fragment.temporal_offset + frame_count}"
                for index, fragment in enumerate(plan.fragments)
            )
            raise DatamoshError(
                "SCATTER fragment construction frame count mismatch: "
                f"expected {frame_count}, found {assembled_count}; "
                f"operation={operation_number if operation_number is not None else 'unknown'}; "
                f"window={window_number if window_number is not None else 'unknown'}; "
                f"neighborhood={plan.source_start_frame}:{plan.source_end_frame}; "
                f"trims={','.join(trim_ranges)}; fps={fps}; "
                f"frame_clock=settb=1/{fps},setpts=N."
            )
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert filter/assembly failures.
        raise DatamoshError(f"SCATTER fragment construction failed: {exc}") from exc


def _verify_scatter_fragment_provenance(
    neighborhood: Path,
    composite: Path,
    plan: _ScatterWindowPlan,
    *,
    width: int,
    height: int,
    evidence_root: Path,
    prefix: str,
    log: LogCallback,
) -> tuple[tuple[ScatterTemporalFragment, ...], int]:
    """Prove each prepared region came from its declared nearby output frame."""
    composite_rgb = evidence_root / f"{prefix}_provenance_composite.rgb"
    temporary_paths = [composite_rgb]
    try:
        _decode_scatter_rgb_frame(
            composite,
            composite_rgb,
            frame_index=0,
            width=width,
            height=height,
            log=log,
        )
        prepared_bytes = composite_rgb.read_bytes()
        prepared_fragments: list[ScatterTemporalFragment] = []
        for fragment in plan.fragments:
            source_frame_index = (
                plan.episode_start_frame
                + fragment.temporal_offset
                - plan.source_start_frame
            )
            source_rgb = evidence_root / f"{prefix}_fragment_{fragment.fragment_id:02d}_source.rgb"
            temporary_paths.append(source_rgb)
            _decode_scatter_rgb_frame(
                neighborhood,
                source_rgb,
                frame_index=source_frame_index,
                width=width,
                height=height,
                log=log,
            )
            source_bytes = source_rgb.read_bytes()
            x, y, box_width, box_height = _scatter_pixel_box(
                fragment.region,
                width=width,
                height=height,
            )
            source_region = _rgb_region_bytes(
                source_bytes,
                frame_width=width,
                x=x,
                y=y,
                width=box_width,
                height=box_height,
            )
            prepared_region = _rgb_region_bytes(
                prepared_bytes,
                frame_width=width,
                x=x,
                y=y,
                width=box_width,
                height=box_height,
            )
            if len(source_region) != len(prepared_region) or not source_region:
                raise DatamoshError(
                    f"SCATTER fragment {fragment.fragment_id} produced invalid provenance bytes."
                )
            mean_delta = sum(
                abs(source_value - prepared_value)
                for source_value, prepared_value in zip(source_region, prepared_region)
            ) / len(source_region)
            if mean_delta > 2.0:
                raise DatamoshError(
                    "SCATTER fragment provenance mismatch: "
                    f"fragment {fragment.fragment_id}, offset {fragment.temporal_offset}, "
                    f"mean absolute delta {mean_delta:.3f}."
                )
            prepared_fragments.append(
                replace(
                    fragment,
                    source_frame_sha256=_sha256(source_bytes),
                    source_region_sha256=_sha256(source_region),
                    prepared_region_sha256=_sha256(prepared_region),
                    provenance_mean_absolute_delta=mean_delta,
                )
            )
        temporary_bytes = sum(path.stat().st_size for path in temporary_paths if path.is_file())
        return tuple(prepared_fragments), temporary_bytes
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize objective provenance failures.
        raise DatamoshError(f"SCATTER fragment construction failed: {exc}") from exc
    finally:
        for path in temporary_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def _decode_scatter_rgb_frame(
    source: Path,
    destination: Path,
    *,
    frame_index: int,
    width: int,
    height: int,
    log: LogCallback,
) -> None:
    if frame_index < 0:
        raise DatamoshError(f"SCATTER requested invalid provenance frame {frame_index}.")
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    try:
        ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vf",
                f"select=eq(n\\,{frame_index})",
                "-frames:v",
                "1",
                "-pix_fmt",
                "rgb24",
                "-f",
                "rawvideo",
                str(destination),
            ],
            log,
        )
        expected_size = width * height * 3
        actual_size = destination.stat().st_size
        if actual_size != expected_size:
            raise DatamoshError(
                "SCATTER provenance frame size mismatch: "
                f"expected {expected_size}, found {actual_size}."
            )
    except DatamoshError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize bounded provenance decode failures.
        raise DatamoshError(f"SCATTER fragment construction failed: {exc}") from exc


def _rgb_region_bytes(
    frame: bytes,
    *,
    frame_width: int,
    x: int,
    y: int,
    width: int,
    height: int,
) -> bytes:
    row_bytes = frame_width * 3
    region_row_bytes = width * 3
    return b"".join(
        frame[(y + row) * row_bytes + x * 3:(y + row) * row_bytes + x * 3 + region_row_bytes]
        for row in range(height)
    )


def _encode_scatter_prediction(
    source: Path,
    destination: Path,
    plan: _ScatterWindowPlan,
    *,
    fps: int,
    log: LogCallback,
) -> None:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    frame_count = plan.recovery_frame - plan.episode_start_frame
    try:
        ffmpeg_utils.run_command(
            [
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
                *_auxiliary_prediction_codec_args(frame_count),
                "-frames:v",
                str(frame_count),
                "-r",
                str(fps),
                "-f",
                "m4v",
                str(destination),
            ],
            log,
        )
    except Exception as exc:  # noqa: BLE001 - convert tool failures at the auxiliary boundary.
        raise DatamoshError(f"SCATTER auxiliary encode failed: {exc}") from exc


def _probe_frame_sha256s(path: Path, *, mode_label: str) -> tuple[str, ...]:
    ffmpeg_path = ffmpeg_utils.require_binary("ffmpeg")
    try:
        completed = ffmpeg_utils.run_command(
            [
                ffmpeg_path,
                "-v",
                "error",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-f",
                "framemd5",
                "-hash",
                "sha256",
                "-",
            ]
        )
        hashes = tuple(
            line.rsplit(",", 1)[-1].strip()
            for line in completed.stdout.splitlines()
            if line and not line.startswith("#") and "," in line
        )
        if not hashes or any(len(value) != 64 for value in hashes):
            raise ValueError(f"invalid frame hashes: {hashes!r}")
        return hashes
    except Exception as exc:  # noqa: BLE001 - normalize evidence-generation failures.
        raise DatamoshError(f"{mode_label} fragment construction failed: {exc}") from exc


def _probe_decoded_frame_count(path: Path, *, mode_label: str = "SKRRT") -> int:
    ffprobe_path = ffmpeg_utils.require_binary("ffprobe")
    completed = ffmpeg_utils.run_command(
        [
            ffprobe_path,
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    try:
        return int(completed.stdout.strip())
    except (TypeError, ValueError) as exc:
        raise DatamoshError(
            f"{mode_label} could not validate bounded frame count: {completed.stdout!r}"
        ) from exc


_OPERATION_HANDLERS: dict[
    str,
    Callable[[bytes, DatamoshOperation], DatamoshTransform],
] = {
    DATAMOSH_MODE_GENERAL: _transform_general_operation,
    DATAMOSH_MODE_OVERFLOW: _transform_overflow_operation,
    DATAMOSH_MODE_SKRRT: _transform_skrrt_operation,
    DATAMOSH_MODE_SCATTER: _transform_scatter_operation,
    DATAMOSH_MODE_BLEED: _transform_bleed_operation,
}


def _prepare_layer_operation_plans(
    controlled_data: bytes,
    operations: tuple[DatamoshOperation, ...],
) -> tuple[DatamoshOperation, ...]:
    """Freeze order-independent target plans using the historical composition path."""
    by_mode: dict[str, DatamoshOperation] = {}
    for operation in operations:
        if operation.mode not in DATAMOSH_MODE_ORDER:
            raise DatamoshError(f"Unknown DATAMOSH operation mode: {operation.mode}")
        if operation.mode in by_mode:
            raise DatamoshError(
                f"Duplicate DATAMOSH operation mode in Layer order: {operation.mode}"
            )
        by_mode[operation.mode] = operation

    planned_modes = {
        DATAMOSH_MODE_GENERAL,
        DATAMOSH_MODE_OVERFLOW,
        DATAMOSH_MODE_BLEED,
    } & by_mode.keys()
    if not planned_modes:
        return operations

    final_planned_index = max(DATAMOSH_MODE_ORDER.index(mode) for mode in planned_modes)
    current = controlled_data
    planned_by_mode: dict[
        str,
        tuple[tuple[DatamoshEvent, ...], tuple[tuple[int, bytes], ...], str],
    ] = {}
    for historical_index, mode in enumerate(DATAMOSH_MODE_ORDER):
        operation = by_mode.get(mode)
        if operation is None:
            continue
        planning_operation = replace(
            operation,
            planned_events=(),
            planned_source_vops=(),
            planning_source_sha256=None,
        )
        planning_source_sha256 = _sha256(current)
        planning_vops = vop_units(parse_mpeg4_units(current))
        transformed = _OPERATION_HANDLERS[mode](current, planning_operation)
        if mode in planned_modes:
            source_frames = sorted(
                {int(event.source_p_frame) for event in transformed.events}
            )
            planned_sources = tuple(
                (frame, planning_vops[frame].data)
                for frame in source_frames
                if 0 <= frame < len(planning_vops)
                and planning_vops[frame].coding_type == 1
            )
            planned_by_mode[mode] = (
                transformed.events,
                planned_sources,
                planning_source_sha256,
            )
        current = transformed.data
        if historical_index >= final_planned_index:
            break

    return tuple(
        replace(
            operation,
            planned_events=planned_by_mode[operation.mode][0],
            planned_source_vops=planned_by_mode[operation.mode][1],
            planning_source_sha256=planned_by_mode[operation.mode][2],
        )
        if operation.mode in planned_by_mode
        else operation
        for operation in operations
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
    loop_protected_tail_start: int | None = None,
    video_crf: int,
    video_bitrate: int | None,
    transitions: tuple[DatamoshTransition, ...] = (),
    operations: tuple[DatamoshOperation, ...] = (),
    log: LogCallback = None,
) -> DatamoshResult:
    """Run one controlled encode, ordered prediction operations, and one safe transcode."""
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
    protected_tail_start = frame_count
    if loop_friendly:
        protected_tail_start = (
            _loop_protected_tail_start(frame_count, fps)
            if loop_protected_tail_start is None
            else max(0, min(frame_count, int(loop_protected_tail_start)))
        )
    if operations:
        configured_operations = tuple(
            replace(
                operation,
                end_frame=min(operation.end_frame, protected_tail_start),
            )
            if loop_friendly
            else operation
            for operation in operations
        )
    else:
        configured_operations = (
            DatamoshOperation(
                mode=DATAMOSH_MODE_GENERAL,
                enabled=True,
                intensity=effect_intensity,
                seed=weird_seed,
                salt=DATAMOSH_SEED_SALT,
                order=0,
                start_frame=eligible_start_frame,
                end_frame=protected_tail_start,
                absolute_frame_offset=absolute_frame_offset,
                transitions=transitions,
                parameters=(("fps", fps),),
            ),
        )
    enabled_operations = tuple(
        operation
        for operation in configured_operations
        if operation.enabled and operation.intensity > 0.0
    )
    transition_map: dict[tuple[int, int], DatamoshTransition] = {
        (target.frame, target.absolute_frame): target for target in transitions
    }
    for operation in enabled_operations:
        transition_map.update(
            {
                (target.frame, target.absolute_frame): target
                for target in operation.transitions
            }
        )
    operation_transitions = tuple(
        sorted(transition_map.values(), key=lambda target: (target.frame, target.absolute_frame))
    )
    protection_boundaries = tuple(
        sorted(
            {
                boundary
                for operation in enabled_operations
                for interval in _operation_protected_intervals(operation, frame_count)
                for boundary in interval
                if 0 < boundary < frame_count
            }
        )
    )

    encode_started = time.perf_counter()
    try:
        _encode_prediction_stream(
            source,
            controlled_stream,
            fps=fps,
            frame_count=frame_count,
            gop_size=gop_size,
            anchor_frame=eligible_start_frame,
            transition_frames=(
                tuple(target.frame for target in operation_transitions)
                + protection_boundaries
            ),
            protected_tail_start=protected_tail_start if loop_friendly else None,
            log=log,
        )
    except Exception as exc:  # noqa: BLE001 - convert external codec errors at this boundary.
        raise DatamoshError(f"DATAMOSHING MPEG-4 intermediate encode failed: {exc}") from exc
    encode_seconds = time.perf_counter() - encode_started

    skrrt_timing = _SkrrtPreparationTiming()
    scatter_timing = _ScatterPreparationTiming()
    try:
        controlled_data = controlled_stream.read_bytes()
        controlled_vops = vop_units(parse_mpeg4_units(controlled_data))
        if len(controlled_vops) != frame_count:
            raise DatamoshError(
                "DATAMOSHING MPEG-4 intermediate frame count mismatch: "
                f"expected {frame_count}, found {len(controlled_vops)} VOPs."
            )
        enabled_operations, skrrt_timing = _prepare_skrrt_operations(
            controlled_stream,
            temporary,
            controlled_vops,
            enabled_operations,
            fps=fps,
            log=log,
        )
        enabled_operations, scatter_timing = _prepare_scatter_operations(
            controlled_stream,
            temporary,
            controlled_vops,
            enabled_operations,
            fps=fps,
            log=log,
        )
        enabled_operations = _prepare_layer_operation_plans(
            controlled_data,
            enabled_operations,
        )
        transform_started = time.perf_counter()
        transformed = transform_mpeg4_operations(
            controlled_data,
            enabled_operations,
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
            protected_tail_start_frame=protected_tail_start,
            effect_intensity=effect_intensity,
            weird_seed=weird_seed,
            transition_targets=operation_transitions,
            events=(),
            original_counts=transformed.original_counts,
            mutated_counts=transformed.mutated_counts,
            input_stream_size=len(controlled_data),
            manipulated_stream_size=len(controlled_data),
            temporary_disk_bytes=(
                controlled_stream.stat().st_size
                + skrrt_timing.temporary_disk_bytes
                + scatter_timing.temporary_disk_bytes
            ),
            intermediate_encode_seconds=encode_seconds,
            reverse_preparation_seconds=skrrt_timing.preparation_seconds,
            reverse_decode_seconds=skrrt_timing.reverse_decode_seconds,
            skrrt_zone_composition_seconds=skrrt_timing.zone_composition_seconds,
            auxiliary_reverse_encode_seconds=skrrt_timing.auxiliary_encode_seconds,
            auxiliary_reverse_encode_count=skrrt_timing.auxiliary_encode_count,
            auxiliary_reverse_validation_seconds=(
                skrrt_timing.structural_validation_seconds
            ),
            reverse_temporary_disk_bytes=skrrt_timing.temporary_disk_bytes,
            scatter_preparation_seconds=scatter_timing.preparation_seconds,
            scatter_decode_seconds=scatter_timing.decode_seconds,
            scatter_fragment_assembly_seconds=scatter_timing.fragment_assembly_seconds,
            auxiliary_scatter_encode_seconds=scatter_timing.auxiliary_encode_seconds,
            auxiliary_scatter_encode_count=scatter_timing.auxiliary_encode_count,
            auxiliary_scatter_validation_seconds=(
                scatter_timing.structural_validation_seconds
            ),
            scatter_temporary_disk_bytes=scatter_timing.temporary_disk_bytes,
            transform_seconds=transform_seconds,
            safe_transcode_seconds=0.0,
            manipulated_stream_sha256=None,
            operations=transformed.operations,
            operation_transform_seconds=transformed.operation_transform_seconds,
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
        if event.mode == DATAMOSH_MODE_SKRRT and event.operation == "SKRRT_REVERSE_PREDICTION_DRAG":
            _log(
                log,
                f"SKRRT event: absolute frame {event.absolute_frame}, "
                f"reverse source frames {list(event.reversed_source_frame_order)}, "
                f"{len(event.repeated_at_frames)} main VOP target(s), "
                f"clean recovery at absolute frame {absolute_frame_offset + int(event.recovery_frame or 0)}.",
            )
        elif (
            event.mode == DATAMOSH_MODE_SCATTER
            and event.operation == "SCATTER_MULTI_TIME_FRAGMENTATION"
        ):
            offsets = sorted({fragment.temporal_offset for fragment in event.scatter_fragments})
            _log(
                log,
                f"SCATTER event: absolute frame {event.absolute_frame}, "
                f"{len(event.scatter_fragments)} material region(s) from offsets {offsets}, "
                f"{len(event.repeated_at_frames)} main VOP target(s), "
                f"clean recovery at absolute frame "
                f"{absolute_frame_offset + int(event.recovery_frame or 0)}.",
            )
        elif event.operation.startswith("OVERFLOW_DECAYING_RECURSIVE_"):
            _log(
                log,
                f"spILL! recursive flow: absolute frame {event.absolute_frame}, "
                f"cascade {event.flow_cascade}, depth {event.flow_chain_depth}/"
                f"{event.flow_refresh_interval}, source prediction frame "
                f"{absolute_frame_offset + event.source_p_frame}, clean recovery at "
                f"absolute frame {absolute_frame_offset + int(event.recovery_frame or 0)}.",
            )
        elif "I_RESET_SUPPRESSED" in event.operation:
            transition_note = (
                f" at {event.transition_from_kind}->{event.transition_to_kind} "
                f"{event.visual_transition} transition"
                if event.transition_absolute_frame is not None
                else ""
            )
            _log(
                log,
                f"DATAMOSHING event: mode {event.mode}, absolute frame {event.absolute_frame}, "
                f"I reset suppressed{transition_note} with encoded P frame "
                f"{absolute_frame_offset + event.source_p_frame}.",
            )
        else:
            _log(
                log,
                f"DATAMOSHING event: mode {event.mode}, absolute frame {event.absolute_frame}, "
                f"encoded P frame {absolute_frame_offset + event.source_p_frame} repeated "
                f"across {len(event.repeated_at_frames)} frame(s).",
            )
    temporary_bytes = sum(
        path.stat().st_size
        for path in (controlled_stream, manipulated_stream, destination)
        if path.exists()
    ) + skrrt_timing.temporary_disk_bytes + scatter_timing.temporary_disk_bytes
    _log(
        log,
        "DATAMOSHING codec stage: "
        f"{transformed.i_reset_count} I reset(s) suppressed, "
        f"{transformed.p_persistence_count} P persistence event(s), "
        f"{decoded_frames}/{frame_count} frames validated.",
    )
    skrrt_zone_timing = (
        f"Zone composition {skrrt_timing.zone_composition_seconds:.3f}s, "
        if skrrt_timing.zone_composition_seconds > 0.0
        else ""
    )
    _log(
        log,
        "DATAMOSHING timing: "
        f"MPEG-4 encode {encode_seconds:.2f}s, "
        f"SKRRT prep/index {skrrt_timing.preparation_seconds:.3f}s, "
        f"reverse decode {skrrt_timing.reverse_decode_seconds:.3f}s, "
        f"{skrrt_zone_timing}"
        f"auxiliary reverse encode {skrrt_timing.auxiliary_encode_seconds:.3f}s, "
        f"auxiliary reverse validation {skrrt_timing.structural_validation_seconds:.3f}s, "
        f"SCATTER prep/index {scatter_timing.preparation_seconds:.3f}s, "
        f"fragment decode {scatter_timing.decode_seconds:.3f}s, "
        f"fragment assembly {scatter_timing.fragment_assembly_seconds:.3f}s, "
        f"auxiliary fragment encode {scatter_timing.auxiliary_encode_seconds:.3f}s, "
        f"auxiliary fragment validation {scatter_timing.structural_validation_seconds:.3f}s, "
        f"VOP transform {transform_seconds:.3f}s, "
        f"safe H.264 transcode {transcode_seconds:.2f}s.",
    )
    return DatamoshResult(
        output_path=destination,
        applied=True,
        frame_count=decoded_frames,
        duration=duration,
        gop_size=gop_size,
        eligible_start_frame=eligible_start_frame,
        protected_tail_start_frame=protected_tail_start,
        effect_intensity=effect_intensity,
        weird_seed=weird_seed,
        transition_targets=operation_transitions,
        events=transformed.events,
        original_counts=transformed.original_counts,
        mutated_counts=transformed.mutated_counts,
        input_stream_size=len(controlled_data),
        manipulated_stream_size=len(transformed.data),
        temporary_disk_bytes=temporary_bytes,
        intermediate_encode_seconds=encode_seconds,
        reverse_preparation_seconds=skrrt_timing.preparation_seconds,
        reverse_decode_seconds=skrrt_timing.reverse_decode_seconds,
        skrrt_zone_composition_seconds=skrrt_timing.zone_composition_seconds,
        auxiliary_reverse_encode_seconds=skrrt_timing.auxiliary_encode_seconds,
        auxiliary_reverse_encode_count=skrrt_timing.auxiliary_encode_count,
        auxiliary_reverse_validation_seconds=(
            skrrt_timing.structural_validation_seconds
        ),
        reverse_temporary_disk_bytes=skrrt_timing.temporary_disk_bytes,
        scatter_preparation_seconds=scatter_timing.preparation_seconds,
        scatter_decode_seconds=scatter_timing.decode_seconds,
        scatter_fragment_assembly_seconds=scatter_timing.fragment_assembly_seconds,
        auxiliary_scatter_encode_seconds=scatter_timing.auxiliary_encode_seconds,
        auxiliary_scatter_encode_count=scatter_timing.auxiliary_encode_count,
        auxiliary_scatter_validation_seconds=(
            scatter_timing.structural_validation_seconds
        ),
        scatter_temporary_disk_bytes=scatter_timing.temporary_disk_bytes,
        transform_seconds=transform_seconds,
        safe_transcode_seconds=transcode_seconds,
        manipulated_stream_sha256=transformed.output_sha256,
        operations=transformed.operations,
        operation_transform_seconds=transformed.operation_transform_seconds,
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


def _stable_score(
    seed: int | None,
    category: int,
    absolute_frame: int,
    *,
    salt: int = DATAMOSH_SEED_SALT,
) -> int:
    mask = (1 << 64) - 1
    payload = (
        (int(seed or 0) & mask).to_bytes(8, "big")
        + (int(salt) & mask).to_bytes(8, "big")
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


def _transition_target_limit(intensity: float, transition_count: int) -> int:
    if transition_count <= 0 or intensity <= 0.0:
        return 0
    amount = max(0.0, min(1.0, float(intensity) / 2.0))
    coverage = 0.15 + 0.85 * amount
    return min(transition_count, max(1, int(round(transition_count * coverage))))


def _transition_persistence_policy(intensity: float, score: int) -> tuple[int, int]:
    amount = max(0.0, min(1.0, float(intensity) / 2.0))
    if amount < 0.40:
        return 2 + score % 3, 2
    if amount < 0.75:
        return 6 + score % 7, 1 + (score // 7) % 2
    return 16 + score % 15, 1


def _loop_protected_tail_start(frame_count: int, fps: int) -> int:
    return timeline_math.loop_protected_tail_start(frame_count, fps)


def _encode_prediction_stream(
    source: Path,
    destination: Path,
    *,
    fps: int,
    frame_count: int,
    gop_size: int,
    anchor_frame: int,
    transition_frames: tuple[int, ...],
    protected_tail_start: int | None,
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
    forced_frames = {
        int(frame)
        for frame in transition_frames
        if 0 < int(frame) < frame_count
    }
    if 0 < anchor_frame < frame_count:
        forced_frames.add(int(anchor_frame))
    if protected_tail_start is not None and 0 < protected_tail_start < frame_count:
        forced_frames.add(int(protected_tail_start))
    if forced_frames:
        forced_times = ",".join(f"{frame / fps:.9f}" for frame in sorted(forced_frames))
        args.extend(["-force_key_frames", forced_times])
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
