#!/usr/bin/env python3
"""Build and run the WZRD.VID Lite iOS simulator smoke harness."""

from __future__ import annotations

from array import array
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPLE_ROOT = ROOT / "apple-lite"
PROJECT = APPLE_ROOT / "WZRDVIDLite.xcodeproj"
DERIVED_DATA = APPLE_ROOT / "DerivedData"
APP_PATH = DERIVED_DATA / "Build/Products/Debug-iphonesimulator/WZRDVIDLite.app"
BUNDLE_ID = "com.samhowell.wzrdvid.lite"
AUDIO_SAMPLE_RATE = 8_000
AUDIO_ARTIFACT_ROOT = Path("/tmp/wzrdvid-phase5-lite-source-audio")


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    check: bool = True,
    echo_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"+ {' '.join(command)}")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if completed.stdout and echo_output:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, command, output=completed.stdout)
    return completed


def pick_device() -> tuple[str, str, str]:
    requested = os.environ.get("WZRDVID_LITE_DEVICE")
    completed = run(["xcrun", "simctl", "list", "-j", "devices", "available"], echo_output=False)
    data = json.loads(completed.stdout)
    devices = [device for group in data.get("devices", {}).values() for device in group if device.get("isAvailable")]
    if requested:
        for device in devices:
            if device.get("name") == requested or device.get("udid") == requested:
                return device["udid"], device["name"], device.get("state", "")
        raise SystemExit(f"Requested simulator not found: {requested}")

    preferred = ["iPhone 17", "iPhone 17 Pro", "iPhone 16e"]
    for name in preferred:
        for device in devices:
            if device.get("name") == name:
                return device["udid"], device["name"], device.get("state", "")
    for device in devices:
        if "iPhone" in device.get("name", ""):
            return device["udid"], device["name"], device.get("state", "")
    raise SystemExit("No available iPhone simulator was found.")


def parse_smoke_result(output: str) -> dict[str, object]:
    match = re.search(r"WZRDVID_LITE_SMOKE_RESULT=(\{.*\})", output)
    if not match:
        raise SystemExit("Simulator smoke did not print WZRDVID_LITE_SMOKE_RESULT.")
    return json.loads(match.group(1))


def exported_file_paths(device_id: str, result: dict[str, object]) -> dict[str, Path]:
    container = run(
        ["xcrun", "simctl", "get_app_container", device_id, BUNDLE_ID, "data"],
        echo_output=False,
    )
    export_root = Path(container.stdout.strip()) / "tmp/wzrdvid-lite-export"
    paths: dict[str, Path] = {}
    for mode in result.get("modeResults") or []:
        if not isinstance(mode, dict) or not mode.get("nativeExportSent"):
            continue
        diagnostics = mode.get("diagnostics") or {}
        filename = diagnostics.get("filename") if isinstance(diagnostics, dict) else None
        if filename:
            paths[str(mode.get("name") or filename)] = export_root / str(filename)
    return paths


def ffprobe_summary(path: Path) -> dict[str, object]:
    completed = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ],
        echo_output=False,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams") or []
    return {
        "duration": float((payload.get("format") or {}).get("duration") or 0),
        "videoTracks": sum(stream.get("codec_type") == "video" for stream in streams),
        "audioTracks": sum(stream.get("codec_type") == "audio" for stream in streams),
        "streams": streams,
    }


