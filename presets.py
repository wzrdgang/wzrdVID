"""Preset definitions for WZRD.VID."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ASCII_RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
BLOCK_RAMP = " .:-=+*#%@"
CHUNKY_SHADE_RAMP = "  ░▒▓█"
CHUNKY_STACK_RAMP = " ▁▂▃▄▅▆▇█"
DENSE_RAMP = "  .,:;irsXA253hMHGS#9B&@$"
GLITCH_RAMP = " .,:;irsXA253hMHGS#9B&@$%?!/\\|[]{}<>"
BUMP_TAPE_RAMP = "  .:-=+*#%@ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MONO_RAMP = "  .:-=+*#%@"


PRESETS: dict[str, dict[str, Any]] = {
    "Classic ANSI": {
        "charset": ASCII_RAMP,
        "background": (7, 7, 10),
        "contrast": 1.12,
        "saturation": 1.12,
        "tint": None,
        "tint_mix": 0.0,
        "base_noise": 0.002,
        "scanline_strength": 0.18,
        "glitch_strength": 0.55,
        "rgb_split": 2,
        "hue_speed": 0.015,
    },
    "Green Terminal": {
        "charset": ASCII_RAMP,
        "background": (0, 8, 3),
        "contrast": 1.28,
        "saturation": 0.72,
        "tint": (84, 255, 128),
        "tint_mix": 0.78,
        "base_noise": 0.006,
        "scanline_strength": 0.34,
        "glitch_strength": 0.45,
        "rgb_split": 1,
        "hue_speed": 0.004,
    },
    "Amber Terminal": {
        "charset": ASCII_RAMP,
        "background": (14, 7, 0),
        "contrast": 1.26,
        "saturation": 0.74,
        "tint": (255, 174, 52),
        "tint_mix": 0.82,
        "base_noise": 0.005,
        "scanline_strength": 0.32,
        "glitch_strength": 0.42,
        "rgb_split": 1,
        "hue_speed": 0.004,
    },
    "Dial-Up Neon": {
        "charset": DENSE_RAMP,
        "background": (3, 4, 14),
        "contrast": 1.42,
        "saturation": 1.42,
        "tint": (72, 235, 255),
        "tint_mix": 0.18,
        "base_noise": 0.016,
        "scanline_strength": 0.28,
        "glitch_strength": 1.0,
        "rgb_split": 5,
        "hue_speed": 0.032,
    },
    "Glitch Hell": {
        "charset": GLITCH_RAMP,
        "background": (2, 2, 6),
        "contrast": 1.68,
        "saturation": 1.68,
        "tint": (255, 64, 190),
        "tint_mix": 0.16,
        "base_noise": 0.055,
        "scanline_strength": 0.42,
        "glitch_strength": 1.85,
        "rgb_split": 8,
        "hue_speed": 0.055,
    },
    "Midnight Bump Tape": {
        "charset": BUMP_TAPE_RAMP,
        "background": (0, 0, 0),
        "contrast": 1.38,
        "saturation": 0.0,
        "tint": (245, 245, 235),
        "tint_mix": 0.92,
        "base_noise": 0.004,
        "scanline_strength": 0.08,
        "glitch_strength": 0.22,
        "rgb_split": 0,
        "hue_speed": 0.0,
    },
    "Monochrome Brutalist": {
        "charset": MONO_RAMP,
        "background": (245, 245, 238),
        "contrast": 1.9,
        "saturation": 0.0,
        "tint": (12, 12, 12),
        "tint_mix": 0.86,
        "base_noise": 0.0,
        "scanline_strength": 0.0,
        "glitch_strength": 0.12,
        "rgb_split": 0,
        "hue_speed": 0.0,
    },
    "Chunkcore": {
        "charset": CHUNKY_SHADE_RAMP,
        "render_mode": "chunky_blocks",
        "background": (5, 6, 9),
        "contrast": 1.62,
        "saturation": 1.24,
        "tint": None,
        "tint_mix": 0.0,
        "base_noise": 0.0,
        "scanline_strength": 0.12,
        "glitch_strength": 0.32,
        "rgb_split": 1,
        "hue_speed": 0.01,
    },
    "Soft CRT Blocks": {
        "charset": CHUNKY_SHADE_RAMP,
        "render_mode": "chunky_blocks",
        "background": (0, 7, 2),
        "contrast": 1.74,
        "saturation": 0.72,
        "tint": (72, 255, 118),
        "tint_mix": 0.84,
        "base_noise": 0.0,
        "scanline_strength": 0.28,
        "glitch_strength": 0.24,
        "rgb_split": 0,
        "hue_speed": 0.004,
    },
    "WZRD Blocks": {
        "charset": CHUNKY_STACK_RAMP,
        "render_mode": "chunky_blocks",
        "background": (3, 3, 12),
        "contrast": 1.76,
        "saturation": 1.55,
        "tint": (96, 238, 255),
        "tint_mix": 0.12,
        "base_noise": 0.004,
        "scanline_strength": 0.22,
        "glitch_strength": 0.75,
        "rgb_split": 3,
        "hue_speed": 0.034,
    },
    "Brutal Blocks": {
        "charset": CHUNKY_SHADE_RAMP,
        "render_mode": "chunky_blocks",
        "background": (8, 8, 8),
        "contrast": 2.05,
        "saturation": 0.0,
        "tint": (238, 238, 230),
        "tint_mix": 0.9,
        "base_noise": 0.0,
        "scanline_strength": 0.06,
        "glitch_strength": 0.12,
        "rgb_split": 0,
        "hue_speed": 0.0,
    },
}


PRESET_DESCRIPTIONS = {
    "Classic ANSI": "Source-colored terminal text with a restrained scanline edge.",
    "Green Terminal": "Phosphor green monochrome with soft noise and old CRT density.",
    "Amber Terminal": "Warm amber console output with vintage terminal contrast.",
    "Dial-Up Neon": "Cyan-magenta early-web color drift with RGB offsets and hard contrast.",
    "Glitch Hell": "Maximal noisy character swaps, split channels, slices, and hard contrast.",
    "Midnight Bump Tape": "Stark black-and-white interstitial texture with blocky late-night tape grit.",
    "Monochrome Brutalist": "High-contrast architectural black-on-light text blocks.",
    "Chunkcore": "Big pastel block glyphs with source color, blunt contrast, and cleaner compression.",
    "Soft CRT Blocks": "Large mint phosphor cells for a bold terminal look that stays readable small.",
    "WZRD Blocks": "Heavy shaded block glyphs, color drift, and restrained glitch for branded WZRD texture.",
    "Brutal Blocks": "Large monochrome shade blocks with blunt contrast and minimal detail noise.",
}


ALIASES = {
    "clean ANSI": "Classic ANSI",
    "green terminal": "Green Terminal",
    "amber terminal": "Amber Terminal",
    "high contrast": "Monochrome Brutalist",
    "glitch": "Glitch Hell",
    "Cyberpunk": "Dial-Up Neon",
    "Chunky ANSI Blocks": "Chunkcore",
    "Chunky Green Blocks": "Soft CRT Blocks",
    "Chunky Cyber Blocks": "WZRD Blocks",
    "Chunky Mono Blocks": "Brutal Blocks",
}


def preset_names() -> list[str]:
    """Return preset names in display order."""
    return list(PRESETS.keys())


def preset_description(name: str) -> str:
    """Return human-readable intent for a preset."""
    resolved_name = ALIASES.get(name, name)
    return PRESET_DESCRIPTIONS.get(resolved_name, "")


def get_preset(name: str) -> dict[str, Any]:
    """Return a defensive copy of a preset by name."""
    resolved_name = ALIASES.get(name, name)
    if resolved_name not in PRESETS:
        valid = ", ".join(preset_names())
        raise KeyError(f"Unknown preset '{name}'. Expected one of: {valid}")
    preset = deepcopy(PRESETS[resolved_name])
    preset["name"] = resolved_name
    return preset
