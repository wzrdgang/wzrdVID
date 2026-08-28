"""Direct contracts for the stdlib-only numeric timeline boundary."""

from __future__ import annotations

import unittest

import timeline_math


class TimelineMathContractTests(unittest.TestCase):
    def test_half_open_interval_intersections_cover_all_overlap_shapes(self) -> None:
        self.assertIsNone(timeline_math.intersect_interval((0.0, 1.0), (2.0, 3.0)))
        self.assertIsNone(timeline_math.intersect_interval((0.0, 1.0), (1.0, 2.0)))
        self.assertEqual(
            timeline_math.intersect_interval((-1.0, 2.0), (0.0, 5.0)),
            (0.0, 2.0),
        )
        self.assertEqual(
            timeline_math.intersect_interval((3.0, 7.0), (0.0, 5.0)),
            (3.0, 5.0),
        )
        self.assertEqual(
            timeline_math.intersect_interval((1.0, 2.0), (0.0, 5.0)),
            (1.0, 2.0),
        )

    def test_preview_rebase_clips_and_uses_a_local_zero_start(self) -> None:
        self.assertEqual(
            timeline_math.rebase_intervals(
                ((0.0, 3.0), (4.0, 7.0), (8.0, 10.0), (10.0, 12.0)),
                2.0,
                10.0,
            ),
            [(0.0, 1.0), (2.0, 5.0), (6.0, 8.0)],
        )
        self.assertEqual(
            timeline_math.rebase_interval((0.0, 2.0), 0.0, 2.0),
            (0.0, 2.0),
        )

    def test_full_and_preview_window_durations_preserve_canonical_bounds(self) -> None:
        self.assertEqual(timeline_math.render_window_duration(10.0, 0.0, None), 10.0)
        self.assertEqual(timeline_math.render_window_duration(10.0, 0.0, 4.0), 4.0)
        self.assertEqual(timeline_math.render_window_duration(10.0, 8.0, 5.0), 2.0)
        with self.assertRaisesRegex(
            ValueError,
            "Preview start is outside the planned output timeline",
        ):
            timeline_math.render_window_duration(10.0, 10.0, 1.0)

    def test_absolute_and_local_time_are_inverse_window_mappings(self) -> None:
        self.assertEqual(timeline_math.absolute_time(1.25, 8.5), 9.75)
        self.assertEqual(timeline_math.local_time(9.75, 8.5), 1.25)
        self.assertEqual(timeline_math.absolute_time(2.0, 0.0), 2.0)

    def test_frame_quantization_handles_integer_and_fractional_boundaries(self) -> None:
        self.assertEqual(timeline_math.quantize_time_to_frame(1.0, 24), 24)
        self.assertEqual(timeline_math.quantize_time_to_frame(0.1, 24), 3)
        self.assertEqual(timeline_math.quantize_time_to_frame(1.0 / 24.0, 24), 1)
        self.assertEqual(timeline_math.absolute_output_frame(7, 1.25, 24), 37)
        self.assertEqual(timeline_math.absolute_output_frame(-40, 1.25, 24), 0)

    def test_frame_ranges_clip_and_remain_half_open(self) -> None:
        self.assertEqual(
            timeline_math.time_intervals_to_frame_intervals(
                ((-1.0, 0.25), (0.5, 99.0), (1.0, 1.0)),
                4,
                4,
            ),
            ((0, 1), (2, 4)),
        )
        intervals = ((2, 4), (4, 7))
        self.assertTrue(timeline_math.frames_fully_covered(2, 7, intervals))
        self.assertFalse(timeline_math.frames_fully_covered(1, 7, intervals))
        self.assertTrue(timeline_math.frame_in_intervals(6, intervals))
        self.assertFalse(timeline_math.frame_in_intervals(7, intervals))

    def test_merge_and_total_retain_existing_interval_tolerance(self) -> None:
        merged = timeline_math.merge_intervals(
            ((-2.0, 1.0), (1.0005, 2.0), (4.0, 9.0), (3.0, 3.0005)),
            5.0,
        )
        self.assertEqual(merged, [(0.0, 2.0), (4.0, 5.0)])
        self.assertEqual(timeline_math.interval_total(merged), 3.0)

    def test_middle_preview_does_not_invent_ending_loop_or_fade_overlap(self) -> None:
        ending = timeline_math.ending_tail_interval(20.0)
        loop = timeline_math.loop_tail_interval(20.0)
        assert ending is not None
        assert loop is not None
        self.assertIsNone(timeline_math.rebase_interval(ending, 8.0, 12.0))
        self.assertIsNone(timeline_math.rebase_interval(loop, 8.0, 12.0))
        self.assertEqual(timeline_math.preview_fade(20.0, 8.0, 4.0, 1.5), (0.0, None))

    def test_true_tail_intersections_preserve_partial_and_complete_bounds(self) -> None:
        ending = timeline_math.ending_tail_interval(20.0)
        assert ending is not None
        self.assertEqual(
            timeline_math.rebase_interval(ending, 18.0, 19.0),
            (0.5, 1.0),
        )
        self.assertEqual(
            timeline_math.rebase_interval(ending, 18.5, 20.0),
            (0.0, 1.5),
        )
        self.assertEqual(timeline_math.preview_fade(20.0, 19.0, 0.5, 1.5), (1.5, -0.5))
        self.assertEqual(timeline_math.preview_fade(20.0, 18.5, 1.5, 1.5), (1.5, 0.0))

    def test_canonical_visual_and_codec_loop_tail_math(self) -> None:
        self.assertAlmostEqual(timeline_math.loop_tail_duration(1.2), 0.4)
        self.assertEqual(timeline_math.loop_tail_duration(3.0), 0.75)
        self.assertEqual(timeline_math.loop_tail_interval(3.0), (2.25, 3.0))
        self.assertIsNone(timeline_math.loop_tail_interval(0.15))
        self.assertEqual(timeline_math.loop_protected_tail_start(240, 24), 222)
        self.assertEqual(timeline_math.loop_protected_tail_start(24, 24), 16)
        self.assertEqual(timeline_math.loop_protected_tail_start(0, 24), 0)
        self.assertEqual(
            timeline_math.preview_loop_protected_tail_start(10.0, 216, 24, 24),
            6,
        )

    def test_style_eligible_frame_conversion_is_local_and_clamped(self) -> None:
        self.assertEqual(timeline_math.style_eligible_start_frame(2.0, 0.5, 24, 100), 36)
        self.assertEqual(timeline_math.style_eligible_start_frame(0.1, 0.0, 24, 100), 3)
        self.assertEqual(timeline_math.style_eligible_start_frame(1.0, 2.0, 24, 100), 0)
        self.assertEqual(timeline_math.style_eligible_start_frame(20.0, 0.0, 24, 100), 100)


if __name__ == "__main__":
    unittest.main()