def decode_audio_pcm(path: Path) -> array:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(AUDIO_SAMPLE_RATE),
            "-f",
            "f32le",
            "-",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    samples = array("f")
    samples.frombytes(completed.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def radix2_fft(values: list[float]) -> list[complex]:
    size = len(values)
    spectrum = [complex(value, 0) for value in values]
    target = 0
    for index in range(1, size):
        bit = size >> 1
        while target & bit:
            target ^= bit
            bit >>= 1
        target ^= bit
        if index < target:
            spectrum[index], spectrum[target] = spectrum[target], spectrum[index]
    length = 2
    while length <= size:
        step = complex(math.cos(-2 * math.pi / length), math.sin(-2 * math.pi / length))
        for offset in range(0, size, length):
            factor = complex(1, 0)
            half = length // 2
            for index in range(offset, offset + half):
                even = spectrum[index]
                odd = spectrum[index + half] * factor
                spectrum[index] = even + odd
                spectrum[index + half] = even - odd
                factor *= step
        length <<= 1
    return spectrum


def fft_window(samples: array, start: float, end: float) -> dict[str, object]:
    first = max(0, round(start * AUDIO_SAMPLE_RATE))
    last = min(len(samples), round(end * AUDIO_SAMPLE_RATE))
    window_samples = list(samples[first:last])
    if len(window_samples) < 256:
        raise ValueError(f"FFT window is too short: {start:.3f}-{end:.3f}s")
    fft_size = min(4096, 1 << (len(window_samples).bit_length() - 1))
    trim = (len(window_samples) - fft_size) // 2
    fft_samples = window_samples[trim:trim + fft_size]
    window = [0.5 - 0.5 * math.cos(2 * math.pi * index / (fft_size - 1)) for index in range(fft_size)]
    spectrum = radix2_fft([sample * weight for sample, weight in zip(fft_samples, window)])
    scale = max(sum(window), 1.0)

    def amplitude(frequency: float) -> float:
        center = round(frequency * fft_size / AUDIO_SAMPLE_RATE)
        low = max(0, center - 2)
        high = min(len(spectrum) // 2, center + 3)
        return float(2 * max(abs(value) for value in spectrum[low:high]) / scale)

    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "rms": math.sqrt(sum(sample * sample for sample in window_samples) / len(window_samples)),
        "fft": {str(frequency): amplitude(frequency) for frequency in (220, 440, 880)},
    }


def analyze_exported_audio(device_id: str, result: dict[str, object]) -> dict[str, object]:
    paths = exported_file_paths(device_id, result)
    needed = {"source-on-no-add", "source-off-add", "source-on-add", "source-on-no-add-repeat"}
    missing = sorted(needed - paths.keys())
    if missing:
        raise RuntimeError(f"Native smoke exports missing for modes: {', '.join(missing)}")

    AUDIO_ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"sampleRate": AUDIO_SAMPLE_RATE, "exports": {}, "checks": {}}
    pcm: dict[str, array] = {}
    for mode, source_path in paths.items():
        if not source_path.is_file():
            raise RuntimeError(f"Native export was not written: {source_path}")
        artifact_path = AUDIO_ARTIFACT_ROOT / f"{mode}{source_path.suffix}"
        shutil.copy2(source_path, artifact_path)
        probe = ffprobe_summary(artifact_path)
        report["exports"][mode] = {"path": str(artifact_path), "probe": probe}
        if mode in needed:
            pcm[mode] = decode_audio_pcm(artifact_path)
        report["checks"][f"{mode}:one-audio-track"] = probe["audioTracks"] == 1
        report["checks"][f"{mode}:one-video-track"] = probe["videoTracks"] == 1

    source_only = fft_window(pcm["source-on-no-add"], 0.30, 1.05)
    added_only = fft_window(pcm["source-off-add"], 0.20, 0.80)
    report["exports"]["source-on-no-add"]["representativeWindow"] = source_only
    report["exports"]["source-off-add"]["representativeWindow"] = added_only
    report["checks"]["source-only:440-present"] = source_only["fft"]["440"] > 0.04
    report["checks"]["source-only:220-absent"] = source_only["fft"]["220"] < 0.025
    report["checks"]["source-only:880-absent"] = source_only["fft"]["880"] < 0.025
    report["checks"]["added-only:220-present"] = added_only["fft"]["220"] > 0.04
    report["checks"]["added-only:440-absent"] = added_only["fft"]["440"] < 0.025
    report["checks"]["added-only:880-absent"] = added_only["fft"]["880"] < 0.025

    mode_d = next(
        mode for mode in result.get("modeResults") or []
        if isinstance(mode, dict) and mode.get("name") == "source-on-add"
    )
    timeline = (mode_d.get("diagnostics") or {}).get("timelineMap") or []
    mixed_windows = []
    mixed_samples = pcm["source-on-add"]
    for index, segment in enumerate(timeline):
        start = float(segment["outputStart"])
        end = float(segment["outputEnd"])
        center = (start + end) / 2
        half_width = min(0.25, max(0.12, (end - start) / 4))
        representative = fft_window(mixed_samples, center - half_width, center + half_width)
        source_name = str(segment["sourceName"])
        segment_duration = end - start
        representative.update({"segment": index, "sourceName": source_name, "kind": "representative"})
        mixed_windows.append(representative)
        if "source-A-440" in source_name and segment_duration >= 1.25:
            report["checks"][f"mixed:{index}:440-present"] = representative["fft"]["440"] > 0.04
            report["checks"][f"mixed:{index}:880-absent"] = representative["fft"]["880"] < 0.025
        elif "source-B-880" in source_name and segment_duration >= 1.25:
            report["checks"][f"mixed:{index}:880-present"] = representative["fft"]["880"] > 0.04
            report["checks"][f"mixed:{index}:440-absent"] = representative["fft"]["440"] < 0.025
        elif "source-STILL" in source_name or "source-C-silent" in source_name:
            report["checks"][f"mixed:{index}:440-absent-on-still"] = representative["fft"]["440"] < 0.025
            report["checks"][f"mixed:{index}:880-absent-on-still"] = representative["fft"]["880"] < 0.025
        if center < 12.8:
            report["checks"][f"mixed:{index}:220-present"] = representative["fft"]["220"] > 0.025

        if index > 0 and end - start > 0.42:
            post_cut = fft_window(mixed_samples, start + 0.10, min(end - 0.08, start + 0.38))
            post_cut.update({"segment": index, "sourceName": source_name, "kind": "postCut"})
            mixed_windows.append(post_cut)
            previous_name = str(timeline[index - 1]["sourceName"])
            if "source-A-440" in previous_name and "source-A-440" not in source_name:
                report["checks"][f"cut:{index}:previous-440-absent"] = post_cut["fft"]["440"] < 0.025
            if "source-B-880" in previous_name and "source-B-880" not in source_name:
                report["checks"][f"cut:{index}:previous-880-absent"] = post_cut["fft"]["880"] < 0.025

    report["exports"]["source-on-add"]["timelineMap"] = timeline
    report["exports"]["source-on-add"]["windows"] = mixed_windows

    repeated_mode = next(
        mode for mode in result.get("modeResults") or []
        if isinstance(mode, dict) and mode.get("name") == "source-on-no-add-repeat"
    )
    repeated_timeline = (repeated_mode.get("diagnostics") or {}).get("timelineMap") or []
    repeated_windows = []
    repeated_samples = pcm["source-on-no-add-repeat"]
    for index, segment in enumerate(repeated_timeline):
        start = float(segment["outputStart"])
        end = float(segment["outputEnd"])
        if end - start < 1.25:
            continue
        center = (start + end) / 2
        representative = fft_window(repeated_samples, center - 0.25, center + 0.25)
        source_name = str(segment["sourceName"])
        representative.update({"segment": index, "sourceName": source_name})
        repeated_windows.append(representative)
        report["checks"][f"repeat:{index}:220-absent"] = representative["fft"]["220"] < 0.025
        if "source-A-440" in source_name:
            report["checks"][f"repeat:{index}:440-present"] = representative["fft"]["440"] > 0.04
            report["checks"][f"repeat:{index}:880-absent"] = representative["fft"]["880"] < 0.025
        elif "source-B-880" in source_name:
            report["checks"][f"repeat:{index}:880-present"] = representative["fft"]["880"] > 0.04
            report["checks"][f"repeat:{index}:440-absent"] = representative["fft"]["440"] < 0.025
        else:
            report["checks"][f"repeat:{index}:440-absent-on-silent"] = representative["fft"]["440"] < 0.025
            report["checks"][f"repeat:{index}:880-absent-on-silent"] = representative["fft"]["880"] < 0.025
    report["exports"]["source-on-no-add-repeat"]["timelineMap"] = repeated_timeline
    report["exports"]["source-on-no-add-repeat"]["windows"] = repeated_windows
    report["checks"]["repeat:better-30s-duration"] = abs(
        report["exports"]["source-on-no-add-repeat"]["probe"]["duration"] - 30.0
    ) < 0.75
    report["passed"] = all(report["checks"].values())
    report_path = AUDIO_ARTIFACT_ROOT / "simulator-audio-analysis.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nObjective PCM/FFT report: {report_path}")
    for name, passed in sorted(report["checks"].items()):
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    return report


