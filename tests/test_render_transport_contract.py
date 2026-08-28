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
import renderer

from tests.fixtures.codec_helpers import probe, run, sha256_path


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

        def fail_zone(*_args: object, **_kwargs: object) -> None:
            raise renderer.RenderError("synthetic Zone contract failure")

        def count_png(*args: object, **kwargs: object) -> object:
            nonlocal png_calls
            png_calls += 1
            return original_png(*args, **kwargs)

        zone = renderer.ZoneDefinition("zone-a", "Tracked", 0.2, 0.2, 0.5, 0.5)
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
            renderer, "_apply_phase2_zone_effect", side_effect=fail_zone
        ), mock.patch.object(
            renderer, "_render_silent_video_with_png_frames", side_effect=count_png
        ), mock.patch.object(
            renderer.tempfile,
            "TemporaryDirectory",
            RecordingTemporaryDirectory,
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                with self.assertRaisesRegex(renderer.RenderError, "synthetic Zone"):
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
