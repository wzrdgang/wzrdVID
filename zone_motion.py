"""Pure deterministic Zone Motion geometry for the desktop renderer."""

from __future__ import annotations

import hashlib
import math

from state_contract import ZoneDefinition


MOTION_DOMAIN = b"WZRDVID_ZONE_MOTION_V1\0"
_UINT64_MAX = float((1 << 64) - 1)


def _motion_digest(weird_seed: int | None, zone_id: str, model: str) -> bytes:
    payload = (
        MOTION_DOMAIN
        + str(int(weird_seed or 0)).encode("utf-8")
        + b"\0"
        + zone_id.encode("utf-8")
        + b"\0"
        + model.encode("ascii")
    )
    return hashlib.sha256(payload).digest()


def stable_motion_seed(weird_seed: int | None, zone_id: str, model: str) -> int:
    """Return the unsigned big-endian seed fixed by the Zone Motion domain."""
    return int.from_bytes(_motion_digest(weird_seed, zone_id, model)[:8], "big")


def _digest_units(weird_seed: int | None, zone_id: str, model: str) -> tuple[float, ...]:
    digest = _motion_digest(weird_seed, zone_id, model)
    return tuple(
        int.from_bytes(digest[offset : offset + 8], "big") / _UINT64_MAX
        for offset in range(0, 32, 8)
    )


def _progress(absolute_time: float, full_duration: float) -> float:
    try:
        time_value = float(absolute_time)
        duration_value = float(full_duration)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(time_value) or not math.isfinite(duration_value) or duration_value <= 0.0:
        return 0.0
    return min(1.0, max(0.0, time_value / duration_value))


def _resolved(zone: ZoneDefinition, x: float, y: float, width: float, height: float) -> ZoneDefinition:
    return ZoneDefinition(zone.id, zone.name, x, y, width, height)


def resolve_zone_motion(
    zone: ZoneDefinition,
    weird_seed: int | None,
    absolute_time: float,
    full_duration: float,
) -> ZoneDefinition:
    """Resolve one persisted base Zone at an absolute assembled-output time."""
    if zone.motion_mode not in {"drift", "pulse"} or zone.motion_amount <= 0.0:
        return zone

    amount = max(0.0, min(50.0, float(zone.motion_amount))) / 100.0
    cycles = max(1, min(8, int(zone.motion_cycles)))
    progress = _progress(absolute_time, full_duration)
    phase_progress = 0.0 if progress >= 1.0 else progress

    if zone.motion_mode == "drift":
        unit_0, unit_1, unit_2, unit_3 = _digest_units(
            weird_seed, zone.id, "drift-c"
        )
        theta = math.tau * (cycles * phase_progress + unit_0)
        weight_x = 0.20 + 0.25 * unit_2
        weight_y = 0.20 + 0.25 * unit_3
        wave_x = (
            math.sin(theta)
            + weight_x * math.sin(2.0 * theta + math.tau * unit_1)
        ) / (1.0 + weight_x)
        wave_y = (
            math.sin(theta + math.tau * unit_1)
            + weight_y * math.sin(3.0 * theta + math.tau * unit_2)
        ) / (1.0 + weight_y)
        target_x = max(0.0, 1.0 - zone.width) * (0.5 + 0.5 * wave_x)
        target_y = max(0.0, 1.0 - zone.height) * (0.5 + 0.5 * wave_y)
        return _resolved(
            zone,
            zone.x + amount * (target_x - zone.x),
            zone.y + amount * (target_y - zone.y),
            zone.width,
            zone.height,
        )

    unit_0, unit_1, unit_2, _unit_3 = _digest_units(
        weird_seed, zone.id, "pulse-b"
    )
    theta = math.tau * (cycles * phase_progress + unit_0)
    weight = 0.18 + 0.22 * unit_2
    wave = (
        math.sin(theta)
        + weight * math.sin(2.0 * theta + math.tau * unit_1)
    ) / (1.0 + weight)
    center_x = zone.x + zone.width / 2.0
    center_y = zone.y + zone.height / 2.0
    center_fit_limit = max(
        1.0,
        min(
            2.0 * center_x / zone.width,
            2.0 * (1.0 - center_x) / zone.width,
            2.0 * center_y / zone.height,
            2.0 * (1.0 - center_y) / zone.height,
        ),
    )
    scale = min(1.0 + amount * wave, center_fit_limit)
    width = max(1e-9, zone.width * scale)
    height = max(1e-9, zone.height * scale)
    return _resolved(
        zone,
        center_x - width / 2.0,
        center_y - height / 2.0,
        width,
        height,
    )
