"""Pure persisted desktop-state contract for WZRD.VID.

This module owns schema, migration, normalization, canonical serialization, and
Reset defaults for plain project/settings data.  It intentionally has no Qt,
renderer, codec, media-probing, path-resolution, or filesystem dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


SCHEMA_VERSION = 6

CODEC_LAYER_ORDER = (
    "datamoshing",
    "overflow",
    "skrrt",
    "scatter",
    "bleed",
)

ZONE_ASSIGNMENT_EFFECT_ORDER = (
    "pixel_sorting",
    "databending",
    "circuit_bending",
    "hex_editing",
    "random_noise_bw",
    "skrrt",
)
MAX_ZONES = 3

STYLE_FX_FULL = "Full effects"
STYLE_FX_RANDOM = "Random clean sections"
STYLE_FX_MANUAL = "Manual clean time blocks"
STYLE_FX_MANUAL_RANDOM = "Manual + random"

PERSISTED_EFFECT_ORDER = (
    "ken_burns",
    "tunnel_zoom",
    "punch_zoom",
    "glitch",
    "datamoshing",
    "overflow",
    "skrrt",
    "scatter",
    "bleed",
    "pixel_sorting",
    "databending",
    "circuit_bending",
    "hex_editing",
    "random_noise_bw",
    "rgb_split",
    "color_drift",
    "scanlines",
    "char_noise",
    "vhs_wobble",
    "boost",
    "stutter_hold",
    "motion_melt",
    "terminal_scroll",
    "tape_damage",
    "mosaic_collapse",
    "audio_reactive",
)

DEFAULT_OFF_EFFECTS = frozenset(
    {
        "tunnel_zoom",
        "datamoshing",
        "overflow",
        "skrrt",
        "scatter",
        "bleed",
        "pixel_sorting",
        "databending",
        "circuit_bending",
        "hex_editing",
        "random_noise_bw",
        "stutter_hold",
        "motion_melt",
        "terminal_scroll",
        "tape_damage",
        "mosaic_collapse",
        "audio_reactive",
    }
)

RESET_PRESERVED_KEYS = (
    "ui_language",
    "resolution_index",
    "preview_from",
    "preview_custom",
)


@dataclass(frozen=True)
class ZoneDefinition:
    """One named rectangle in normalized final-output coordinates."""

    id: str
    name: str
    x: float
    y: float
    width: float
    height: float
    motion_mode: str | None = None
    motion_amount: float = 25.0
    motion_cycles: int = 2

    def as_dict(self) -> dict[str, object]:
        record: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "x": float(self.x),
            "y": float(self.y),
            "width": float(self.width),
            "height": float(self.height),
        }
        if isinstance(self.motion_mode, str) and self.motion_mode in {"drift", "pulse"}:
            record.update(
                {
                    "motion_mode": self.motion_mode,
                    "motion_amount": float(self.motion_amount),
                    "motion_cycles": int(self.motion_cycles),
                }
            )
        return record


def normalize_codec_layer_order(value: object) -> tuple[str, ...]:
    """Return the current complete, duplicate-free persisted codec Layer."""
    if not isinstance(value, (list, tuple)):
        return CODEC_LAYER_ORDER

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_mode in value:
        if not isinstance(raw_mode, str):
            continue
        mode = raw_mode.strip().lower()
        if mode in CODEC_LAYER_ORDER and mode not in seen:
            normalized.append(mode)
            seen.add(mode)
    normalized.extend(mode for mode in CODEC_LAYER_ORDER if mode not in seen)
    return tuple(normalized)


def normalize_zone_state(
    zones_value: object,
    assignments_value: object,
) -> tuple[tuple[ZoneDefinition, ...], dict[str, str], bool]:
    """Validate schema-6 Zone fields and report whether repair was required."""
    repaired = False
    raw_zones: list[object]
    if isinstance(zones_value, list):
        raw_zones = zones_value
    else:
        raw_zones = []
        repaired = zones_value not in (None, ())

    zones: list[ZoneDefinition] = []
    seen_ids: set[str] = set()
    for record in raw_zones:
        if len(zones) >= MAX_ZONES:
            repaired = True
            break
        if isinstance(record, ZoneDefinition):
            record = record.as_dict()
        if not isinstance(record, dict):
            repaired = True
            continue
        zone_id = record.get("id")
        name = record.get("name")
        geometry = tuple(record.get(key) for key in ("x", "y", "width", "height"))
        if (
            not isinstance(zone_id, str)
            or not zone_id.strip()
            or zone_id in seen_ids
            or not isinstance(name, str)
            or not name.strip()
            or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in geometry
            )
        ):
            repaired = True
            continue
        x, y, width, height = (float(value) for value in geometry)
        if (
            not all(math.isfinite(value) for value in (x, y, width, height))
            or width <= 0.0
            or height <= 0.0
        ):
            repaired = True
            continue
        left = max(0.0, min(1.0, x))
        top = max(0.0, min(1.0, y))
        right = max(0.0, min(1.0, x + width))
        bottom = max(0.0, min(1.0, y + height))
        if right <= left or bottom <= top:
            repaired = True
            continue
        in_bounds = (
            x >= 0.0
            and y >= 0.0
            and x + width <= 1.0
            and y + height <= 1.0
        )
        if not in_bounds:
            repaired = True
        raw_motion_mode = record.get("motion_mode")
        motion_mode = (
            raw_motion_mode
            if isinstance(raw_motion_mode, str)
            and raw_motion_mode in {"drift", "pulse"}
            else None
        )
        if "motion_mode" in record and motion_mode is None:
            repaired = True
        if motion_mode is None:
            if "motion_amount" in record or "motion_cycles" in record:
                repaired = True
            motion_amount = 25.0
            motion_cycles = 2
        else:
            raw_motion_amount = record.get("motion_amount", 25.0)
            if (
                isinstance(raw_motion_amount, bool)
                or not isinstance(raw_motion_amount, (int, float))
                or not math.isfinite(float(raw_motion_amount))
            ):
                motion_amount = 25.0
                repaired = True
            else:
                motion_amount = max(0.0, min(50.0, float(raw_motion_amount)))
                if motion_amount != float(raw_motion_amount):
                    repaired = True
            raw_motion_cycles = record.get("motion_cycles", 2)
            if isinstance(raw_motion_cycles, bool) or not isinstance(raw_motion_cycles, int):
                motion_cycles = 2
                repaired = True
            else:
                motion_cycles = max(1, min(8, raw_motion_cycles))
                if motion_cycles != raw_motion_cycles:
                    repaired = True
        zone = ZoneDefinition(
            id=zone_id,
            name=name.strip(),
            x=x if in_bounds else left,
            y=y if in_bounds else top,
            width=width if in_bounds else right - left,
            height=height if in_bounds else bottom - top,
            motion_mode=motion_mode,
            motion_amount=motion_amount,
            motion_cycles=motion_cycles,
        )
        zones.append(zone)
        seen_ids.add(zone.id)

    assignments: dict[str, str] = {}
    if assignments_value is None:
        raw_assignments: dict[object, object] = {}
    elif isinstance(assignments_value, dict):
        raw_assignments = assignments_value
    else:
        raw_assignments = {}
        repaired = True
    valid_ids = {zone.id for zone in zones}
    for raw_effect, raw_zone_id in raw_assignments.items():
        if (
            raw_effect not in ZONE_ASSIGNMENT_EFFECT_ORDER
            or not isinstance(raw_zone_id, str)
            or raw_zone_id not in valid_ids
        ):
            repaired = True
            continue
        assignments[str(raw_effect)] = raw_zone_id
    return tuple(zones), assignments, repaired


def normalize_style_fx_coverage_mode(value: object) -> str:
    """Return a known Style FX mode, defaulting fail-safe to Full effects."""
    if not isinstance(value, str):
        return STYLE_FX_FULL
    normalized = value.strip().lower()
    aliases = {
        STYLE_FX_FULL.lower(): STYLE_FX_FULL,
        STYLE_FX_RANDOM.lower(): STYLE_FX_RANDOM,
        STYLE_FX_MANUAL.lower(): STYLE_FX_MANUAL,
        STYLE_FX_MANUAL_RANDOM.lower(): STYLE_FX_MANUAL_RANDOM,
    }
    return aliases.get(normalized, STYLE_FX_FULL)


def normalize_loaded_max_video_length(value: object) -> str:
    """Match the current load-time blank/auto/historical no-op text repair."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "auto", "none", "null"}:
        return ""
    return text


