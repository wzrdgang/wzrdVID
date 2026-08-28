"""Tracked v0.4.0 Full Frame and Material Dynamics contracts."""

from __future__ import annotations

import hashlib
import random
import unittest
from unittest import mock

import numpy as np

import renderer
from tests.fixtures.helpers import (
    ORACLE_FRAME_COUNT,
    ORACLE_INTENSITIES,
    ORACLE_SEED,
    ORACLE_SHA256,
    apply_direct_effect,
    material_case,
    material_oracle_records,
    oracle_source_frame,
    serialized_oracle,
    zone_source_frame,
)


class MaterialContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle_records, cls.oracle_source_immutable = material_oracle_records()
        cls.oracle_sha256 = hashlib.sha256(
            serialized_oracle(cls.oracle_records)
        ).hexdigest()

    def test_18_case_full_frame_oracle(self) -> None:
        expected_keys = {
            f"{intensity:.2f}:" + ",".join(enabled)
            for intensity in ORACLE_INTENSITIES
            for enabled in (
                *((effect,) for effect in renderer.PHASE2_FRAME_EFFECT_ORDER),
                renderer.PHASE2_FRAME_EFFECT_ORDER,
            )
        }
        self.assertEqual(set(self.oracle_records), expected_keys)
        self.assertEqual(len(self.oracle_records), 18)
        self.assertTrue(self.oracle_source_immutable)
        self.assertTrue(
            all(
                len(record["frame_sha256"]) == ORACLE_FRAME_COUNT
                for record in self.oracle_records.values()
            )
        )
        self.assertEqual(self.oracle_sha256, ORACLE_SHA256)
        print(f"FULL_FRAME_ORACLE_SHA256={self.oracle_sha256}")

        source = zone_source_frame(7)
        source_before = source.copy()
        for effect in renderer.PHASE2_FRAME_EFFECT_ORDER:
            previous = np.roll(source, 3, axis=1) if effect == "circuit_bending" else None
            output = apply_direct_effect(effect, source, previous=previous)
            self.assertEqual(output.dtype, np.uint8, effect)
            self.assertEqual(output.shape, source.shape, effect)
            self.assertTrue(output.flags.writeable, effect)
        self.assertTrue(np.array_equal(source, source_before))

    def test_full_frame_never_calls_zone_only_path(self) -> None:
        effects = {key: True for key in renderer.PHASE2_FRAME_EFFECT_ORDER}
        source = oracle_source_frame(4)
        with mock.patch.object(
            renderer,
            "_apply_phase2_zone_effect",
            side_effect=AssertionError("Full Frame entered the Zone-only path"),
        ):
            result = renderer._apply_phase2_frame_effects(
                source,
                effects,
                1.0,
                4,
                24,
                ORACLE_SEED,
                zones=(),
                effect_zone_assignments={},
            )
        self.assertEqual(result.size, source.size)

    def test_material_seed_intensity_and_global_rng_contract(self) -> None:
        python_state = random.getstate()
        numpy_state = np.random.get_state()
        try:
            random.seed(90_211)
            expected_python = [random.random() for _ in range(4)]
            random.seed(90_211)
            np.random.seed(41_009)
            expected_numpy = np.random.random(4)
            np.random.seed(41_009)

            first = material_case(1.0, ORACLE_SEED)
            repeated = material_case(1.0, ORACLE_SEED)
            changed = material_case(1.0, ORACLE_SEED + 1)

            self.assertEqual(first, repeated)
            self.assertNotEqual(first["output_sha256"], changed["output_sha256"])
            self.assertNotEqual(first["events"], changed["events"])
            self.assertEqual([random.random() for _ in range(4)], expected_python)
            np.testing.assert_array_equal(np.random.random(4), expected_numpy)
        finally:
            random.setstate(python_state)
            np.random.set_state(numpy_state)

        all_effects = ",".join(renderer.PHASE2_FRAME_EFFECT_ORDER)
        intensity_hashes = {
            self.oracle_records[f"{intensity:.2f}:{all_effects}"]["combined_sha256"]
            for intensity in ORACLE_INTENSITIES
        }
        self.assertEqual(len(intensity_hashes), 3)
        self.assertTrue(first["events"])
        self.assertEqual(len(first["organic_states"]), ORACLE_FRAME_COUNT)

    def test_random_noise_bw_binary_and_seed_contract(self) -> None:
        source = oracle_source_frame(11)
        effects = {"random_noise_bw": True}
        first = renderer._apply_phase2_frame_effects(
            source, effects, 1.45, 11, 24, ORACLE_SEED
        )
        repeated = renderer._apply_phase2_frame_effects(
            source, effects, 1.45, 11, 24, ORACLE_SEED
        )
        changed = renderer._apply_phase2_frame_effects(
            source, effects, 1.45, 11, 24, ORACLE_SEED + 1
        )
        first_array = np.asarray(first, dtype=np.uint8)
        self.assertTrue(set(np.unique(first_array)).issubset({0, 255}))
        np.testing.assert_array_equal(first_array[:, :, 0], first_array[:, :, 1])
        np.testing.assert_array_equal(first_array[:, :, 1], first_array[:, :, 2])
        np.testing.assert_array_equal(first_array, np.asarray(repeated, dtype=np.uint8))
        self.assertFalse(np.array_equal(first_array, np.asarray(changed, dtype=np.uint8)))


if __name__ == "__main__":
    unittest.main()
