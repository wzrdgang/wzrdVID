#!/usr/bin/env python3
"""Build and run the WZRD.VID Lite iOS simulator smoke harness."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPLE_ROOT = ROOT / "apple-lite"
PROJECT = APPLE_ROOT / "WZRDVIDLite.xcodeproj"
DERIVED_DATA = APPLE_ROOT / "DerivedData"
APP_PATH = DERIVED_DATA / "Build/Products/Debug-iphonesimulator/WZRDVIDLite.app"
BUNDLE_ID = "com.samhowell.wzrdvid.lite"


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
        timeout=90,
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

    if launch.returncode != 0 or not result.get("passed"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
