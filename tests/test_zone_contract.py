"""Tracked v0.4.0 frame-domain Zone contracts."""

from __future__ import annotations

import hashlib
import unittest

import numpy as np
from PIL import Image

import renderer
from tests.fixtures.helpers import (
    apply_forced_zone_effect,
    forced_control,
    outside_mask,
    zone_source_frame,
)


class ZoneContractTests(unittest.TestCase):
    def test_zone_normalization_maximum_and_clipped_geometry(self) -> None:
        first = {
            "id": "first",
            "name": "First",
            "x": 0.1,
            "y": 0.2,
            "width": 0.4,
            "height": 0.5,
        }
        partial = {
            "id": "partial",
            "name": "Partial",
            "x": -0.2,
            "y": 0.8,
            "width": 0.5,
            "height": 0.5,
        }
        records = [
            first,
            dict(first),
            "malformed",
            {"id": "nan", "name": "NaN", "x": float("nan"), "y": 0, "width": 1, "height": 1},
            {"id": "zero", "name": "Zero", "x": 0, "y": 0, "width": 0, "height": 1},
            {"id": "outside", "name": "Outside", "x": 1.2, "y": 0, "width": 0.2, "height": 0.2},
            partial,
        ]
        zones, assignments, repaired = renderer.normalize_zone_state(
            records,
            {
                "pixel_sorting": "partial",
                "databending": "missing",
                "datamoshing": "first",
            },
        )
        self.assertTrue(repaired)
        self.assertEqual([zone.id for zone in zones], ["first", "partial"])
        self.assertEqual(zones[0].name, "First")
        self.assertEqual(assignments, {"pixel_sorting": "partial"})
        self.assertEqual(
            renderer.rasterize_zone(zones[0], (101, 57)), (10, 11, 51, 40)
        )
        self.assertEqual(
            renderer.rasterize_zone(zones[1], (101, 57)), (0, 45, 31, 57)
        )
        self.assertEqual(renderer.normalize_zone_state({"bad": True}, ["bad"]), ((), {}, True))

        four_valid = [
            {"id": str(index), "name": str(index), "x": index * 0.1, "y": 0, "width": 0.1, "height": 0.2}
            for index in range(4)
        ]
        maximum, _, maximum_repaired = renderer.normalize_zone_state(four_valid, {})
        self.assertTrue(maximum_repaired)
        self.assertEqual([zone.id for zone in maximum], ["0", "1", "2"])

    def test_each_effect_one_zone_hard_containment(self) -> None:
        source = zone_source_frame(7)
        source_before = source.copy()
        rectangle = (31, 17, 131, 76)
        for effect in renderer.PHASE2_FRAME_EFFECT_ORDER:
            previous = (
                np.roll(source[17:76, 31:131], 3, axis=1)
                if effect == "circuit_bending"
                else None
            )
            output = apply_forced_zone_effect(
                effect, source, rectangle, intensity=1.0, previous=previous
            )
            changed = np.any(output != source, axis=2)
            self.assertTrue(changed[17:76, 31:131].any(), effect)
            self.assertFalse(changed[outside_mask(source.shape, rectangle)].any(), effect)
            self.assertEqual(output.dtype, np.uint8, effect)
            self.assertTrue(output.flags.writeable, effect)
            if effect == "random_noise_bw":
                roi = output[17:76, 31:131]
                self.assertTrue(set(np.unique(roi)).issubset({0, 255}))
                np.testing.assert_array_equal(roi[:, :, 0], roi[:, :, 1])
                np.testing.assert_array_equal(roi[:, :, 1], roi[:, :, 2])
        np.testing.assert_array_equal(source, source_before)

    def test_three_zones_are_deterministic_and_hard_contained(self) -> None:
        zones = (
            renderer.ZoneDefinition("a", "A", 0.08, 0.12, 0.28, 0.42),
            renderer.ZoneDefinition("b", "B", 0.62, 0.10, 0.30, 0.40),
            renderer.ZoneDefinition("c", "C", 0.34, 0.58, 0.32, 0.34),
        )
        assignments = {
            effect: zones[index % 3].id
            for index, effect in enumerate(renderer.PHASE2_FRAME_EFFECT_ORDER)
        }
        effects = {effect: True for effect in renderer.PHASE2_FRAME_EFFECT_ORDER}
        union = np.zeros((108, 192), dtype=bool)
        for zone in zones:
            left, top, right, bottom = renderer.rasterize_zone(zone, (192, 108))
            union[top:bottom, left:right] = True

        run_hashes: list[str] = []
        for _run in range(2):
            choreographer = renderer._FrameEffectChoreographer(effects, 1.45, 24, 7_719)
            digest = hashlib.sha256()
            for frame_index in range(24):
                source = zone_source_frame(frame_index, 192, 108)
                source_before = source.copy()
                output = np.asarray(
                    renderer._apply_phase2_frame_effects(
                        Image.fromarray(source, mode="RGB"),
                        effects,
                        1.45,
                        frame_index,
                        24,
                        7_719,
                        choreographer=choreographer,
                        material=source,
                        zones=zones,
                        effect_zone_assignments=assignments,
                    ),
                    dtype=np.uint8,
                )
                np.testing.assert_array_equal(output[~union], source[~union])
                np.testing.assert_array_equal(source, source_before)
                digest.update(output.tobytes())
            run_hashes.append(digest.hexdigest())
        self.assertEqual(run_hashes[0], run_hashes[1])
        self.assertEqual(len(choreographer.zone_previous_rgb), 3)

    def test_overlap_uses_fixed_effect_order(self) -> None:
        self.assertEqual(
            renderer.PHASE2_FRAME_EFFECT_ORDER,
            (
                "pixel_sorting",
                "databending",
                "circuit_bending",
                "hex_editing",
                "random_noise_bw",
            ),
        )
        source = zone_source_frame(7)
        zones = (
            renderer.ZoneDefinition("first", "First", 0.12, 0.14, 0.58, 0.62),
            renderer.ZoneDefinition("second", "Second", 0.38, 0.28, 0.54, 0.58),
        )
        rectangles = {
            zone.id: renderer.rasterize_zone(zone, (160, 90)) for zone in zones
        }
        controls = {
            "pixel_sorting": forced_control(81_001),
            "random_noise_bw": forced_control(82_001),
        }
        effects = {"pixel_sorting": True, "random_noise_bw": True}
        assignments = {"pixel_sorting": "first", "random_noise_bw": "second"}

        choreographer = renderer._FrameEffectChoreographer(effects, 1.0, 24, 33_201)
        choreographer.controls_for = lambda _analysis, _frame, _effect_analyses=None: controls
        actual = np.asarray(
            renderer._apply_phase2_frame_effects(
                Image.fromarray(source, mode="RGB"),
                effects,
                1.0,
                7,
                24,
                33_201,
                choreographer=choreographer,
                material=source,
                zones=zones,
                effect_zone_assignments=assignments,
            ),
            dtype=np.uint8,
        )

        fixed = source.copy()
        reverse = source.copy()
        for target, order in (
            (fixed, ("pixel_sorting", "random_noise_bw")),
            (reverse, ("random_noise_bw", "pixel_sorting")),
        ):
            for effect in order:
                rectangle = rectangles[assignments[effect]]
                left, top, right, bottom = rectangle
                renderer._apply_phase2_zone_effect(
                    effect,
                    target,
                    rectangle,
                    1.0,
                    7,
                    24,
                    33_201,
                    renderer._FrameMaterialAnalysis(
                        rgb=source[top:bottom, left:right].copy()
                    ),
                    controls[effect],
                    None,
                )
        np.testing.assert_array_equal(actual, fixed)
        self.assertFalse(np.array_equal(fixed, reverse))

    def test_outside_material_isolation(self) -> None:
        zone = renderer.ZoneDefinition("isolation", "Isolation", 0.25, 0.22, 0.5, 0.56)
        rectangle = renderer.rasterize_zone(zone, (160, 90))
        left, top, right, bottom = rectangle
        for effect in ("pixel_sorting", "circuit_bending"):
            effects = {effect: True}
            choreographers = (
                renderer._FrameEffectChoreographer(effects, 1.45, 24, 4_711, record_events=True),
                renderer._FrameEffectChoreographer(effects, 1.45, 24, 4_711, record_events=True),
            )
            digests = [hashlib.sha256(), hashlib.sha256()]
            for frame_index in range(48):
                base = zone_source_frame(frame_index)
                variant = zone_source_frame(frame_index, outside_variant=True)
                variant[top:bottom, left:right] = base[top:bottom, left:right]
                outputs = []
                for source, choreographer in zip((base, variant), choreographers):
                    source_before = source.copy()
                    output = np.asarray(
                        renderer._apply_phase2_frame_effects(
                            Image.fromarray(source, mode="RGB"),
                            effects,
                            1.45,
                            frame_index,
                            24,
                            4_711,
                            choreographer=choreographer,
                            material=source,
                            zones=(zone,),
                            effect_zone_assignments={effect: zone.id},
                        ),
                        dtype=np.uint8,
                    )
                    np.testing.assert_array_equal(source, source_before)
                    outputs.append(output)
                np.testing.assert_array_equal(
                    outputs[0][top:bottom, left:right],
                    outputs[1][top:bottom, left:right],
                )
                for digest, output in zip(digests, outputs):
                    digest.update(output[top:bottom, left:right].tobytes())
            self.assertEqual(digests[0].hexdigest(), digests[1].hexdigest(), effect)
            self.assertEqual(
                choreographers[0].event_trace(), choreographers[1].event_trace(), effect
            )
            self.assertEqual(
                choreographers[0].organic_state_trace(),
                choreographers[1].organic_state_trace(),
                effect,
            )

    def test_circuit_zone_history_and_reset(self) -> None:
        zone = renderer.ZoneDefinition("history", "History", 0.25, 0.22, 0.5, 0.56)
        rectangle = renderer.rasterize_zone(zone, (160, 90))
        left, top, right, bottom = rectangle
        effects = {"circuit_bending": True}
        choreographer = renderer._FrameEffectChoreographer(effects, 1.45, 24, 8_099)
        for frame_index in range(12):
            source = zone_source_frame(frame_index)
            renderer._apply_phase2_frame_effects(
                Image.fromarray(source, mode="RGB"),
                effects,
                1.45,
                frame_index,
                24,
                8_099,
                choreographer=choreographer,
                material=source,
                zones=(zone,),
                effect_zone_assignments={"circuit_bending": zone.id},
            )
            np.testing.assert_array_equal(
                choreographer.zone_previous_rgb[rectangle],
                source[top:bottom, left:right],
            )
            self.assertEqual(
                choreographer.zone_previous_rgb[rectangle].shape,
                (bottom - top, right - left, 3),
            )

        choreographer.reset_temporal_state()
        self.assertFalse(choreographer.zone_previous_rgb)
        self.assertFalse(choreographer.zone_previous_luma)
        fresh = renderer._FrameEffectChoreographer(effects, 1.45, 24, 8_099)
        source = zone_source_frame(0)
        reset_output = renderer._apply_phase2_frame_effects(
            Image.fromarray(source, mode="RGB"),
            effects,
            1.45,
            0,
            24,
            8_099,
            choreographer=choreographer,
            material=source,
            zones=(zone,),
            effect_zone_assignments={"circuit_bending": zone.id},
        )
        fresh_output = renderer._apply_phase2_frame_effects(
            Image.fromarray(source, mode="RGB"),
            effects,
            1.45,
            0,
            24,
            8_099,
            choreographer=fresh,
            material=source,
            zones=(zone,),
            effect_zone_assignments={"circuit_bending": zone.id},
        )
        np.testing.assert_array_equal(
            np.asarray(reset_output, dtype=np.uint8),
            np.asarray(fresh_output, dtype=np.uint8),
        )
        np.testing.assert_array_equal(
            choreographer.zone_previous_rgb[rectangle], fresh.zone_previous_rgb[rectangle]
        )


if __name__ == "__main__":
    unittest.main()
