"""Deterministic persisted and geometric Zone Motion contracts."""

from __future__ import annotations

import hashlib
import math
import unittest
from unittest import mock

from state_contract import ZoneDefinition, normalize_zone_state
import zone_motion
import renderer


BASE = {
    "id": "zone-alpha",
    "name": "Alpha",
    "x": 0.2,
    "y": 0.25,
    "width": 0.3,
    "height": 0.4,
}


class ZoneMotionContractTests(unittest.TestCase):
    def test_static_is_the_absent_field_canonical_form(self) -> None:
        zones, _assignments, repaired = normalize_zone_state([BASE], {})
        self.assertFalse(repaired)
        self.assertEqual(zones[0].as_dict(), BASE)

        stale = {**BASE, "motion_mode": "static", "motion_amount": 44, "motion_cycles": 7}
        zones, _assignments, repaired = normalize_zone_state([stale], {})
        self.assertTrue(repaired)
        self.assertIsNone(zones[0].motion_mode)
        self.assertEqual(zones[0].as_dict(), BASE)

    def test_moving_defaults_clamps_and_malformed_repairs(self) -> None:
        cases = (
            ({**BASE, "motion_mode": "drift"}, ("drift", 25.0, 2), False),
            (
                {**BASE, "motion_mode": "pulse", "motion_amount": -7, "motion_cycles": 99},
                ("pulse", 0.0, 8),
                True,
            ),
            (
                {**BASE, "motion_mode": "drift", "motion_amount": math.inf, "motion_cycles": 3.0},
                ("drift", 25.0, 2),
                True,
            ),
            (
                {**BASE, "motion_mode": "wobble", "motion_amount": 50, "motion_cycles": 8},
                (None, 25.0, 2),
                True,
            ),
            (
                {**BASE, "motion_mode": {"bad": True}},
                (None, 25.0, 2),
                True,
            ),
        )
        for record, expected, expected_repaired in cases:
            with self.subTest(record=record):
                zones, _assignments, repaired = normalize_zone_state([record], {})
                zone = zones[0]
                self.assertEqual(
                    (zone.motion_mode, zone.motion_amount, zone.motion_cycles), expected
                )
                self.assertEqual(repaired, expected_repaired)
                self.assertEqual(
                    set(zone.as_dict()) - set(BASE),
                    {"motion_mode", "motion_amount", "motion_cycles"}
                    if zone.motion_mode
                    else set(),
                )

    def test_exact_seed_domain_and_fixed_digest_chunks(self) -> None:
        expected = {
            "drift-c": (
                "90dfe3c61c6fd23c91f49b36fb8651ac13377264f925f423ce61d811142457cf",
                10_439_312_901_288_219_196,
            ),
            "pulse-b": (
                "532b019b8c825bd11cd7c10d4b1d4f0722abb71f850c37acbc48d1c6cc1bca5a",
                5_992_885_496_735_488_977,
            ),
        }
        for model, (expected_hex, expected_seed) in expected.items():
            payload = (
                b"WZRDVID_ZONE_MOTION_V1\0"
                + b"1771336264\0zone-alpha\0"
                + model.encode("ascii")
            )
            digest = hashlib.sha256(payload).digest()
            self.assertEqual(digest.hex(), expected_hex)
            self.assertEqual(
                zone_motion.stable_motion_seed(1771336264, "zone-alpha", model),
                expected_seed,
            )
            self.assertEqual(
                zone_motion._digest_units(1771336264, "zone-alpha", model),
                tuple(
                    int.from_bytes(digest[offset : offset + 8], "big")
                    / float((1 << 64) - 1)
                    for offset in range(0, 32, 8)
                ),
            )

    def test_amount_zero_and_static_return_exact_base_before_seed_work(self) -> None:
        static = ZoneDefinition(**BASE)
        zero = ZoneDefinition(**BASE, motion_mode="drift", motion_amount=0.0, motion_cycles=8)
        with mock.patch.object(zone_motion, "_digest_units", side_effect=AssertionError("seeded")):
            self.assertIs(zone_motion.resolve_zone_motion(static, 7, 2.0, 8.0), static)
            self.assertIs(zone_motion.resolve_zone_motion(zero, 7, 2.0, 8.0), zero)

    def test_selected_models_are_contained_deterministic_and_close_exactly(self) -> None:
        for mode in ("drift", "pulse"):
            zone = ZoneDefinition(
                **BASE,
                motion_mode=mode,
                motion_amount=50.0,
                motion_cycles=8,
            )
            start = zone_motion.resolve_zone_motion(zone, 1771336264, 0.0, 10.0)
            end = zone_motion.resolve_zone_motion(zone, 1771336264, 10.0, 10.0)
            self.assertEqual(start.as_dict(), end.as_dict())
            repeat = zone_motion.resolve_zone_motion(zone, 1771336264, 2.75, 10.0)
            self.assertEqual(
                repeat.as_dict(),
                zone_motion.resolve_zone_motion(zone, 1771336264, 2.75, 10.0).as_dict(),
            )
            for step in range(101):
                resolved = zone_motion.resolve_zone_motion(
                    zone, 1771336264, 10.0 * step / 100.0, 10.0
                )
                self.assertGreater(resolved.width, 0.0)
                self.assertGreater(resolved.height, 0.0)
                self.assertGreaterEqual(resolved.x, -1e-12)
                self.assertGreaterEqual(resolved.y, -1e-12)
                self.assertLessEqual(resolved.x + resolved.width, 1.0 + 1e-12)
                self.assertLessEqual(resolved.y + resolved.height, 1.0 + 1e-12)
                if mode == "drift":
                    self.assertEqual(resolved.width, zone.width)
                    self.assertEqual(resolved.height, zone.height)
                else:
                    self.assertAlmostEqual(
                        resolved.width / resolved.height,
                        zone.width / zone.height,
                        places=12,
                    )
                    self.assertAlmostEqual(
                        resolved.x + resolved.width / 2.0,
                        zone.x + zone.width / 2.0,
                        places=12,
                    )
                    self.assertAlmostEqual(
                        resolved.y + resolved.height / 2.0,
                        zone.y + zone.height / 2.0,
                        places=12,
                    )

    def test_preview_windows_resolve_the_same_absolute_geometry_as_full_output(self) -> None:
        zone = ZoneDefinition(
            **BASE, motion_mode="drift", motion_amount=25.0, motion_cycles=4
        )
        duration = 23.75
        windows = {
            "start": (0.0, 5.0),
            "five-second": (5.0, 5.0),
            "ten-second": (10.0, 10.0),
            "middle": (duration / 2.0, 5.0),
            "custom": (7.35, 5.0),
            "style-crossing": (3.5, 5.0),
            "clean-crossing": (12.25, 5.0),
            "near-end": (duration - 1.0, 1.0),
        }
        fps = 24
        for label, (offset, length) in windows.items():
            with self.subTest(label=label):
                for local_frame in (0, max(0, int(length * fps) - 1)):
                    absolute_time = offset + local_frame / fps
                    full = zone_motion.resolve_zone_motion(
                        zone, 88_121, absolute_time, duration
                    )
                    preview = zone_motion.resolve_zone_motion(
                        zone,
                        88_121,
                        offset + local_frame / fps,
                        duration,
                    )
                    self.assertEqual(full.as_dict(), preview.as_dict())

    def test_skrrt_uses_the_saved_static_base_rectangle_for_moving_zone(self) -> None:
        static = ZoneDefinition(**BASE)
        moving = ZoneDefinition(
            **BASE, motion_mode="pulse", motion_amount=50.0, motion_cycles=8
        )

        def operation(zone: ZoneDefinition) -> object:
            settings = renderer.RenderSettings(
                video_path="source.mp4",
                output_path="output.mp4",
                audio_path=None,
                video_start=0.0,
                video_end=None,
                audio_start=0.0,
                audio_end=None,
                preset_name="Classic ANSI",
                fps=24,
                width_chars=80,
                output_size=(640, 360),
                effects={"skrrt": True},
                zones=(zone,),
                effect_zone_assignments={"skrrt": zone.id},
                weird_seed=19_881,
            )
            return renderer._datamosh_operations(
                settings,
                ("skrrt",),
                0,
                120,
                0,
                (),
                (),
            )[0]

        self.assertEqual(operation(static).zone_box, operation(moving).zone_box)
        self.assertEqual(
            operation(moving).zone_box,
            renderer.rasterize_zone(static, (640, 360)),
        )


if __name__ == "__main__":
    unittest.main()