def canonical_audio_mode(value: object) -> str:
    """Map historical audio labels without validating current UI membership."""
    text = str(value)
    aliases = {
        "External Music/Audio": "External only",
        "Keep source audio": "Source audio only",
        "Source audio": "Source audio only",
        "External + source audio": "External + selected source audio",
    }
    return aliases.get(text, text)


def canonical_transition_mode(value: object) -> str:
    """Keep visible None compatible with the persisted Hard Cut identity."""
    text = str(value or "").strip()
    return "Hard Cut" if text in {"", "None", "Hard Cut"} else str(value)


def normalize_effects(
    value: object,
    *,
    current: Mapping[str, object] | None = None,
) -> dict[str, bool]:
    """Normalize the sole persisted activation dictionary in stable UI order."""
    defaults = {
        effect: effect not in DEFAULT_OFF_EFFECTS for effect in PERSISTED_EFFECT_ORDER
    }
    if not isinstance(value, dict):
        if current is None:
            return defaults
        return {
            effect: bool(current.get(effect, defaults[effect]))
            for effect in PERSISTED_EFFECT_ORDER
        }
    return {
        effect: bool(value.get(effect, defaults[effect]))
        for effect in PERSISTED_EFFECT_ORDER
    }


def normalize_style_fx_manual_blocks(value: object) -> list[dict[str, str]]:
    """Keep only current dict-shaped persisted Style FX manual blocks."""
    if not isinstance(value, list):
        return []
    return [
        {
            "start": str(block.get("start", "0:12")),
            "end": str(block.get("end", "0:18")),
        }
        for block in value
        if isinstance(block, dict)
    ]


