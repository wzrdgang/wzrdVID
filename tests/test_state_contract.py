"""Tracked v0.4.0 schema-6 and desktop state contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PIL import Image

import app
import renderer
import state_contract


class StateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="wzrdvid-frame-state-tests-")
        cls.root = Path(cls._temp.name)
        cls._original_paths = (
            app.SETTINGS_PATH,
            app.PREVIEW_DIR,
            app.IMPORTED_MEDIA_DIR,
        )
        app.SETTINGS_PATH = cls.root / "settings.json"
        app.PREVIEW_DIR = cls.root / "Previews"
        app.IMPORTED_MEDIA_DIR = cls.root / "ImportedMedia"
        cls._patchers = (
            mock.patch.object(app.MainWindow, "check_media_tools", lambda self: None),
            mock.patch.object(
                app.MainWindow, "check_for_updates", lambda self, manual=False: None
            ),
            mock.patch.object(
                app.MainWindow, "start_auto_preview_cache_cleanup", lambda self: None
            ),
        )
        for patcher in cls._patchers:
            patcher.start()
        cls.qapp = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls) -> None:
        for patcher in reversed(cls._patchers):
            patcher.stop()
        app.SETTINGS_PATH, app.PREVIEW_DIR, app.IMPORTED_MEDIA_DIR = cls._original_paths
        cls._temp.cleanup()

    def setUp(self) -> None:
        app.SETTINGS_PATH.unlink(missing_ok=True)
        self.window = app.MainWindow()

    def tearDown(self) -> None:
        self.window.close()
        self.qapp.processEvents()

    @staticmethod
    def valid_zones() -> list[dict[str, object]]:
        return [
            {"id": "one", "name": "Face", "x": 0.1, "y": 0.1, "width": 0.3, "height": 0.4},
            {"id": "two", "name": "Sky", "x": 0.55, "y": 0.05, "width": 0.35, "height": 0.3},
        ]

    def test_schema_3_4_5_ignore_zone_fields(self) -> None:
        future = self.valid_zones()[0]
        for schema in (3, 4, 5):
            self.window._apply_project_state(
                {
                    "schema_version": schema,
                    "zones": [future],
                    "effect_zone_assignments": {"skrrt": "one"},
                }
            )
            self.assertFalse(self.window.zones, schema)
            self.assertFalse(self.window.effect_zone_assignments, schema)

    def test_schema_6_missing_and_valid_zone_fields(self) -> None:
        self.window._apply_project_state({"schema_version": 6})
        self.assertFalse(self.window.zones)
        self.assertFalse(self.window.effect_zone_assignments)

        self.window._apply_project_state(
            {
                "schema_version": 6,
                "zones": self.valid_zones(),
                "effect_zone_assignments": {
                    "pixel_sorting": "one",
                    "hex_editing": "two",
                    "skrrt": "one",
                },
            }
        )
        self.assertEqual([zone.id for zone in self.window.zones], ["one", "two"])
        self.assertEqual(
            self.window.effect_zone_assignments,
            {"pixel_sorting": "one", "hex_editing": "two", "skrrt": "one"},
        )

    def test_malformed_state_and_exact_zone_eligibility(self) -> None:
        malformed = [
            self.valid_zones()[0],
            dict(self.valid_zones()[0]),
            {"id": "bad", "name": "Bad", "x": float("inf"), "y": 0, "width": 1, "height": 1},
            {"id": "clip", "name": "Clip", "x": 0.8, "y": -0.2, "width": 0.5, "height": 0.5},
        ]
        self.window._apply_project_state(
            {
                "schema_version": 6,
                "zones": malformed,
                "effect_zone_assignments": {
                    "pixel_sorting": "one",
                    "databending": "missing",
                    "datamoshing": "one",
                    "overflow": "one",
                    "scatter": "one",
                    "bleed": "one",
                    "skrrt": "one",
                },
            }
        )
        self.assertEqual([zone.id for zone in self.window.zones], ["one", "clip"])
        self.assertEqual(
            self.window.effect_zone_assignments,
            {"pixel_sorting": "one", "skrrt": "one"},
        )
        self.assertEqual(
            renderer.ZONE_ASSIGNMENT_EFFECT_ORDER,
            (
                "pixel_sorting",
                "databending",
                "circuit_bending",
                "hex_editing",
                "random_noise_bw",
                "skrrt",
            ),
        )
        self.assertTrue(
            {"datamoshing", "overflow", "scatter", "bleed"}.isdisjoint(
                renderer.ZONE_ASSIGNMENT_EFFECT_ORDER
            )
        )

    def test_state_round_trip_rename_layer_and_byte_idempotence(self) -> None:
        self.window._set_zone_state(
            self.valid_zones(),
            {"pixel_sorting": "one", "skrrt": "two"},
            warn_on_repair=False,
        )
        self.window._set_codec_layer_order(tuple(reversed(renderer.CODEC_LAYER_ORDER)))
        self.window.selected_zone_id = "one"
        self.window._refresh_zone_ui()
        self.window.zone_name_edit.setText("Renamed Face")
        self.window._rename_zone()
        self.assertEqual(self.window._selected_zone().id, "one")
        self.assertEqual(self.window._selected_zone().name, "Renamed Face")

        self.window._save_settings()
        first_bytes = app.SETTINGS_PATH.read_bytes()
        second = app.MainWindow()
        try:
            self.assertEqual([zone.id for zone in second.zones], ["one", "two"])
            self.assertEqual(second.zones[0].name, "Renamed Face")
            self.assertEqual(
                second.effect_zone_assignments,
                {"pixel_sorting": "one", "skrrt": "two"},
            )
            self.assertEqual(
                second._codec_layer_order(), tuple(reversed(renderer.CODEC_LAYER_ORDER))
            )
            second._save_settings()
            self.assertEqual(app.SETTINGS_PATH.read_bytes(), first_bytes)
            self.assertEqual(
                json.loads(first_bytes)["schema_version"], 6
            )
        finally:
            second.close()

        self.window._set_codec_layer_order(tuple(reversed(renderer.CODEC_LAYER_ORDER)))
        self.window._apply_project_state({"schema_version": 6})
        self.assertEqual(self.window._codec_layer_order(), renderer.CODEC_LAYER_ORDER)

    def test_zone_motion_controls_persistence_duplicate_and_static_canonicalization(self) -> None:
        base = self.valid_zones()[0]
        self.window._set_zone_state([base], {"pixel_sorting": "one", "skrrt": "one"}, warn_on_repair=False)
        self.window.selected_zone_id = "one"
        self.window._refresh_zone_ui()
        self.assertEqual(self.window.zone_motion_combo.currentText(), "Static")
        self.assertFalse(self.window.zone_motion_amount.isEnabled())
        self.assertFalse(self.window.zone_motion_cycles.isEnabled())
        self.assertEqual(self.window.zone_motion_amount.value(), 25.0)
        self.assertEqual(self.window.zone_motion_cycles.value(), 2)
        self.assertEqual(
            self.window.zone_motion_note.text(),
            "Drift/Pulse moves the five Material effects only. SKRRT keeps the Zone’s static base rectangle.",
        )
        self.assertIn("disabled for Static", self.window.zone_motion_amount.accessibleDescription())
        self.assertIn("disabled for Static", self.window.zone_motion_cycles.accessibleDescription())

        self.window.zone_motion_combo.setCurrentIndex(
            self.window.zone_motion_combo.findData("drift")
        )
        self.window.zone_motion_amount.setValue(37.5)
        self.window.zone_motion_cycles.setValue(6)
        moving = self.window._selected_zone()
        self.assertEqual(
            (moving.motion_mode, moving.motion_amount, moving.motion_cycles),
            ("drift", 37.5, 6),
        )
        self.assertTrue(self.window.zone_motion_amount.isEnabled())
        self.assertTrue(self.window.zone_motion_cycles.isEnabled())

        self.window._duplicate_zone()
        duplicate = self.window._selected_zone()
        self.assertNotEqual(duplicate.id, moving.id)
        self.assertEqual(
            (duplicate.motion_mode, duplicate.motion_amount, duplicate.motion_cycles),
            ("drift", 37.5, 6),
        )

        self.window._save_settings()
        first_bytes = app.SETTINGS_PATH.read_bytes()
        second = app.MainWindow()
        try:
            self.assertEqual(second.zones[0].motion_mode, "drift")
            self.assertEqual(second.zones[0].motion_amount, 37.5)
            self.assertEqual(second.zones[0].motion_cycles, 6)
            second._save_settings()
            self.assertEqual(app.SETTINGS_PATH.read_bytes(), first_bytes)
        finally:
            second.close()

        self.window.selected_zone_id = "one"
        self.window._refresh_zone_ui()
        self.window.zone_motion_combo.setCurrentIndex(
            self.window.zone_motion_combo.findData(None)
        )
        self.assertEqual(self.window._selected_zone().as_dict(), base)
        self.assertEqual(self.window.zone_motion_amount.value(), 25.0)
        self.assertEqual(self.window.zone_motion_cycles.value(), 2)

    def test_preview_collects_current_unsaved_moving_zone_state(self) -> None:
        source = self.root / "preview-zone-source.png"
        Image.new("RGB", (64, 36), (90, 140, 210)).save(source)
        self.window.timeline_items = [
            {
                "path": str(source),
                "kind": "photo",
                "duration": 8.0,
                "photo_hold_duration": "8.0",
                "trim_start": "0:00",
                "trim_end": "auto",
                "has_audio": False,
                "include_audio": False,
            }
        ]
        self.window._refresh_timeline_table()
        self.window._set_zone_state(
            [self.valid_zones()[0]],
            {"pixel_sorting": "one"},
            warn_on_repair=False,
        )
        self.window.effect_checks["pixel_sorting"].setChecked(True)
        self.window.zone_motion_combo.setCurrentIndex(
            self.window.zone_motion_combo.findData("pulse")
        )
        self.window.zone_motion_amount.setValue(41.0)
        self.window.zone_motion_cycles.setValue(7)
        self.window._set_combo_text(self.window.preview_from, "Custom timestamp")
        self.window.preview_custom.setText("0:02")

        settings = self.window._collect_preview_settings()
        self.assertEqual(settings.output_time_offset, 2.0)
        self.assertEqual(settings.effect_zone_assignments, {"pixel_sorting": "one"})
        self.assertEqual(len(settings.zones), 1)
        self.assertEqual(
            (
                settings.zones[0].motion_mode,
                settings.zones[0].motion_amount,
                settings.zones[0].motion_cycles,
            ),
            ("pulse", 41.0, 7),
        )

    def test_recipe_export_import_uses_the_same_canonical_boundary(self) -> None:
        recipe_path = self.root / "phase13-recipe.json"
        recipe_zones = self.valid_zones()
        recipe_zones[0].update(
            {
                "motion_mode": "pulse",
                "motion_amount": 32.0,
                "motion_cycles": 4,
            }
        )
        self.window._set_zone_state(
            recipe_zones,
            {"pixel_sorting": "one", "skrrt": "two"},
            warn_on_repair=False,
        )
        reversed_layer = tuple(reversed(renderer.CODEC_LAYER_ORDER))
        self.window._set_codec_layer_order(reversed_layer)
        self.window.style_begin_time.setText("0:07")
        self.window._set_combo_text(
            self.window.style_fx_coverage_mode,
            state_contract.STYLE_FX_MANUAL,
        )
        self.window.add_style_fx_manual_block("0:01", "0:02")

        with mock.patch.object(
            QFileDialog,
            "getSaveFileName",
            return_value=(str(recipe_path), "WZRD.VID recipe (*.json)"),
        ):
            self.window.save_project_preset()

        exported = json.loads(recipe_path.read_text())
        self.assertEqual(exported["schema_version"], state_contract.SCHEMA_VERSION)
        self.window._apply_project_state({"schema_version": 6})
        self.assertFalse(self.window.zones)

        with mock.patch.object(
            QFileDialog,
            "getOpenFileName",
            return_value=(str(recipe_path), "WZRD.VID recipe (*.json)"),
        ):
            self.window.load_project_preset()

        self.assertEqual([zone.id for zone in self.window.zones], ["one", "two"])
        self.assertEqual(
            (
                self.window.zones[0].motion_mode,
                self.window.zones[0].motion_amount,
                self.window.zones[0].motion_cycles,
            ),
            ("pulse", 32.0, 4),
        )
        self.assertEqual(
            self.window.effect_zone_assignments,
            {"pixel_sorting": "one", "skrrt": "two"},
        )
        self.assertEqual(self.window._codec_layer_order(), reversed_layer)
        self.assertEqual(self.window.style_begin_time.text(), "0:07")
        self.assertEqual(
            self.window.style_fx_coverage_mode.currentText(),
            state_contract.STYLE_FX_MANUAL,
        )
        self.assertEqual(
            [row.values() for row in self.window.style_fx_block_rows],
            [("0:01", "0:02")],
        )

    def test_reset_clears_spatial_state_and_restores_layer(self) -> None:
        self.assertEqual(
            tuple(key for key, _label, _tooltip in app.EFFECTS),
            state_contract.PERSISTED_EFFECT_ORDER,
        )
        self.window._set_zone_state(
            self.valid_zones(),
            {"pixel_sorting": "one", "skrrt": "two"},
            warn_on_repair=False,
        )
        self.window._set_codec_layer_order(tuple(reversed(renderer.CODEC_LAYER_ORDER)))
        self.window.style_begin_time.setText("0:09")
        self.window.max_video_length.setText("30")
        self.window.random_clip_assembly.setChecked(True)
        self.window.resolution_slider.setValue(2)
        self.window._set_combo_text(self.window.preview_from, "Custom timestamp")
        self.window.preview_duration.setCurrentText("10s")
        self.window.preview_custom.setText("0:37")
        with mock.patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Reset,
        ):
            self.window.reset_project()
        self.assertFalse(self.window.zones)
        self.assertFalse(self.window.effect_zone_assignments)
        self.assertEqual(self.window._codec_layer_order(), renderer.CODEC_LAYER_ORDER)
        self.assertEqual(self.window.style_begin_time.text(), "0:00")
        self.assertEqual(self.window.max_video_length.text(), "")
        self.assertFalse(self.window.random_clip_assembly.isChecked())
        self.assertEqual(self.window.resolution_slider.value(), 2)
        self.assertEqual(self.window.preview_from.currentText(), "Custom timestamp")
        self.assertEqual(self.window.preview_duration.currentText(), "5s")
        self.assertEqual(self.window.preview_custom.text(), "0:37")


if __name__ == "__main__":
    unittest.main()