def main() -> int:
    device_id, device_name, device_state = pick_device()
    print(f"Using simulator: {device_name} ({device_id})")

    run(["python3", "apple-lite/scripts/prepare_lite_web_bundle.py"])
    run(
        [
            "xcodebuild",
            "-quiet",
            "-project",
            str(PROJECT),
            "-scheme",
            "WZRDVIDLite",
            "-configuration",
            "Debug",
            "-destination",
            f"platform=iOS Simulator,id={device_id}",
            "-derivedDataPath",
            str(DERIVED_DATA),
            "build",
            "CODE_SIGNING_ALLOWED=NO",
        ],
        timeout=300,
    )

    if device_state != "Booted":
        run(["xcrun", "simctl", "boot", device_id])
    run(["xcrun", "simctl", "bootstatus", device_id, "-b"], timeout=120)
    run(["xcrun", "simctl", "install", device_id, str(APP_PATH)], timeout=120)

    env = os.environ.copy()
    env["SIMCTL_CHILD_WZRDVID_LITE_SMOKE"] = "1"
    launch = run(
        [
            "xcrun",
            "simctl",
            "launch",
            "--console",
            "--terminate-running-process",
            device_id,
            BUNDLE_ID,
            "--lite-smoke",
        ],
        env=env,
        timeout=240,
        check=False,
    )
    result = parse_smoke_result(launch.stdout or "")

    print("\nSmoke checks:")
    for name, passed in sorted((result.get("checks") or {}).items()):
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    print("\nCapabilities:")
    for name, value in sorted((result.get("capabilities") or {}).items()):
        print(f"  {name}: {value}")
    for warning in result.get("warnings") or []:
        print(f"WARNING: {warning}")
    for error in result.get("errors") or []:
        print(f"ERROR: {error}")

    audio_report = analyze_exported_audio(device_id, result) if result.get("passed") else None

    if launch.returncode != 0 or not result.get("passed") or not audio_report or not audio_report.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