def _bounded_percent(value: object, default: int = 10) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def _integer_or(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def normalize_persisted_state(
    raw_state: Mapping[str, object],
    *,
    current_effects: Mapping[str, object] | None = None,
    style_fx_random_seed_fallback: int,
) -> tuple[dict[str, object], bool]:
    """Migrate and normalize the extracted pure fields for MainWindow loading."""
    state = dict(raw_state)
    try:
        source_schema = int(state.get("schema_version", 0))
    except (TypeError, ValueError):
        source_schema = 0

    state["schema_version"] = SCHEMA_VERSION
    state["style_begin_time"] = str(state.get("style_begin_time", "0:00"))
    state["max_video_length"] = normalize_loaded_max_video_length(
        state.get("max_video_length", "")
    )
    state["random_clip_assembly"] = bool(
        state.get("random_clip_assembly", False)
    )
    default_audio_mode = (
        "External only"
        if str(state.get("audio_path", "")).strip()
        else "Source audio only"
    )
    state["audio_mode"] = canonical_audio_mode(
        str(state.get("audio_mode", default_audio_mode))
    )
    state["effects"] = normalize_effects(
        state.get("effects", {}),
        current=current_effects,
    )
    state["codec_layer_order"] = list(
        normalize_codec_layer_order(
            state.get("codec_layer_order", CODEC_LAYER_ORDER)
        )
    )
    state["style_fx_coverage_mode"] = normalize_style_fx_coverage_mode(
        state.get("style_fx_coverage_mode")
    )
    state["style_fx_manual_blocks"] = normalize_style_fx_manual_blocks(
        state.get("style_fx_manual_blocks", [])
    )
    state["style_fx_random_percent"] = _bounded_percent(
        state.get("style_fx_random_percent", 10)
    )
    state["style_fx_random_seed"] = _integer_or(
        state.get("style_fx_random_seed", style_fx_random_seed_fallback),
        style_fx_random_seed_fallback,
    )
    state["transition_mode"] = canonical_transition_mode(
        state.get("transition_mode", "CRT Flash")
    )

    if source_schema >= SCHEMA_VERSION:
        zones, assignments, zone_repaired = normalize_zone_state(
            state.get("zones", []),
            state.get("effect_zone_assignments", {}),
        )
    else:
        zones, assignments, zone_repaired = (), {}, False
    state["zones"] = [zone.as_dict() for zone in zones]
    state["effect_zone_assignments"] = assignments
    return state, zone_repaired


def canonicalize_persisted_state(
    raw_state: Mapping[str, object],
) -> dict[str, object]:
    """Prepare UI-collected project/settings data for deterministic JSON output."""
    state = dict(raw_state)
    state["schema_version"] = SCHEMA_VERSION
    state["effects"] = normalize_effects(state.get("effects", {}))
    zones, assignments, _repaired = normalize_zone_state(
        state.get("zones", []),
        state.get("effect_zone_assignments", {}),
    )
    state["zones"] = [zone.as_dict() for zone in zones]
    state["effect_zone_assignments"] = assignments
    state["codec_layer_order"] = list(
        normalize_codec_layer_order(
            state.get("codec_layer_order", CODEC_LAYER_ORDER)
        )
    )
    state["style_fx_coverage_mode"] = normalize_style_fx_coverage_mode(
        state.get("style_fx_coverage_mode")
    )
    state["style_fx_manual_blocks"] = normalize_style_fx_manual_blocks(
        state.get("style_fx_manual_blocks", [])
    )
    state["style_fx_random_percent"] = _bounded_percent(
        state.get("style_fx_random_percent", 10)
    )
    state["transition_mode"] = canonical_transition_mode(
        state.get("transition_mode", "CRT Flash")
    )
    return state


def default_project_state(
    *,
    ui_language: str = "system",
    random_seed: int,
    style_fx_random_seed: int,
    weird_seed: int,
) -> dict[str, object]:
    """Return the canonical fresh persisted project state for schema 6."""
    return {
        "app": "WZRD.VID",
        "schema_version": SCHEMA_VERSION,
        "ui_language": ui_language,
        "timeline_items": [],
        "video_path": "",
        "audio_path": "",
        "output_path": "",
        "video_start": "0:00",
        "video_end": "auto",
        "audio_start": "0:00",
        "audio_end": "auto",
        "audio_timeline_start": "0:00",
        "audio_timeline_end": "auto",
        "style_begin_time": "0:00",
        "max_video_length": "",
        "random_clip_assembly": False,
        "audio_mode": "Silent",
        "worky_music_mode": False,
        "match_timeline_to_audio": False,
        "match_timeline_mode": "Speed up/down timeline",
        "preset": "Classic ANSI",
        "chunky_blocks": False,
        "width_chars": 120,
        "fps": 24,
        "effect_intensity": 65,
        "resolution_index": 1,
        "output_size_preset": "Full Quality",
        "custom_max_width": 1280,
        "custom_fps": 24,
        "custom_crf": 22,
        "custom_audio_kbps": 128,
        "target_size_enabled": False,
        "target_size_mb": 29.0,
        "optimize_preset": "29 MB Text Limit",
        "effects": normalize_effects({}),
        "zones": [],
        "effect_zone_assignments": {},
        "codec_layer_order": list(CODEC_LAYER_ORDER),
        "bypass_mode": "Full ANSI",
        "random_percent": 10,
        "random_seed": int(random_seed),
        "style_fx_coverage_mode": STYLE_FX_FULL,
        "style_fx_random_percent": 10,
        "style_fx_random_seed": int(style_fx_random_seed),
        "weird_seed": int(weird_seed),
        "framing_fit_mode": "Fill/Crop",
        "framing_anchor": "Center",
        "framing_offset_x": 0,
        "framing_offset_y": 0,
        "framing_zoom": 0,
        "letterbox_background": "Black",
        "preserve_upper_bias": True,
        "dither_mode": "None",
        "transition_mode": "CRT Flash",
        "transition_intensity": 55,
        "ending_mode": "Fade Out",
        "loop_friendly": False,
        "preview_from": "Start",
        "preview_duration": "5s",
        "preview_custom": "0:00",
        "manual_blocks": [],
        "style_fx_manual_blocks": [],
        "batch_enabled": False,
        "batch_variants": ["29 MB Text Limit", "Chunkcore"],
    }


def reset_project_state(
    current_state: Mapping[str, object],
    *,
    random_seed: int,
    style_fx_random_seed: int,
    weird_seed: int,
) -> dict[str, object]:
    """Return the exact current Reset contract, including intentionally kept UI state."""
    reset = default_project_state(
        ui_language=str(current_state.get("ui_language", "system")),
        random_seed=random_seed,
        style_fx_random_seed=style_fx_random_seed,
        weird_seed=weird_seed,
    )
    for key in RESET_PRESERVED_KEYS:
        if key in current_state:
            reset[key] = current_state[key]
    return canonicalize_persisted_state(reset)
