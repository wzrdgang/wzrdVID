"""Tracked frame-pipe, PNG fallback, failure, audio, and cleanup contracts."""

from __future__ import annotations

import gc
import os
import tempfile
import unittest
import warnings
from dataclasses import replace
from pathlib import Path
from unittest import mock

import datamosh
import ffmpeg_utils
import numpy as np
import renderer

from tests.fixtures.codec_helpers import encode_rgb_frames, probe, run, sha256_path


class RenderTransportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="wzrdvid-render-transport-")
        cls.root = Path(cls._temporary.name)
        cls.source = cls.root / "source-with-aac.mp4"
        run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=160x90:rate=2:duration=1.5",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=880:sample_rate=48000:duration=1.5",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(cls.source),
            ]
        )
        cls.source_sha256 = sha256_path(cls.source)
        cls.random_red = cls.root / "random-red.mp4"
        cls.random_blue = cls.root / "random-blue.mp4"
        encode_rgb_frames(
            [np.full((90, 160, 3), (235, 24, 18), dtype=np.uint8) for _ in range(2)],
            cls.random_red,
            fps=2,
        )
        encode_rgb_frames(
            [np.full((90, 160, 3), (18, 28, 235), dtype=np.uint8) for _ in range(2)],
            cls.random_blue,
            fps=2,
        )
        cls.settings = renderer.RenderSettings(
            video_path=str(cls.source),
            output_path=str(cls.root / "placeholder.mp4"),
            audio_path=str(cls.source),
            video_start=0.0,
            video_end=1.0,
            audio_start=0.0,
            audio_end=1.0,
            preset_name="Glitch Hell",
            fps=2,
            width_chars=24,
            output_size=(160, 90),
            video_crf=28,
            audio_bitrate="96k",
            max_video_length=1.0,
            audio_mode=renderer.AUDIO_EXTERNAL,
            effects={"glitch": True, "scanlines": True, "rgb_split": True},
            effect_intensity=0.7,
            transition_mode="Hard Cut",
            ending_mode="Hard Cut",
            timeline_items=[
                renderer.TimelineItem(
                    path=str(cls.source),
                    kind="video",
                    duration=1.5,
                    trim_start=0.0,
                    trim_end=1.0,
                    has_audio=True,
                    include_audio=True,
                )
            ],
        )

    @classmethod
    def tearDownClass(cls) -> None:
        root = cls.root
        cls._temporary.cleanup()
        if root.exists():
            raise AssertionError(f"render-transport temporary directory leaked: {root}")

    def _render(
        self,
        name: str,
        settings: renderer.RenderSettings | None = None,
    ) -> tuple[Path, list[str]]:
        logs: list[str] = []
        output = self.root / f"{name}.mp4"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            result = Path(
                renderer.render_project(
                    replace(settings or self.settings, output_path=str(output)),
                    log=logs.append,
                )
            )
            gc.collect()
        return result, logs

    def assert_h264_aac(self, path: Path) -> None:
        media = probe(path)
        video = next(
            stream for stream in media["streams"] if stream["codec_type"] == "video"
        )
        audio = next(
            stream for stream in media["streams"] if stream["codec_type"] == "audio"
        )
        self.assertEqual(video["codec_name"], "h264")
        self.assertEqual(video["pix_fmt"], "yuv420p")
        self.assertEqual(audio["codec_name"], "aac")

    def test_default_forced_png_and_eligible_automatic_fallback_keep_aac(self) -> None:
        original_pipe = renderer._render_silent_video_with_pipe
        original_png = renderer._render_silent_video_with_png_frames
        transport_variables = {
            renderer.FRAME_PIPE_FORCE_PNG_ENV_VAR: "0",
            renderer.FRAME_PIPE_ENV_VAR: "0",
        }
        with mock.patch.dict(os.environ, transport_variables, clear=False):
            with mock.patch.object(
                renderer, "_render_silent_video_with_pipe", wraps=original_pipe
            ) as pipe_mock, mock.patch.object(
                renderer, "_render_silent_video_with_png_frames", wraps=original_png
            ) as png_mock:
                default_output, default_logs = self._render("default-pipe")
            self.assertEqual(pipe_mock.call_count, 1)
            self.assertEqual(png_mock.call_count, 0)
            self.assertTrue(
                any(
                    "enabled (default desktop transport)" in line
                    for line in default_logs
                )
            )
            self.assertFalse(any("Falling back to PNG" in line for line in default_logs))
            self.assert_h264_aac(default_output)

        with mock.patch.dict(
            os.environ,
            {renderer.FRAME_PIPE_FORCE_PNG_ENV_VAR: "1"},
            clear=False,
        ):
            with mock.patch.object(
                renderer, "_render_silent_video_with_pipe", wraps=original_pipe
            ) as pipe_mock, mock.patch.object(
                renderer, "_render_silent_video_with_png_frames", wraps=original_png
            ) as png_mock:
                forced_output, forced_logs = self._render("forced-png")
            self.assertEqual(pipe_mock.call_count, 0)
            self.assertEqual(png_mock.call_count, 1)
            self.assertTrue(
                any(
                    "forced legacy PNG" in line
                    and renderer.FRAME_PIPE_FORCE_PNG_ENV_VAR in line
                    for line in forced_logs
                )
            )
            self.assert_h264_aac(forced_output)

        def fail_pipe(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("synthetic pre-audio frame-pipe failure")

        with mock.patch.dict(os.environ, transport_variables, clear=False):
            with mock.patch.object(
                ffmpeg_utils, "encode_raw_rgb_frames_to_mp4", side_effect=fail_pipe
            ), mock.patch.object(
                renderer, "_render_silent_video_with_png_frames", wraps=original_png
            ) as png_mock:
                fallback_output, fallback_logs = self._render("automatic-fallback")
            self.assertEqual(png_mock.call_count, 1)
            self.assertTrue(
                any("synthetic pre-audio frame-pipe failure" in line for line in fallback_logs)
            )
            self.assertTrue(
                any("Falling back to PNG frame staging" in line for line in fallback_logs)
            )
            self.assertTrue(
                any("Muxing selected external audio" in line for line in fallback_logs)
            )
            self.assert_h264_aac(fallback_output)
        self.assertEqual(sha256_path(self.source), self.source_sha256)

    def test_preview_before_delayed_matched_audio_is_valid_silence_then_crossing_keeps_aac(self) -> None:
        delayed = replace(
            self.settings,
            audio_start=0.0,
            audio_end=0.4,
            audio_timeline_start=0.6,
            audio_timeline_end=1.0,
            match_timeline_to_audio=True,
            match_timeline_mode=renderer.MATCH_SPEED,
            ending_mode="Hard Cut",
        )
        before, before_logs = self._render(
            "preview-before-delayed-audio",
            replace(
                delayed,
                preview_duration=0.4,
                output_time_offset=0.0,
            ),
        )
        before_media = probe(before)
        self.assertFalse(
            any(stream["codec_type"] == "audio" for stream in before_media["streams"])
        )
        self.assertTrue(
            any("outside the configured external-audio placement" in line for line in before_logs)
        )

        crossing, _crossing_logs = self._render(
            "preview-crossing-delayed-audio",
            replace(
                delayed,
                preview_duration=0.5,
                output_time_offset=0.4,
            ),
        )
        crossing_media = probe(crossing)
        video = next(
            stream for stream in crossing_media["streams"] if stream["codec_type"] == "video"
        )
        audio = next(
            stream for stream in crossing_media["streams"] if stream["codec_type"] == "audio"
        )
        self.assertEqual(video["codec_name"], "h264")
        self.assertEqual(video["pix_fmt"], "yuv420p")
        self.assertEqual(audio["codec_name"], "aac")
        self.assertEqual(sha256_path(self.source), self.source_sha256)

    def test_random_preview_frames_follow_the_canonical_full_render_slice(self) -> None:
        def color_labels(path: Path) -> list[str]:
            decoded = run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(path),
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-",
                ]
            ).stdout
            frames = np.frombuffer(decoded, dtype=np.uint8).reshape((-1, 90, 160, 3))
            return [
                "red" if float(frame[:, :, 0].mean()) > float(frame[:, :, 2].mean()) else "blue"
                for frame in frames
            ]

        source_hashes = {
            self.random_red: sha256_path(self.random_red),
            self.random_blue: sha256_path(self.random_blue),
        }
        random_settings = replace(
            self.settings,
            video_path=str(self.random_red),
            video_start=0.0,
            video_end=2.0,
            audio_path=None,
            audio_mode=renderer.AUDIO_SILENT,
            max_video_length=2.0,
            random_clip_assembly=True,
            random_min_len=0.5,
            random_max_len=0.5,
            random_seed=31,
            style_begin_time=99.0,
            effects={},
            timeline_items=[
                renderer.TimelineItem(
                    path=str(self.random_red),
                    kind="video",
                    duration=1.0,
                    trim_start=0.0,
                    trim_end=1.0,
                ),
                renderer.TimelineItem(
                    path=str(self.random_blue),
                    kind="video",
                    duration=1.0,
                    trim_start=0.0,
                    trim_end=1.0,
                ),
            ],
        )
        full, _full_logs = self._render("random-full", random_settings)
        preview, _preview_logs = self._render(
            "random-preview",
            replace(
                random_settings,
                output_time_offset=0.5,
                preview_duration=1.0,
            ),
        )
        full_labels = color_labels(full)
        preview_labels = color_labels(preview)
        self.assertEqual(preview_labels, full_labels[1:3])
        self.assertEqual(len(preview_labels), 2)
        self.assertEqual(
            {path: sha256_path(path) for path in source_hashes},
            source_hashes,
        )

    def test_preview_codec_loop_uses_the_canonical_protected_tail(self) -> None:
        preview_settings = replace(
            self.settings,
            fps=8,
            output_time_offset=0.5,
            preview_duration=0.5,
            loop_friendly=True,
            effects={"datamoshing": True},
        )
        with mock.patch.object(
            datamosh,
            "apply_datamosh",
            wraps=datamosh.apply_datamosh,
        ) as codec_mock:
            output, _logs = self._render("preview-codec-loop", preview_settings)
        self.assertEqual(codec_mock.call_count, 1)
        self.assertEqual(codec_mock.call_args.kwargs["loop_protected_tail_start"], 1)
        self.assert_h264_aac(output)
        self.assertEqual(sha256_path(self.source), self.source_sha256)

    def test_datamosh_error_propagates_without_png_retry_and_cleans_temp(self) -> None:
        output = self.root / "datamosh-failure.mp4"
        logs: list[str] = []
        png_calls = 0
        created_roots: list[Path] = []
        original_png = renderer._render_silent_video_with_png_frames
        original_temporary_directory = renderer.tempfile.TemporaryDirectory

        class RecordingTemporaryDirectory:
            def __init__(inner_self, *args: object, **kwargs: object) -> None:
                inner_self.inner = original_temporary_directory(*args, **kwargs)

            def __enter__(inner_self) -> str:
                path = Path(inner_self.inner.__enter__())
                created_roots.append(path)
                return str(path)

            def __exit__(inner_self, *args: object) -> object:
                return inner_self.inner.__exit__(*args)

        def fail_codec(*_args: object, **_kwargs: object) -> None:
            raise datamosh.DatamoshError("synthetic codec preparation failure")

        def count_png(*args: object, **kwargs: object) -> object:
            nonlocal png_calls
            png_calls += 1
            return original_png(*args, **kwargs)

        failing = replace(
            self.settings,
            output_path=str(output),
            effects={"datamoshing": True},
        )
        with mock.patch.dict(
            os.environ,
            {renderer.FRAME_PIPE_FORCE_PNG_ENV_VAR: "0"},
            clear=False,
        ), mock.patch.object(
            datamosh, "apply_datamosh", side_effect=fail_codec
        ), mock.patch.object(
            renderer, "_render_silent_video_with_png_frames", side_effect=count_png
        ), mock.patch.object(
            renderer.tempfile,
            "TemporaryDirectory",
            RecordingTemporaryDirectory,
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                with self.assertRaisesRegex(
                    datamosh.DatamoshError, "synthetic codec preparation failure"
                ):
                    renderer.render_project(failing, log=logs.append)
                gc.collect()
        self.assertEqual(png_calls, 0)
        self.assertFalse(any("Falling back to PNG" in line for line in logs))
        self.assertFalse(output.exists())
        self.assertTrue(created_roots)
        self.assertTrue(all(not path.exists() for path in created_roots))
        self.assertEqual(sha256_path(self.source), self.source_sha256)

    def test_zone_render_error_propagates_without_png_retry_and_cleans_temp(self) -> None:
        output = self.root / "zone-render-failure.mp4"
        logs: list[str] = []
        png_calls = 0
        created_roots: list[Path] = []
        original_png = renderer._render_silent_video_with_png_frames
        original_temporary_directory = renderer.tempfile.TemporaryDirectory

        class RecordingTemporaryDirectory:
            def __init__(inner_self, *args: object, **kwargs: object) -> None:
                inner_self.inner = original_temporary_directory(*args, **kwargs)

            def __enter__(inner_self) -> str:
                path = Path(inner_self.inner.__enter__())
                created_roots.append(path)
                return str(path)

            def __exit__(inner_self, *args: object) -> object:
                return inner_self.inner.__exit__(*args)

        def fail_zone_motion(*_args: object, **_kwargs: object) -> None:
            raise MemoryError("synthetic Zone geometry allocation failure")

        def count_png(*args: object, **kwargs: object) -> object:
            nonlocal png_calls
            png_calls += 1
            return original_png(*args, **kwargs)

        zone = renderer.ZoneDefinition(
            "zone-a", "Tracked", 0.2, 0.2, 0.5, 0.5, "drift", 25.0, 2
        )
        failing = replace(
            self.settings,
            output_path=str(output),
            effects={"pixel_sorting": True},
            zones=(zone,),
            effect_zone_assignments={"pixel_sorting": zone.id},
        )
        with mock.patch.dict(
            os.environ,
            {renderer.FRAME_PIPE_FORCE_PNG_ENV_VAR: "0"},
            clear=False,
        ), mock.patch.object(
            renderer.zone_motion, "resolve_zone_motion", side_effect=fail_zone_motion
        ), mock.patch.object(
            renderer, "_render_silent_video_with_png_frames", side_effect=count_png
        ), mock.patch.object(
            renderer.tempfile,
            "TemporaryDirectory",
            RecordingTemporaryDirectory,
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                with self.assertRaisesRegex(
                    renderer.RenderError, "synthetic Zone geometry allocation failure"
                ):
                    renderer.render_project(failing, log=logs.append)
                gc.collect()
        self.assertEqual(png_calls, 0)
        self.assertFalse(any("Falling back to PNG" in line for line in logs))
        self.assertFalse(output.exists())
        self.assertTrue(created_roots)
        self.assertTrue(all(not path.exists() for path in created_roots))
        self.assertEqual(sha256_path(self.source), self.source_sha256)


if __name__ == "__main__":
    unittest.main()
