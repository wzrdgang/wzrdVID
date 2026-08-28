"""Tracked MPEG-4 structure, DATAMOSHING, spILL!, and FLOWs contracts."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import datamosh

from tests.fixtures.codec_helpers import (
    build_controlled_codec_fixture,
    build_organic_fixture,
    codec_operation,
    event_targets,
    organic_overflow_operation,
    sha256_path,
    synthetic_mpeg4_stream,
)


class CodecStructureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="wzrdvid-codec-structure-")
        cls.root = Path(cls._temporary.name)
        cls.source, cls.controlled_path, cls.controlled_data = (
            build_controlled_codec_fixture(cls.root)
        )
        cls.source_sha256 = sha256_path(cls.source)
        cls.organic_source, cls.organic_data, cls.organic_activity = (
            build_organic_fixture(cls.root)
        )
        cls.organic_source_sha256 = sha256_path(cls.organic_source)

    @classmethod
    def tearDownClass(cls) -> None:
        root = cls.root
        cls._temporary.cleanup()
        if root.exists():
            raise AssertionError(f"codec fixture temporary directory leaked: {root}")

    def test_controlled_vop_structure_and_malformed_rejection(self) -> None:
        units = datamosh.parse_mpeg4_units(self.controlled_data)
        vops = datamosh.vop_units(units)
        counts = datamosh.vop_type_counts(units)
        self.assertEqual(len(vops), 48)
        self.assertEqual(counts["I"] + counts["P"], 48)
        self.assertGreaterEqual(counts["I"], 2)
        self.assertGreater(counts["P"], 0)
        self.assertEqual((counts["B"], counts["S"]), (0, 0))
        self.assertEqual(vops[0].coding_type, 0)

        for malformed in (b"", b"not-mpeg4", b"\x00\x00\x01", b"\x00\x00\x01\xb6"):
            with self.subTest(malformed=malformed):
                with self.assertRaises(datamosh.DatamoshError):
                    datamosh.parse_mpeg4_units(malformed)

        for label, stream in (
            ("B", synthetic_mpeg4_stream((0, 2, 1))),
            ("S", synthetic_mpeg4_stream((0, 3, 1))),
            ("missing-anchor", synthetic_mpeg4_stream((1, 1, 1))),
        ):
            with self.subTest(label=label):
                operation = replace(codec_operation("datamoshing"), end_frame=3)
                with self.assertRaises(datamosh.DatamoshError):
                    datamosh.transform_mpeg4_operations(stream, (operation,))

    def test_auxiliary_validator_requires_one_initial_i_then_p_only(self) -> None:
        valid = synthetic_mpeg4_stream((0, 1, 1, 1))
        vops = datamosh._validate_auxiliary_prediction_structure(
            valid,
            expected_count=4,
            mode_label="TRACKED TEST",
            window_number=1,
            source_start_frame=2,
            source_end_frame=6,
        )
        self.assertEqual(tuple(unit.coding_type for unit in vops), (0, 1, 1, 1))

        invalid = (
            ("wrong-count", valid, 5),
            ("second-i", synthetic_mpeg4_stream((0, 1, 0, 1)), 4),
            ("b-vop", synthetic_mpeg4_stream((0, 1, 2, 1)), 4),
            ("s-vop", synthetic_mpeg4_stream((0, 1, 3, 1)), 4),
            ("p-first", synthetic_mpeg4_stream((1, 1, 1, 1)), 4),
            ("truncated", b"\x00\x00\x01\xb6", 1),
        )
        for label, stream, expected_count in invalid:
            with self.subTest(label=label):
                with self.assertRaises(datamosh.DatamoshError):
                    datamosh._validate_auxiliary_prediction_structure(
                        stream,
                        expected_count=expected_count,
                        mode_label="TRACKED TEST",
                        window_number=2,
                        source_start_frame=4,
                        source_end_frame=8,
                    )

    def test_datamoshing_is_deterministic_and_flows_is_transition_only(self) -> None:
        general = codec_operation("datamoshing", intensity=1.3)
        first = datamosh._transform_general_operation(self.controlled_data, general)
        second = datamosh._transform_general_operation(self.controlled_data, general)
        self.assertEqual(first.data, second.data)
        self.assertEqual(first.events, second.events)
        self.assertNotEqual(first.data, self.controlled_data)
        self.assertTrue(first.events)

        flows = codec_operation("bleed", intensity=2.0)
        active = datamosh._transform_bleed_operation(self.controlled_data, flows)
        inactive = datamosh._transform_bleed_operation(
            self.controlled_data,
            replace(flows, transitions=()),
        )
        self.assertTrue(active.events)
        self.assertTrue(
            all(event.transition_absolute_frame is not None for event in active.events)
        )
        self.assertEqual(inactive.events, ())
        self.assertEqual(inactive.data, self.controlled_data)
        self.assertEqual(sha256_path(self.source), self.source_sha256)

    def test_canonical_spill_intensity_ancestry_refresh_and_recovery(self) -> None:
        expected = {
            0.7: (10, 0, 0),
            1.3: (42, 16, 4),
            2.0: (60, 60, 7),
        }
        controlled_vops = datamosh.vop_units(
            datamosh.parse_mpeg4_units(self.organic_data)
        )
        for intensity, (changed_count, recursive_count, maximum_depth) in expected.items():
            with self.subTest(intensity=intensity):
                operation = organic_overflow_operation(self.organic_activity, intensity)
                first = datamosh._transform_overflow_operation(
                    self.organic_data, operation
                )
                second = datamosh._transform_overflow_operation(
                    self.organic_data, operation
                )
                self.assertEqual(first.data, second.data)
                self.assertEqual(first.events, second.events)
                output_vops = datamosh.vop_units(
                    datamosh.parse_mpeg4_units(first.data)
                )
                changed = {
                    frame
                    for frame, (before, after) in enumerate(
                        zip(controlled_vops, output_vops)
                    )
                    if before.data != after.data
                }
                recursive = tuple(
                    event
                    for event in first.events
                    if event.operation.startswith("OVERFLOW_DECAYING_RECURSIVE_")
                )
                self.assertEqual(len(changed), changed_count)
                self.assertEqual(len(recursive), recursive_count)
                self.assertEqual(
                    max((int(event.flow_chain_depth or 0) for event in recursive), default=0),
                    maximum_depth,
                )
                self.assertEqual(changed, event_targets(first.events))

                seen_targets: set[int] = set()
                recursively_sourced = 0
                for event in recursive:
                    targets = event.repeated_at_frames or (event.frame,)
                    if event.source_p_frame in seen_targets:
                        recursively_sourced += 1
                    for target in targets:
                        self.assertEqual(
                            output_vops[target].data,
                            output_vops[event.source_p_frame].data,
                        )
                        seen_targets.add(int(target))
                    self.assertGreater(int(event.flow_refresh_interval or 0), 0)
                    self.assertLessEqual(
                        int(event.flow_chain_depth or 0),
                        int(event.flow_refresh_interval or 0),
                    )
                if recursive:
                    self.assertGreater(recursively_sourced, 0)

                recoveries = {
                    int(event.recovery_frame)
                    for event in recursive
                    if event.recovery_frame is not None
                    and int(event.recovery_frame) < len(controlled_vops)
                }
                for recovery in recoveries:
                    self.assertEqual(
                        output_vops[recovery].data,
                        controlled_vops[recovery].data,
                    )
        self.assertEqual(sha256_path(self.organic_source), self.organic_source_sha256)


if __name__ == "__main__":
    unittest.main()
