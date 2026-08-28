"""Rights-safe generated fixtures for codec, Layer, and transport contracts."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

import datamosh
import renderer


CODEC_FPS = 8
CODEC_SIZE = (160, 90)
CODEC_FRAME_COUNT = 48
CODEC_SEED = 4_040
CODEC_TRANSITION_FRAME = 40

ORGANIC_FPS = 8
ORGANIC_SIZE = (480, 270)
ORGANIC_SHOT_FRAMES = 20
ORGANIC_SEED = 1_771_336_264
ORGANIC_MATERIALS = (
    "static",
    "normal_motion",
    "lateral_motion",
    "camera_motion",
    "textured_detail",
    "face_subject",
    "dark_motion",
    "bright_color",
)

MODE_POLICY = {
    datamosh.DATAMOSH_MODE_GENERAL: (datamosh.DATAMOSH_SEED_SALT, 10),
    datamosh.DATAMOSH_MODE_OVERFLOW: (datamosh.OVERFLOW_SEED_SALT, 20),
    datamosh.DATAMOSH_MODE_SKRRT: (datamosh.SKRRT_SEED_SALT, 30),
    datamosh.DATAMOSH_MODE_SCATTER: (datamosh.SCATTER_SEED_SALT, 40),
    datamosh.DATAMOSH_MODE_BLEED: (datamosh.BLEED_SEED_SALT, 50),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(args: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def probe(path: Path) -> dict[str, object]:
    completed = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(completed.stdout)


def encode_rgb_frames(
    frames: list[np.ndarray],
    destination: Path,
    *,
    fps: int,
    crf: int = 14,
) -> None:
    """Encode deterministic runtime RGB arrays without retaining a media fixture."""
    height, width = frames[0].shape[:2]
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{width}x{height}",
            "-r",
            str(fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            str(crf),
            "-g",
            str(fps),
            "-sc_threshold",
            "0",
            "-pix_fmt",
            "yuv420p",
            str(destination),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert process.stdin is not None
    for frame in frames:
        process.stdin.write(np.ascontiguousarray(frame).tobytes())
    process.stdin.close()
    stderr = process.stderr.read() if process.stderr is not None else b""
    if process.stderr is not None:
        process.stderr.close()
    if process.wait() != 0:
        raise RuntimeError(f"fixture encode failed: {stderr.decode(errors='replace')}")


def codec_frame(frame_index: int) -> np.ndarray:
    width, height = CODEC_SIZE
    y, x = np.mgrid[0:height, 0:width]
    red = (x * 7 + y * 3 + frame_index * 13) % 256
    green = (x * 2 + y * 11 + frame_index * 17) % 256
    blue = ((x ^ y) * 5 + frame_index * 19) % 256
    frame = np.stack((red, green, blue), axis=2).astype(np.uint8)
    cv2.rectangle(
        frame,
        ((frame_index * 7) % width, 17),
        (min(width - 1, (frame_index * 7) % width + 38), 68),
        (244, 31, 197),
        -1,
    )
    cv2.circle(
        frame,
        ((29 + frame_index * 9) % width, 45),
        13,
        (23, 231, 246),
        -1,
    )
    return np.ascontiguousarray(frame)


def codec_activity() -> tuple[datamosh.DatamoshActivity, ...]:
    regions = (
        datamosh.DatamoshSpatialRegion(0.08, 0.15, 0.27, 0.38, 0.96),
        datamosh.DatamoshSpatialRegion(0.58, 0.10, 0.30, 0.33, 0.89),
        datamosh.DatamoshSpatialRegion(0.31, 0.55, 0.35, 0.31, 0.82),
        datamosh.DatamoshSpatialRegion(0.02, 0.64, 0.24, 0.29, 0.74),
        datamosh.DatamoshSpatialRegion(0.73, 0.57, 0.22, 0.34, 0.68),
    )
    return (
        datamosh.DatamoshActivity(
            frame=15,
            absolute_frame=15,
            motion_activity=0.94,
            motion_x=0.71,
            motion_y=-0.38,
            direction_confidence=0.91,
            texture_activity=0.86,
            edge_activity=0.81,
            spatial_regions=regions,
        ),
    )


def codec_transitions() -> tuple[datamosh.DatamoshTransition, ...]:
    return (
        datamosh.DatamoshTransition(
            frame=CODEC_TRANSITION_FRAME,
            absolute_frame=CODEC_TRANSITION_FRAME,
            from_kind="video",
            to_kind="video",
            visual_transition="Hard Cut",
        ),
    )


def codec_operation(
    mode: str,
    *,
    intensity: float = 2.0,
    seed: int = CODEC_SEED,
    protected: tuple[tuple[int, int], ...] = (),
    zone_box: tuple[int, int, int, int] | None = None,
) -> datamosh.DatamoshOperation:
    salt, order = MODE_POLICY[mode]
    return datamosh.DatamoshOperation(
        mode=mode,
        enabled=True,
        intensity=intensity,
        seed=seed,
        salt=salt,
        order=order,
        start_frame=0,
        end_frame=CODEC_FRAME_COUNT,
        absolute_frame_offset=0,
        transitions=codec_transitions(),
        activity=(
            codec_activity()
            if mode
            in {
                datamosh.DATAMOSH_MODE_OVERFLOW,
                datamosh.DATAMOSH_MODE_SKRRT,
                datamosh.DATAMOSH_MODE_SCATTER,
            }
            else ()
        ),
        protected_intervals=protected,
        parameters=(
            ("fps", CODEC_FPS),
            ("width", CODEC_SIZE[0]),
            ("height", CODEC_SIZE[1]),
        ),
        zone_box=zone_box,
    )


def build_controlled_codec_fixture(root: Path) -> tuple[Path, Path, bytes]:
    source = root / "codec-source.mp4"
    controlled = root / "controlled.m4v"
    encode_rgb_frames(
        [codec_frame(index) for index in range(CODEC_FRAME_COUNT)],
        source,
        fps=CODEC_FPS,
    )
    datamosh._encode_prediction_stream(
        source,
        controlled,
        fps=CODEC_FPS,
        frame_count=CODEC_FRAME_COUNT,
        gop_size=CODEC_FPS,
        anchor_frame=0,
        transition_frames=(CODEC_TRANSITION_FRAME,),
        protected_tail_start=None,
        log=None,
    )
    return source, controlled, controlled.read_bytes()


def organic_material_frame(kind: str, local: int) -> np.ndarray:
    """Reproduce the accepted canonical spILL! material fixture."""
    width, height = ORGANIC_SIZE
    yy, xx = np.mgrid[0:height, 0:width]
    checker = (((xx // 16) + (yy // 16)) % 2).astype(np.uint8)
    base = np.empty((height, width, 3), dtype=np.uint8)
    base[:, :, 0] = 22 + checker * 38
    base[:, :, 1] = 34 + checker * 46
    base[:, :, 2] = 50 + checker * 30
    if kind == "static":
        frame = base
    elif kind == "normal_motion":
        frame = np.roll(base, local * 3, axis=1)
        cv2.circle(frame, (70 + local * 8, 130), 28, (230, 85, 175), -1)
    elif kind == "lateral_motion":
        frame = np.roll(base, local * 13, axis=1)
        start = (local * 23) % width
        cv2.rectangle(frame, (start, 65), (start + 90, 205), (38, 224, 240), -1)
    elif kind == "camera_motion":
        matrix = cv2.getRotationMatrix2D(
            (width / 2, height / 2), local * 2.8, 1.0 + local * 0.008
        )
        frame = cv2.warpAffine(
            base, matrix, (width, height), borderMode=cv2.BORDER_WRAP
        )
    elif kind == "textured_detail":
        noise = ((xx * 17 + yy * 31 + local * 19) % 255).astype(np.uint8)
        frame = np.stack(
            (noise, np.roll(noise, 9, axis=1), np.roll(noise, 13, axis=0)),
            axis=2,
        )
    elif kind == "face_subject":
        frame = np.full((height, width, 3), (58, 38, 76), dtype=np.uint8)
        center = (width // 2 + int(18 * math.sin(local / 3)), 112)
        cv2.circle(frame, center, 66, (202, 164, 128), -1)
        cv2.circle(frame, (center[0] - 23, center[1] - 12), 7, (20, 24, 32), -1)
        cv2.circle(frame, (center[0] + 23, center[1] - 12), 7, (20, 24, 32), -1)
        cv2.ellipse(
            frame,
            (center[0], center[1] + 22),
            (26, 12),
            0,
            0,
            180,
            (90, 28, 54),
            4,
        )
        cv2.rectangle(
            frame,
            (center[0] - 70, 178),
            (center[0] + 70, 269),
            (34, 126, 188),
            -1,
        )
    elif kind == "dark_motion":
        frame = np.full((height, width, 3), (5, 7, 12), dtype=np.uint8)
        cv2.line(
            frame,
            (0, (local * 11) % height),
            (width - 1, (local * 11 + 55) % height),
            (38, 60, 92),
            7,
        )
    elif kind == "bright_color":
        frame = np.full((height, width, 3), (218, 202, 112), dtype=np.uint8)
        cv2.circle(frame, ((80 + local * 17) % width, 92), 54, (205, 82, 158), -1)
        cv2.rectangle(frame, (170, 135), (440, 235), (62, 158, 196), -1)
    else:
        raise ValueError(kind)
    cv2.putText(
        frame,
        kind.upper(),
        (12, height - 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        (248, 248, 248),
        2,
    )
    return cv2.cvtColor(np.ascontiguousarray(frame), cv2.COLOR_BGR2RGB)


def decode_activity(
    source: Path,
    *,
    expected_frames: int,
) -> tuple[datamosh.DatamoshActivity, ...]:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError("could not decode activity source")
    samples: list[datamosh.DatamoshActivity] = []
    previous_luma: np.ndarray | None = None
    try:
        for frame in range(expected_frames):
            ok, bgr = capture.read()
            if not ok:
                raise RuntimeError(f"activity source ended at frame {frame}")
            reduced = cv2.resize(bgr, (320, 180), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(reduced, cv2.COLOR_BGR2RGB)
            analysis = renderer._FrameMaterialAnalysis(
                rgb=rgb, previous_luma=previous_luma
            )
            motion_x, motion_y, confidence = analysis.motion_direction()
            regions = analysis.scatter_regions()
            samples.append(
                datamosh.DatamoshActivity(
                    frame=frame,
                    absolute_frame=frame,
                    motion_activity=analysis.motion_activity,
                    motion_x=motion_x,
                    motion_y=motion_y,
                    direction_confidence=confidence,
                    texture_activity=analysis.texture_activity if regions else 0.0,
                    edge_activity=analysis.edge_activity if regions else 0.0,
                    spatial_regions=regions,
                )
            )
            previous_luma = analysis.luma.copy()
    finally:
        capture.release()
    return tuple(samples)


def build_organic_fixture(
    root: Path,
) -> tuple[Path, bytes, tuple[datamosh.DatamoshActivity, ...]]:
    frames = [
        organic_material_frame(kind, local)
        for kind in ORGANIC_MATERIALS
        for local in range(ORGANIC_SHOT_FRAMES)
    ]
    source = root / "organic-source.mp4"
    controlled = root / "organic-controlled.m4v"
    encode_rgb_frames(frames, source, fps=ORGANIC_FPS, crf=23)
    transitions = organic_transitions()
    datamosh._encode_prediction_stream(
        source,
        controlled,
        fps=ORGANIC_FPS,
        frame_count=len(frames),
        gop_size=ORGANIC_FPS,
        anchor_frame=0,
        transition_frames=tuple(target.frame for target in transitions),
        protected_tail_start=None,
        log=None,
    )
    return source, controlled.read_bytes(), decode_activity(
        source, expected_frames=len(frames)
    )


def organic_transitions() -> tuple[datamosh.DatamoshTransition, ...]:
    return tuple(
        datamosh.DatamoshTransition(
            frame=index * ORGANIC_SHOT_FRAMES,
            absolute_frame=index * ORGANIC_SHOT_FRAMES,
            from_kind="video",
            to_kind="video",
            visual_transition="Hard Cut",
        )
        for index in range(1, len(ORGANIC_MATERIALS))
    )


def organic_overflow_operation(
    activity: tuple[datamosh.DatamoshActivity, ...],
    intensity: float,
) -> datamosh.DatamoshOperation:
    return datamosh.DatamoshOperation(
        mode=datamosh.DATAMOSH_MODE_OVERFLOW,
        enabled=True,
        intensity=intensity,
        seed=ORGANIC_SEED,
        salt=datamosh.OVERFLOW_SEED_SALT,
        order=20,
        start_frame=0,
        end_frame=len(activity),
        absolute_frame_offset=0,
        transitions=organic_transitions(),
        activity=activity,
        parameters=(
            ("fps", ORGANIC_FPS),
            ("width", ORGANIC_SIZE[0]),
            ("height", ORGANIC_SIZE[1]),
        ),
    )


def event_targets(events: tuple[datamosh.DatamoshEvent, ...]) -> set[int]:
    targets: set[int] = set()
    for event in events:
        if event.repeated_at_frames:
            targets.update(int(frame) for frame in event.repeated_at_frames)
        elif "I_RESET_SUPPRESSED" in event.operation:
            targets.add(int(event.frame))
    return targets


def synthetic_mpeg4_stream(coding_types: tuple[int, ...]) -> bytes:
    prefix = b"\x00\x00\x01\xb0\x12\x34"
    return prefix + b"".join(
        b"\x00\x00\x01\xb6" + bytes(((coding_type & 3) << 6, index + 1, 0xA5))
        for index, coding_type in enumerate(coding_types)
    )
