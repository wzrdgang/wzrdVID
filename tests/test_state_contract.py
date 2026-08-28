"""Tracked v0.4.0 schema-6 and desktop state contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

import app
import renderer


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

    def test_reset_clears_spatial_state_and_restores_layer(self) -> None:
        self.window._set_zone_state(
            self.valid_zones(),
            {"pixel_sorting": "one", "skrrt": "two"},
            warn_on_repair=False,
        )
        self.window._set_codec_layer_order(tuple(reversed(renderer.CODEC_LAYER_ORDER)))
        with mock.patch.object(
            QMessageBox,
            "question",
            return_value=QMessageBox.StandardButton.Reset,
        ):
            self.window.reset_project()
        self.assertFalse(self.window.zones)
        self.assertFalse(self.window.effect_zone_assignments)
        self.assertEqual(self.window._codec_layer_order(), renderer.CODEC_LAYER_ORDER)


if __name__ == "__main__":
    unittest.main()
