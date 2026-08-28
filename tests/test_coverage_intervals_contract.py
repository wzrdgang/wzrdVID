from __future__ import annotations

import inspect
import random
import unittest

import coverage_intervals
import timeline_math


class CoverageIntervalsContractTests(unittest.TestCase):
    def _build(
        self,
        duration: float,
        *,
        include_manual: bool = False,
        manual_intervals: tuple[tuple[float, float], ...] = (),
        include_random: bool = False,
        random_percent: float = 0.0,
        random_seed: int | None = 101,
        random_min_length: float = 0.5,
        random_max_length: float = 2.0,
    ) -> tuple[tuple[float, float], ...]:
        return coverage_intervals.build_coverage_intervals(
            duration,
            include_manual=include_manual,
            manual_intervals=manual_intervals,
            include_random=include_random,
            random_percent=random_percent,
            random_seed=random_seed,
            random_min_length=random_min_length,
            random_max_length=random_max_length,
        )

    def test_public_boundary_is_caller_neutral(self) -> None:
        parameters = set(inspect.signature(coverage_intervals.build_coverage_intervals).parameters)
        self.assertEqual(
            parameters,
            {
                "duration",
                "include_manual",
                "manual_intervals",
                "include_random",
                "random_percent",
                "random_seed",
                "random_min_length",
                "random_max_length",
            },
        )
        self.assertFalse(any("style" in name or "ansi" in name for name in parameters))

    def test_disabled_coverage_and_nonpositive_duration_are_empty(self) -> None:
        self.assertEqual(self._build(20.0), ())
        self.assertEqual(
            self._build(
                0.0,
                include_manual=True,
                manual_intervals=((0.0, 1.0),),
                include_random=True,
                random_percent=100.0,
            ),
            (),
        )

    def test_manual_intervals_are_clamped_sorted_and_merged(self) -> None:
        self.assertEqual(
            self._build(
                10.0,
                include_manual=True,
                manual_intervals=((-2.0, 1.0), (1.0, 3.0), (8.0, 14.0), (7.0, 6.0), (2.5, 5.0)),
            ),
            ((0.0, 5.0), (8.0, 10.0)),
        )

    def test_random_zero_small_half_and_full_percent_contract(self) -> None:
        self.assertEqual(self._build(10.0, include_random=True, random_percent=0.0), ())
        self.assertEqual(
            self._build(10.0, include_random=True, random_percent=1.0),
            ((1.8501677075742986, 2.3501677075742986),),
        )
        self.assertEqual(
            self._build(10.0, include_random=True, random_percent=50.0),
            (
                (0.052426660166708, 0.6937816006160356),
                (1.231322913422981, 2.063867287712342),
                (5.10022955562117, 6.300937572916631),
                (6.838002915828618, 7.416692131333033),
                (8.018243573744979, 8.836808726282475),
                (8.887905028451376, 9.680036771752581),
            ),
        )
        self.assertEqual(
            self._build(10.0, include_random=True, random_percent=100.0),
            ((0.0, 10.0),),
        )

    def test_random_percent_is_clamped(self) -> None:
        self.assertEqual(self._build(10.0, include_random=True, random_percent=-20.0), ())
        self.assertEqual(
            self._build(10.0, include_random=True, random_percent=120.0),
            ((0.0, 10.0),),
        )

    def test_same_seed_repeats_and_changed_seed_changes_placement(self) -> None:
        seed_101 = self._build(10.0, include_random=True, random_percent=50.0)
        self.assertEqual(seed_101, self._build(10.0, include_random=True, random_percent=50.0))
        self.assertEqual(
            self._build(10.0, include_random=True, random_percent=50.0, random_seed=102),
            (
                (1.4552344482160096, 2.879182378830345),
                (3.658109254039334, 4.353254908709347),
                (5.07339148109274, 6.4851402202289465),
                (6.578737195301449, 7.928115850943499),
            ),
        )
        self.assertNotEqual(
            seed_101,
            self._build(10.0, include_random=True, random_percent=50.0, random_seed=102),
        )

    def test_independent_callers_share_the_same_numeric_kernel(self) -> None:
        inputs = {
            "include_manual": True,
            "manual_intervals": ((4.0, 7.0), (12.0, 13.0)),
            "include_random": True,
            "random_percent": 35.0,
            "random_seed": 101,
        }
        first_caller = self._build(20.0, **inputs)
        second_caller = self._build(20.0, **inputs)
        self.assertEqual(first_caller, second_caller)

    def test_random_planning_does_not_mutate_global_random_state(self) -> None:
        before = random.getstate()
        self._build(20.0, include_random=True, random_percent=35.0)
        self.assertEqual(random.getstate(), before)

    def test_combined_manual_and_random_preserves_additional_target_semantics(self) -> None:
        result = self._build(
            20.0,
            include_manual=True,
            manual_intervals=((4.0, 7.0), (12.0, 13.0)),
            include_random=True,
            random_percent=35.0,
        )
        self.assertEqual(
            result,
            (
                (0.02967013724615893, 0.6096679946381403),
                (0.913882004757183, 1.746426379046544),
                (4.0, 7.0),
                (8.501814776677532, 9.7834789090433),
                (12.0, 13.0),
                (13.586038144148525, 14.635810606303576),
                (15.292215074723606, 16.110780227261102),
                (16.1789822332156, 17.37969025051106),
                (18.992151707268043, 19.784283450569248),
            ),
        )
        self.assertEqual(timeline_math.interval_total(result), 10.555383739336325)

    def test_fixed_chunk_and_small_final_remainder_behavior(self) -> None:
        self.assertEqual(
            self._build(
                10.0,
                include_random=True,
                random_percent=30.0,
                random_min_length=0.75,
                random_max_length=0.75,
            ),
            (
                (1.3492009884817648, 2.0992009884817646),
                (5.426242927352961, 6.176242927352961),
                (8.120717325293755, 8.870717325293755),
                (8.928572740315278, 9.678572740315278),
            ),
        )
        partial = self._build(10.0, include_random=True, random_percent=13.0)
        self.assertEqual(
            partial,
            (
                (5.607744256104245, 6.175103973469949),
                (9.019495923144992, 9.675299519572302),
            ),
        )
        self.assertEqual(timeline_math.interval_total(partial), 1.2231633137930142)

    def test_tolerance_short_duration_and_unfillable_gap_edges(self) -> None:
        self.assertEqual(
            self._build(
                0.1,
                include_random=True,
                random_percent=50.0,
                random_min_length=0.5,
                random_max_length=3.0,
            ),
            (),
        )
        self.assertEqual(
            self._build(
                1.0,
                include_manual=True,
                manual_intervals=((0.0, 0.6),),
                include_random=True,
                random_percent=20.0,
                random_min_length=0.5,
                random_max_length=3.0,
            ),
            ((0.0, 0.6),),
        )
        self.assertEqual(
            self._build(
                10.0,
                include_manual=True,
                manual_intervals=((0.0, 10.0),),
                include_random=True,
                random_percent=50.0,
            ),
            ((0.0, 10.0),),
        )

    def test_inverted_random_length_range_keeps_existing_minimum_precedence(self) -> None:
        self.assertEqual(
            self._build(
                10.0,
                include_random=True,
                random_percent=20.0,
                random_min_length=2.0,
                random_max_length=0.5,
            ),
            ((7.722008856488889, 9.72200885648889),),
        )

    def test_preview_is_derived_by_rebasing_the_full_interval_map(self) -> None:
        full = self._build(
            20.0,
            include_manual=True,
            manual_intervals=((4.0, 7.0), (12.0, 13.0)),
            include_random=True,
            random_percent=35.0,
        )
        self.assertEqual(timeline_math.rebase_intervals(full, 5.0, 8.0), [(0.0, 2.0)])

    def test_duration_is_the_only_timeline_input(self) -> None:
        short = self._build(10.0, include_random=True, random_percent=35.0)
        assembled = self._build(20.0, include_random=True, random_percent=35.0)
        self.assertNotEqual(short, assembled)
        self.assertTrue(all(0.0 <= start < end <= 20.0 for start, end in assembled))


if __name__ == "__main__":
    unittest.main()
