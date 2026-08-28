"""Direct tests for the stdlib-only persisted desktop state boundary."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

import datamosh
import state_contract


class StateModuleContractTests(unittest.TestCase):
    @staticmethod
    def zones() -> list[dict[str, object]]:
        return [
            {"id": "one", "name": "Face", "x": 0.1, "y": 0.1, "width": 0.3, "height": 0.4},
            {"id": "two", "name": "Sky", "x": 0.55, "y": 0.05, "width": 0.35, "height": 0.3},
            {"id": "three", "name": "Floor", "x": 0.0, "y": 0.7, "width": 1.0, "height": 0.3},
        ]

    def normalize(self, raw: dict[str, object]) -> tuple[dict[str, object], bool]:
        return state_contract.normalize_persisted_state(
            raw,
            current_effects=state_contract.normalize_effects({}),
            style_fx_random_seed_fallback=424_242,
        )

    def test_module_imports_only_stdlib(self) -> None:
        source = Path(state_contract.__file__).read_text()
        imports = {
            node.module.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom) and node.module not in {None, "__future__"}
        }
        imports.update(
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        self.assertEqual(imports, {"dataclasses", "math", "typing"})

    def test_schema_3_4_5_migrate_without_future_zones(self) -> None:
        for schema in (3, 4, 5):
            with self.subTest(schema=schema):
                state, repaired = self.normalize(
                    {
                        "schema_version": schema,
                        "zones": self.zones(),
                        "effect_zone_assignments": {"skrrt": "one"},
                        "max_video_length": "90" if schema >= 4 else "",
                        "random_clip_assembly": schema >= 4,
                        "style_begin_time": "0:07" if schema >= 5 else "0:00",
                    }
                )
                self.assertEqual(state["schema_version"], 6)
                self.assertEqual(state["zones"], [])
                self.assertEqual(state["effect_zone_assignments"], {})
                self.assertFalse(repaired)
                self.assertEqual(state["max_video_length"], "90" if schema >= 4 else "")
                self.assertEqual(state["random_clip_assembly"], schema >= 4)
                self.assertEqual(state["style_begin_time"], "0:07" if schema >= 5 else "0:00")

    def test_schema_6_valid_state_preserves_zone_ids_and_assignments(self) -> None:
        state, repaired = self.normalize(
            {
                "schema_version": 6,
                "zones": self.zones(),
                "effect_zone_assignments": {
                    "pixel_sorting": "one",
                    "databending": "two",
                    "circuit_bending": "three",
                    "hex_editing": "one",
                    "random_noise_bw": "two",
                    "skrrt": "three",
                },
            }
        )
        self.assertFalse(repaired)
        self.assertEqual([zone["id"] for zone in state["zones"]], ["one", "two", "three"])
        self.assertEqual(
            tuple(state["effect_zone_assignments"]),
            state_contract.ZONE_ASSIGNMENT_EFFECT_ORDER,
        )

    def test_malformed_schema_6_matches_current_repairs(self) -> None:
        first = self.zones()[0]
        state, repaired = self.normalize(
            {
                "schema_version": "6",
                "max_video_length": " none ",
                "random_clip_assembly": "yes",
                "zones": [
                    first,
                    dict(first),
                    {"id": "inf", "name": "Bad", "x": float("inf"), "y": 0, "width": 1, "height": 1},
                    {"id": "clip", "name": " Clip ", "x": 0.8, "y": -0.2, "width": 0.5, "height": 0.5},
                ],
                "effect_zone_assignments": {
                    "pixel_sorting": "one",
                    "databending": "missing",
                    "datamoshing": "one",
                    "skrrt": "one",
                },
                "codec_layer_order": ["skrrt", "skrrt", "unknown"],
                "style_fx_coverage_mode": {"bad": True},
                "style_fx_manual_blocks": {"start": "0:01", "end": "0:02"},
                "style_fx_random_percent": "bad",
                "style_fx_random_seed": "bad",
                "transition_mode": "None",
            }
        )
        self.assertTrue(repaired)
        self.assertEqual([zone["id"] for zone in state["zones"]], ["one", "clip"])
        self.assertEqual(state["zones"][1]["name"], "Clip")
        self.assertEqual(
            state["effect_zone_assignments"],
            {"pixel_sorting": "one", "skrrt": "one"},
        )
        self.assertEqual(
            state["codec_layer_order"],
            ["skrrt", "datamoshing", "overflow", "scatter", "bleed"],
        )
        self.assertEqual(state["style_fx_coverage_mode"], state_contract.STYLE_FX_FULL)
        self.assertEqual(state["style_fx_manual_blocks"], [])
        self.assertEqual(state["style_fx_random_percent"], 10)
        self.assertEqual(state["style_fx_random_seed"], 424_242)
        self.assertEqual(state["max_video_length"], "")
        self.assertTrue(state["random_clip_assembly"])
        self.assertEqual(state["transition_mode"], "Hard Cut")

    def test_layer_style_audio_and_effect_contracts(self) -> None:
        self.assertEqual(state_contract.CODEC_LAYER_ORDER, datamosh.DATAMOSH_MODE_ORDER)
        self.assertEqual(
            state_contract.normalize_codec_layer_order(tuple(reversed(state_contract.CODEC_LAYER_ORDER))),
            tuple(reversed(state_contract.CODEC_LAYER_ORDER)),
        )
        self.assertEqual(
            state_contract.normalize_codec_layer_order(["bleed", "bleed", "unknown"]),
            ("bleed", "datamoshing", "overflow", "skrrt", "scatter"),
        )
        self.assertEqual(state_contract.canonical_audio_mode("Keep source audio"), "Source audio only")
        self.assertEqual(state_contract.canonical_transition_mode("None"), "Hard Cut")
        self.assertEqual(
            state_contract.normalize_style_fx_coverage_mode(" manual + RANDOM "),
            state_contract.STYLE_FX_MANUAL_RANDOM,
        )
        defaults = state_contract.normalize_effects({})
        self.assertTrue(defaults["glitch"])
        self.assertFalse(defaults["pixel_sorting"])
        self.assertFalse(defaults["skrrt"])

    def test_default_and_reset_contracts(self) -> None:
        current = state_contract.default_project_state(
            ui_language="es",
            random_seed=1,
            style_fx_random_seed=2,
            weird_seed=3,
        )
        current.update(
            {
                "resolution_index": 2,
                "preview_from": "Custom timestamp",
                "preview_custom": "0:37",
                "style_begin_time": "0:09",
                "codec_layer_order": list(reversed(state_contract.CODEC_LAYER_ORDER)),
                "zones": self.zones(),
                "effect_zone_assignments": {"skrrt": "three"},
            }
        )
        reset = state_contract.reset_project_state(
            current,
            random_seed=11,
            style_fx_random_seed=12,
            weird_seed=13,
        )
        expected = state_contract.default_project_state(
            ui_language="es",
            random_seed=11,
            style_fx_random_seed=12,
            weird_seed=13,
        )
        expected.update(
            {
                "resolution_index": 2,
                "preview_from": "Custom timestamp",
                "preview_custom": "0:37",
            }
        )
        self.assertEqual(reset, expected)
        self.assertEqual(reset["zones"], [])
        self.assertEqual(reset["effect_zone_assignments"], {})
        self.assertEqual(reset["codec_layer_order"], list(state_contract.CODEC_LAYER_ORDER))

    def test_canonical_serialization_is_byte_idempotent(self) -> None:
        state = state_contract.default_project_state(
            random_seed=101,
            style_fx_random_seed=202,
            weird_seed=303,
        )
        state.update(
            {
                "zones": self.zones()[:2],
                "effect_zone_assignments": {"pixel_sorting": "one", "skrrt": "two"},
                "codec_layer_order": list(reversed(state_contract.CODEC_LAYER_ORDER)),
                "transition_mode": "None",
                "style_fx_coverage_mode": "Manual + random",
                "style_fx_manual_blocks": [{"start": "0:04", "end": "0:06"}],
            }
        )
        first = state_contract.canonicalize_persisted_state(state)
        first_bytes = json.dumps(first, indent=2).encode()
        second = state_contract.canonicalize_persisted_state(json.loads(first_bytes))
        second_bytes = json.dumps(second, indent=2).encode()
        self.assertEqual(second_bytes, first_bytes)
        self.assertEqual([zone["id"] for zone in second["zones"]], ["one", "two"])
        self.assertEqual(second["transition_mode"], "Hard Cut")


if __name__ == "__main__":
    unittest.main()
