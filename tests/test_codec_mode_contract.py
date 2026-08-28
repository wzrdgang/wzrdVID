"""Tracked SKRRT, ShShSHa, protected-interval, and recovery contracts."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import datamosh
import renderer

from tests.fixtures.codec_helpers import (
    CODEC_FPS,
    build_controlled_codec_fixture,
    codec_operation,
    event_targets,
    sha256_path,
)


class CodecModeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="wzrdvid-codec-modes-")
        cls.root = Path(cls._temporary.name)
        cls.source, cls.controlled_path, cls.controlled_data = (
            build_controlled_codec_fixture(cls.root)
        )
        cls.source_sha256 = sha256_path(cls.source)
        cls.controlled_vops = datamosh.vop_units(
            datamosh.parse_mpeg4_units(cls.controlled_data)
        )

        cls.full_operation, cls.full_repeat_operation = cls._prepare_skrrt_pair(
            "full", None
        )
        cls.central_operation, _ = cls._prepare_skrrt_pair(
            "central", (42, 20, 118, 72)
        )
        cls.edge_operation, _ = cls._prepare_skrrt_pair(
            "edge", (0, 0, 48, 38)
        )
        cls.scatter_operation, cls.scatter_repeat_operation = (
            cls._prepare_scatter_pair()
        )

    @classmethod
    def _prepare_skrrt_pair(
        cls,
        label: str,
        zone_box: tuple[int, int, int, int] | None,
    ) -> tuple[datamosh.DatamoshOperation, datamosh.DatamoshOperation]:
        operation = codec_operation("skrrt", zone_box=zone_box)
        prepared, _ = datamosh._prepare_skrrt_operations(
            cls.controlled_path,
            cls.root / f"skrrt-{label}",
            cls.controlled_vops,
            (operation,),
            fps=CODEC_FPS,
            log=None,
        )
        repeated, _ = datamosh._prepare_skrrt_operations(
            cls.controlled_path,
            cls.root / f"skrrt-{label}-repeat",
            cls.controlled_vops,
            (operation,),
            fps=CODEC_FPS,
            log=None,
        )
        return prepared[0], repeated[0]

    @classmethod
    def _prepare_scatter_pair(
        cls,
    ) -> tuple[datamosh.DatamoshOperation, datamosh.DatamoshOperation]:
        operation = codec_operation("scatter")
        prepared, _ = datamosh._prepare_scatter_operations(
            cls.controlled_path,
            cls.root / "scatter",
            cls.controlled_vops,
            (operation,),
            fps=CODEC_FPS,
            log=None,
        )
        repeated, _ = datamosh._prepare_scatter_operations(
            cls.controlled_path,
            cls.root / "scatter-repeat",
            cls.controlled_vops,
            (operation,),
            fps=CODEC_FPS,
            log=None,
        )
        return prepared[0], repeated[0]

    @classmethod
    def tearDownClass(cls) -> None:
        root = cls.root
        cls._temporary.cleanup()
        if root.exists():
            raise AssertionError(f"codec-mode temporary directory leaked: {root}")

    def test_skrrt_full_frame_reverse_provenance_and_determinism(self) -> None:
        self.assertEqual(len(self.full_operation.prepared_windows), 1)
        window = self.full_operation.prepared_windows[0]
        repeated = self.full_repeat_operation.prepared_windows[0]
        self.assertIsNone(window.zone_box)
        self.assertEqual(
            window.source_reversed_order,
            tuple(reversed(window.source_chronological_order)),
        )
        self.assertEqual(window.reverse_vop_count, len(window.source_reversed_order))
        self.assertEqual(len(window.prediction_vops), window.reverse_vop_count - 1)
        self.assertEqual(window.reverse_stream_sha256, repeated.reverse_stream_sha256)
        self.assertEqual(window.prediction_vops, repeated.prediction_vops)
        self.assertNotIn(window.recovery_frame, window.target_frames)

        transformed = datamosh._transform_skrrt_operation(
            self.controlled_data, self.full_operation
        )
        self.assertTrue(transformed.events)
        primary = next(
            event
            for event in transformed.events
            if event.operation == "SKRRT_REVERSE_PREDICTION_DRAG"
        )
        self.assertEqual(primary.source_frame_order, window.source_chronological_order)
        self.assertEqual(primary.reversed_source_frame_order, window.source_reversed_order)
        self.assertEqual(primary.reverse_stream_sha256, window.reverse_stream_sha256)

    def test_skrrt_zone_central_and_edge_preserve_exact_prepared_provenance(self) -> None:
        full = self.full_operation.prepared_windows[0]
        for label, operation in (
            ("central", self.central_operation),
            ("edge", self.edge_operation),
        ):
            with self.subTest(label=label):
                self.assertEqual(len(operation.prepared_windows), 1)
                window = operation.prepared_windows[0]
                self.assertIsNotNone(window.zone_box)
                self.assertTrue(window.prepared_inside_exact)
                self.assertTrue(window.prepared_outside_exact)
                self.assertEqual(
                    window.source_chronological_order,
                    full.source_chronological_order,
                )
                self.assertEqual(window.source_reversed_order, full.source_reversed_order)
                self.assertEqual(
                    len(window.current_frame_sha256s), window.reverse_vop_count
                )
                self.assertEqual(
                    len(window.reverse_source_frame_sha256s), window.reverse_vop_count
                )
                self.assertEqual(
                    len(window.prepared_frame_sha256s), window.reverse_vop_count
                )
                self.assertEqual(len(window.prediction_vops), window.reverse_vop_count - 1)
                transformed = datamosh._transform_skrrt_operation(
                    self.controlled_data, operation
                )
                self.assertTrue(transformed.events)

    def test_shshsha_multi_time_provenance_determinism_and_zone_ineligibility(self) -> None:
        self.assertEqual(len(self.scatter_operation.prepared_scatter_windows), 1)
        window = self.scatter_operation.prepared_scatter_windows[0]
        repeated = self.scatter_repeat_operation.prepared_scatter_windows[0]
        offsets = {fragment.temporal_offset for fragment in window.fragments}
        self.assertGreaterEqual(len(offsets), 2)
        self.assertNotIn(0, offsets)
        self.assertTrue(any(offset < 0 for offset in offsets))
        self.assertTrue(any(offset > 0 for offset in offsets))
        self.assertEqual(window.prepared_stream_sha256, repeated.prepared_stream_sha256)
        self.assertEqual(window.prediction_vops, repeated.prediction_vops)
        self.assertEqual(window.prepared_vop_count, len(window.prediction_vops) + 1)
        self.assertEqual(
            len(window.prepared_frame_sha256s), window.prepared_vop_count
        )
        for fragment in window.fragments:
            self.assertIsNotNone(fragment.source_frame_sha256)
            self.assertEqual(
                fragment.source_region_sha256, fragment.prepared_region_sha256
            )
            self.assertLessEqual(
                float(fragment.provenance_mean_absolute_delta or 0.0), 2.0
            )
        transformed = datamosh._transform_scatter_operation(
            self.controlled_data, self.scatter_operation
        )
        primary = next(
            event
            for event in transformed.events
            if event.operation == "SCATTER_MULTI_TIME_FRAGMENTATION"
        )
        self.assertEqual(primary.scatter_fragments, window.fragments)
        self.assertEqual(primary.scatter_stream_sha256, window.prepared_stream_sha256)
        self.assertNotIn(
            datamosh.DATAMOSH_MODE_SCATTER,
            renderer.ZONE_ASSIGNMENT_EFFECT_ORDER,
        )

    def test_mode_local_recovery_and_protected_intervals(self) -> None:
        for label, operation, handler, windows in (
            (
                "skrrt",
                self.full_operation,
                datamosh._transform_skrrt_operation,
                self.full_operation.prepared_windows,
            ),
            (
                "scatter",
                self.scatter_operation,
                datamosh._transform_scatter_operation,
                self.scatter_operation.prepared_scatter_windows,
            ),
        ):
            with self.subTest(label=label):
                transformed = handler(self.controlled_data, operation)
                output_vops = datamosh.vop_units(
                    datamosh.parse_mpeg4_units(transformed.data)
                )
                for window in windows:
                    self.assertEqual(
                        output_vops[window.recovery_frame].data,
                        self.controlled_vops[window.recovery_frame].data,
                    )

        overflow = datamosh._transform_overflow_operation(
            self.controlled_data, codec_operation("overflow")
        )
        overflow_vops = datamosh.vop_units(datamosh.parse_mpeg4_units(overflow.data))
        recoveries = {
            int(event.recovery_frame)
            for event in overflow.events
            if event.recovery_frame is not None
            and int(event.recovery_frame) < len(self.controlled_vops)
        }
        self.assertTrue(recoveries)
        for recovery in recoveries:
            self.assertEqual(
                overflow_vops[recovery].data,
                self.controlled_vops[recovery].data,
            )

        activity_protected = ((14, 18),)
        protected_overflow = datamosh._transform_overflow_operation(
            self.controlled_data,
            codec_operation("overflow", protected=activity_protected),
        )
        self.assertEqual(protected_overflow.events, ())
        self.assertEqual(
            datamosh._plan_skrrt_windows(
                codec_operation("skrrt", protected=activity_protected),
                self.controlled_vops,
            ),
            (),
        )
        self.assertEqual(
            datamosh._plan_scatter_windows(
                codec_operation("scatter", protected=activity_protected),
                self.controlled_vops,
            ),
            (),
        )

        transition_protected = ((39, 42),)
        protected_flows = datamosh._transform_bleed_operation(
            self.controlled_data,
            codec_operation("bleed", protected=transition_protected),
        )
        self.assertEqual(protected_flows.events, ())
        protected_general = datamosh._transform_general_operation(
            self.controlled_data,
            codec_operation("datamoshing", protected=transition_protected),
        )
        for event in protected_general.events:
            self.assertFalse(39 <= event.source_p_frame < 42)
        self.assertTrue(event_targets(protected_general.events).isdisjoint(range(39, 42)))
        self.assertEqual(sha256_path(self.source), self.source_sha256)


if __name__ == "__main__":
    unittest.main()
