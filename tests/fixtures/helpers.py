"""Generated frame fixtures and shared frame-contract helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import numpy as np
from PIL import Image

import datamosh
import renderer


ORACLE_INTENSITIES = (0.65, 1.0, 1.45)
ORACLE_SEED = 8_675_309
ORACLE_FPS = 24
ORACLE_FRAME_COUNT = 84
ORACLE_SIZE = (192, 108)
ORACLE_SHA256 = "441f9150b0f8c2d79fadb5a653a4b930d777959c37e458099a3b28eee3baa80a"


def oracle_source_frame(
    frame_index: int,
    width: int = ORACLE_SIZE[0],
    height: int = ORACLE_SIZE[1],
) -> Image.Image:
    """Reproduce the exact generated fixture used by the accepted v0.4.0 oracle."""
    y, x = np.mgrid[0:height, 0:width]
    moving_x = (frame_index * 5) % width
    moving_y = (frame_index * 3) % height
    red = (x * 3 + y + frame_index * 7) % 256
    green = (y * 5 + (x // 6) * 27 + frame_index * 11) % 256
    blue = ((x ^ y) * 9 + frame_index * 13) % 256
    rgb = np.stack((red, green, blue), axis=2).astype(np.uint8)
    mask = (np.abs(x - moving_x) < 22) & (np.abs(y - moving_y) < 15)
    rgb[mask] = np.array((250, 18, 210), dtype=np.uint8)
    rgb[:, (frame_index * 2) % width : ((frame_index * 2) % width) + 3] = 255
    return Image.fromarray(rgb, mode="RGB")


def oracle_transitions() -> tuple[datamosh.DatamoshTransition, ...]:
    return (
        datamosh.DatamoshTransition(20, 20, "video", "photo", "CRT Flash"),
        datamosh.DatamoshTransition(57, 57, "photo", "video", "Hard Cut"),
    )


def material_oracle_records() -> tuple[dict[str, object], bool]:
    """Build the 18 ordered v0.4.0 cases entirely in memory."""
    cases = [(key,) for key in renderer.PHASE2_FRAME_EFFECT_ORDER]
    cases.append(renderer.PHASE2_FRAME_EFFECT_ORDER)
    records: dict[str, object] = {}
    source_immutable = True
    for intensity in ORACLE_INTENSITIES:
        for enabled in cases:
            effects = {
                key: key in enabled for key in renderer.PHASE2_FRAME_EFFECT_ORDER
            }
            choreographer = renderer._FrameEffectChoreographer(
                effects,
                intensity,
                ORACLE_FPS,
                ORACLE_SEED,
                oracle_transitions(),
                record_events=True,
            )
            frame_hashes: list[str] = []
            combined = hashlib.sha256()
            for frame_index in range(ORACLE_FRAME_COUNT):
                source = oracle_source_frame(frame_index)
                source_before = np.asarray(source, dtype=np.uint8).copy()
                result = renderer._apply_phase2_frame_effects(
                    source,
                    effects,
                    intensity,
                    frame_index,
                    ORACLE_FPS,
                    ORACLE_SEED,
                    choreographer=choreographer,
                    material=source,
                )
                source_immutable &= np.array_equal(
                    np.asarray(source, dtype=np.uint8), source_before
                )
                result_bytes = np.asarray(result, dtype=np.uint8).tobytes()
                frame_hashes.append(hashlib.sha256(result_bytes).hexdigest())
                combined.update(result_bytes)
            key = f"{intensity:.2f}:" + ",".join(enabled)
            records[key] = {
                "combined_sha256": combined.hexdigest(),
                "frame_sha256": frame_hashes,
                "events": [asdict(event) for event in choreographer.recorded_events],
                "organic_states": choreographer.recorded_organic_states,
                "peak_analysis_bytes": choreographer.peak_analysis_bytes,
            }
    return records, source_immutable


def serialized_oracle(records: dict[str, object]) -> bytes:
    """Match the historical oracle's sorted, indented JSON byte contract."""
    return (json.dumps(records, indent=2, sort_keys=True) + "\n").encode("utf-8")


