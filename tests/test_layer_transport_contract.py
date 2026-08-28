"""Tracked Layer ordering plus controlled encode/safe-transcode contracts."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import datamosh

from tests.fixtures.codec_helpers import (
    CODEC_FPS,
    CODEC_FRAME_COUNT,
    build_controlled_codec_fixture,
    codec_operation,
    probe,
    sha256_path,
)


def _payloads(data: bytes) -> tuple[bytes, ...]:
    return tuple(
        unit.data
        for unit in datamosh.vop_units(datamosh.parse_mpeg4_units(data))
    )


def _frozen_signature(operation: datamosh.DatamoshOperation) -> tuple[object, ...]:
    return (
        operation.mode,
        operation.planned_events,
        tuple(
            (frame, hashlib.sha256(payload).hexdigest())
            for frame, payload in operation.planned_source_vops
        ),
        operation.planning_source_sha256,
        tuple(
            (window.reverse_stream_sha256, window.prediction_vops)
            for window in operation.prepared_windows
        ),
        tuple(
            (window.prepared_stream_sha256, window.prediction_vops)
            for window in operation.prepared_scatter_windows
        ),
    )


def _ordered_stage_trace(
    controlled_data: bytes,
    operations: tuple[datamosh.DatamoshOperation, ...],
) -> tuple[bytes, dict[str, set[int]], dict[str, tuple[bytes, ...]]]:
    current = controlled_data
    changed_by_mode: dict[str, set[int]] = {}
    payload_after_mode: dict[str, tuple[bytes, ...]] = {}
    for operation in sorted(operations, key=lambda item: (item.order, item.mode)):
        before = _payloads(current)
        transformed = datamosh._OPERATION_HANDLERS[operation.mode](current, operation)
        current = transformed.data
        after = _payloads(current)
        changed_by_mode[operation.mode] = {
            frame
            for frame, (left, right) in enumerate(zip(before, after))
            if left != right
        }
        payload_after_mode[operation.mode] = after
    return current, changed_by_mode, payload_after_mode


class LayerTransportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="wzrdvid-layer-contract-")
        cls.root = Path(cls._temporary.name)
        cls.source, cls.controlled_path, cls.controlled_data = (
            build_controlled_codec_fixture(cls.root)
        )
        cls.source_sha256 = sha256_path(cls.source)
        cls.controlled_vops = datamosh.vop_units(
            datamosh.parse_mpeg4_units(cls.controlled_data)
        )

        base_skrrt = codec_operation("skrrt")
        prepared_skrrt, _ = datamosh._prepare_skrrt_operations(
            cls.controlled_path,
            cls.root / "layer-skrrt",
            cls.controlled_vops,
            (base_skrrt,),
            fps=CODEC_FPS,
            log=None,
        )
        base_scatter = codec_operation("scatter")
        prepared_scatter, _ = datamosh._prepare_scatter_operations(
            cls.controlled_path,
            cls.root / "layer-scatter",
            cls.controlled_vops,
            (base_scatter,),
            fps=CODEC_FPS,
            log=None,
        )
        base_operations = (
            codec_operation("datamoshing"),
            codec_operation("overflow"),
            prepared_skrrt[0],
            prepared_scatter[0],
            codec_operation("bleed"),
        )
        cls.historical = datamosh._prepare_layer_operation_plans(
            cls.controlled_data, base_operations
        )
        reversed_modes = tuple(reversed(datamosh.DATAMOSH_MODE_ORDER))
        reverse_order = {
            mode: (index + 1) * 10 for index, mode in enumerate(reversed_modes)
        }
        cls.alternate = tuple(
            replace(operation, order=reverse_order[operation.mode])
            for operation in cls.historical
        )

    @classmethod
    def tearDownClass(cls) -> None:
        root = cls.root
        cls._temporary.cleanup()
        if root.exists():
            raise AssertionError(f"Layer temporary directory leaked: {root}")

    def test_historical_and_alternate_layer_freeze_plans_and_auxiliary_bytes(self) -> None:
        historical = datamosh.transform_mpeg4_operations(
            self.controlled_data, self.historical
        )
        alternate = datamosh.transform_mpeg4_operations(
            self.controlled_data, self.alternate
        )
        self.assertNotEqual(historical.data, alternate.data)
        self.assertEqual(historical.original_vop_count, historical.mutated_vop_count)
        self.assertEqual(alternate.original_vop_count, alternate.mutated_vop_count)
        self.assertEqual(
            historical.mutated_counts["B"] + historical.mutated_counts["S"], 0
        )
        self.assertEqual(
            alternate.mutated_counts["B"] + alternate.mutated_counts["S"], 0
        )

        historical_by_mode = {item.mode: item for item in self.historical}
        alternate_by_mode = {item.mode: item for item in self.alternate}
        self.assertEqual(set(historical_by_mode), set(datamosh.DATAMOSH_MODE_ORDER))
        for mode in datamosh.DATAMOSH_MODE_ORDER:
            self.assertEqual(
                _frozen_signature(historical_by_mode[mode]),
                _frozen_signature(alternate_by_mode[mode]),
            )

        repeated = datamosh.transform_mpeg4_operations(
            self.controlled_data, self.historical
        )
        self.assertEqual(repeated.data, historical.data)
        self.assertEqual(repeated.events, historical.events)

    def test_layer_whole_vop_last_writer_wins(self) -> None:
        historical_data, historical_changes, historical_payloads = _ordered_stage_trace(
            self.controlled_data, self.historical
        )
        alternate_data, alternate_changes, alternate_payloads = _ordered_stage_trace(
            self.controlled_data, self.alternate
        )
        self.assertEqual(
            historical_data,
            datamosh.transform_mpeg4_operations(
                self.controlled_data, self.historical
            ).data,
        )
        self.assertEqual(
            alternate_data,
            datamosh.transform_mpeg4_operations(
                self.controlled_data, self.alternate
            ).data,
        )

        def verify_last_writer(
            operations: tuple[datamosh.DatamoshOperation, ...],
            final_data: bytes,
            changes: dict[str, set[int]],
            payloads: dict[str, tuple[bytes, ...]],
        ) -> set[int]:
            ordered_modes = [
                item.mode for item in sorted(operations, key=lambda item: item.order)
            ]
            overlaps = {
                frame
                for frame in range(CODEC_FRAME_COUNT)
                if sum(frame in changes[mode] for mode in ordered_modes) >= 2
            }
            self.assertTrue(overlaps)
            final_payloads = _payloads(final_data)
            for frame in overlaps:
                last_writer = next(
                    mode
                    for mode in reversed(ordered_modes)
                    if frame in changes[mode]
                )
                self.assertEqual(
                    final_payloads[frame], payloads[last_writer][frame]
                )
            return overlaps

        historical_overlaps = verify_last_writer(
            self.historical,
            historical_data,
            historical_changes,
            historical_payloads,
        )
        alternate_overlaps = verify_last_writer(
            self.alternate,
            alternate_data,
            alternate_changes,
            alternate_payloads,
        )
        changed_final_frames = {
            frame
            for frame, (left, right) in enumerate(
                zip(_payloads(historical_data), _payloads(alternate_data))
            )
            if left != right
        }
        self.assertTrue(
            changed_final_frames & historical_overlaps & alternate_overlaps
        )

    def test_layer_rejects_duplicate_and_unknown_modes(self) -> None:
        duplicate = codec_operation("datamoshing")
        with self.assertRaisesRegex(datamosh.DatamoshError, "Duplicate"):
            datamosh.transform_mpeg4_operations(
                self.controlled_data, (duplicate, duplicate)
            )
        unknown = replace(codec_operation("datamoshing"), mode="unknown-mode")
        with self.assertRaisesRegex(datamosh.DatamoshError, "Unknown"):
            datamosh.transform_mpeg4_operations(self.controlled_data, (unknown,))

    def test_apply_uses_one_main_encode_and_one_safe_h264_transcode(self) -> None:
        temporary_path: Path | None = None
        original_encode = datamosh._encode_prediction_stream
        original_transcode = datamosh._transcode_manipulated_stream
        with tempfile.TemporaryDirectory(prefix="wzrdvid-apply-contract-") as temp_root:
            temporary_path = Path(temp_root)
            output = temporary_path / "safe-output.mp4"
            work = temporary_path / "work"
            with mock.patch.object(
                datamosh,
                "_encode_prediction_stream",
                wraps=original_encode,
            ) as encode_mock, mock.patch.object(
                datamosh,
                "_transcode_manipulated_stream",
                wraps=original_transcode,
            ) as transcode_mock:
                result = datamosh.apply_datamosh(
                    self.source,
                    output,
                    work,
                    fps=CODEC_FPS,
                    frame_count=CODEC_FRAME_COUNT,
                    effect_intensity=1.3,
                    weird_seed=4_040,
                    eligible_start_frame=0,
                    absolute_frame_offset=0,
                    loop_friendly=False,
                    video_crf=24,
                    video_bitrate=None,
                    transitions=codec_operation("datamoshing").transitions,
                    operations=(codec_operation("datamoshing", intensity=1.3),),
                    log=None,
                )
                self.assertTrue(result.applied)
                self.assertEqual(encode_mock.call_count, 1)
                self.assertEqual(transcode_mock.call_count, 1)
                media = probe(output)
                video = next(
                    stream
                    for stream in media["streams"]
                    if stream["codec_type"] == "video"
                )
                self.assertEqual(video["codec_name"], "h264")
                self.assertEqual(video["pix_fmt"], "yuv420p")
                self.assertEqual(int(video["nb_read_frames"]), CODEC_FRAME_COUNT)
                self.assertFalse(
                    any(
                        stream["codec_type"] == "audio"
                        for stream in media["streams"]
                    )
                )
                self.assertEqual(sha256_path(self.source), self.source_sha256)
        assert temporary_path is not None
        self.assertFalse(temporary_path.exists())


if __name__ == "__main__":
    unittest.main()