def material_case(
    intensity: float,
    seed: int,
    enabled: tuple[str, ...] = renderer.PHASE2_FRAME_EFFECT_ORDER,
) -> dict[str, object]:
    """Return deterministic output, event, and organic traces for one case."""
    effects = {key: key in enabled for key in renderer.PHASE2_FRAME_EFFECT_ORDER}
    choreographer = renderer._FrameEffectChoreographer(
        effects,
        intensity,
        ORACLE_FPS,
        seed,
        oracle_transitions(),
        record_events=True,
    )
    output = hashlib.sha256()
    for frame_index in range(ORACLE_FRAME_COUNT):
        source = oracle_source_frame(frame_index)
        result = renderer._apply_phase2_frame_effects(
            source,
            effects,
            intensity,
            frame_index,
            ORACLE_FPS,
            seed,
            choreographer=choreographer,
            material=source,
        )
        output.update(np.asarray(result, dtype=np.uint8).tobytes())
    return {
        "output_sha256": output.hexdigest(),
        "events": choreographer.event_trace(),
        "organic_states": choreographer.organic_state_trace(),
    }


def zone_source_frame(
    frame_index: int,
    width: int = 160,
    height: int = 90,
    *,
    outside_variant: bool = False,
) -> np.ndarray:
    """Generate moving RGB material with an optional outside-only variant."""
    y, x = np.mgrid[0:height, 0:width]
    red = (x * 5 + y * 3 + frame_index * 11) % 256
    green = (x * 2 + y * 7 + frame_index * 13) % 256
    blue = ((x ^ y) * 9 + frame_index * 17) % 256
    rgb = np.stack((red, green, blue), axis=2).astype(np.uint8)
    if outside_variant:
        rgb[:, : width // 5] = np.array((3, 251, 19), dtype=np.uint8)
        rgb[: height // 6, :] = np.roll(
            rgb[: height // 6, :], frame_index * 7, axis=1
        )
    return rgb


def outside_mask(
    shape: tuple[int, int, int], rectangle: tuple[int, int, int, int]
) -> np.ndarray:
    mask = np.ones(shape[:2], dtype=bool)
    left, top, right, bottom = rectangle
    mask[top:bottom, left:right] = False
    return mask


def forced_control(seed: int = 99_173) -> renderer._FrameEffectControl:
    return renderer._FrameEffectControl(
        strength=1.0,
        event_strength=1.0,
        event_seed=seed,
        event_frame=7,
        focus_x=0.45,
        focus_y=0.55,
    )


def apply_direct_effect(
    effect: str,
    source: np.ndarray,
    *,
    intensity: float = 1.0,
    frame_index: int = 7,
    seed: int = 12_891,
    previous: np.ndarray | None = None,
) -> np.ndarray:
    """Exercise one existing full-frame effect seam with deterministic control."""
    analysis = renderer._FrameMaterialAnalysis(rgb=source.copy())
    control = forced_control(seed + 86_282)
    if effect == "pixel_sorting":
        return renderer._apply_pixel_sorting_frame(
            source, intensity, frame_index, seed, analysis, control
        )
    if effect == "databending":
        return renderer._apply_databending_frame(
            source, intensity, frame_index, 24, seed, analysis, control
        )
    if effect == "circuit_bending":
        return renderer._apply_circuit_bending_frame(
            source, intensity, frame_index, 24, seed, previous, analysis, control
        )
    if effect == "hex_editing":
        return renderer._apply_hex_editing_frame(
            source, intensity, frame_index, seed, analysis, control
        )
    if effect == "random_noise_bw":
        return renderer._apply_random_noise_bw_frame(
            source, intensity, frame_index, seed, analysis
        )
    raise AssertionError(f"unknown frame effect: {effect}")


def apply_forced_zone_effect(
    effect: str,
    source: np.ndarray,
    rectangle: tuple[int, int, int, int],
    *,
    intensity: float = 1.0,
    seed: int = 12_891,
    control: renderer._FrameEffectControl | None = None,
    previous: np.ndarray | None = None,
) -> np.ndarray:
    output = source.copy()
    left, top, right, bottom = rectangle
    analysis = renderer._FrameMaterialAnalysis(
        rgb=source[top:bottom, left:right].copy()
    )
    renderer._apply_phase2_zone_effect(
        effect,
        output,
        rectangle,
        intensity,
        7,
        24,
        seed,
        analysis,
        control or forced_control(),
        previous,
    )
    return output
