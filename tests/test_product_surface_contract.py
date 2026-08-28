"""Focused desktop update-handoff and Preview surface contracts."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import app


class ProductSurfaceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="wzrdvid-product-surface-")
        cls.root = Path(cls._temp.name)
        cls._original_paths = (app.SETTINGS_PATH, app.PREVIEW_DIR, app.IMPORTED_MEDIA_DIR)
        app.SETTINGS_PATH = cls.root / "settings.json"
        app.PREVIEW_DIR = cls.root / "Previews"
        app.IMPORTED_MEDIA_DIR = cls.root / "ImportedMedia"
        cls._patchers = (
            mock.patch.object(app.MainWindow, "check_media_tools", lambda self: None),
            mock.patch.object(app.MainWindow, "check_for_updates", lambda self, manual=False: None),
            mock.patch.object(app.MainWindow, "start_auto_preview_cache_cleanup", lambda self: None),
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

    def test_fresh_preview_controls_have_current_label_and_range_state(self) -> None:
        self.assertEqual(self.window.preview_duration.currentText(), "5s")
        self.assertEqual(self.window.preview_button.text(), "PREVIEW 5 SEC")
        self.assertFalse(self.window.preview_custom.isEnabled())

        self.window.preview_duration.setCurrentText("10s")
        self.assertEqual(self.window.preview_button.text(), "PREVIEW 10 SEC")
        self.window.preview_from.setCurrentText("Custom timestamp")
        self.assertTrue(self.window.preview_custom.isEnabled())

    def test_update_activation_opens_exact_absolute_url_once_and_no_unrelated_control_opens(self) -> None:
        release_url = "https://github.com/wzrdgang/wzrdVID/releases/tag/v0.4.0"
        self.window.update_check_finished("v0.4.0", True, release_url)
        opened = []
        with (
            mock.patch.object(app.QDesktopServices, "openUrl", side_effect=lambda url: opened.append(url) or True),
            mock.patch.object(app.QMessageBox, "warning") as warning,
        ):
            self.window.check_update_button.click()
            self.assertEqual(opened, [])
            self.window.download_update_button.click()

        self.assertEqual(len(opened), 1)
        self.assertFalse(opened[0].isRelative())
        self.assertEqual(opened[0].scheme(), "https")
        self.assertEqual(opened[0].host(), "github.com")
        self.assertEqual(opened[0].toString(), release_url)
        warning.assert_not_called()

    def test_update_handoff_failure_is_reported(self) -> None:
        release_url = "https://github.com/wzrdgang/wzrdVID/releases/latest"
        self.window.latest_release_url = release_url
        with (
            mock.patch.object(app.QDesktopServices, "openUrl", return_value=False) as opener,
            mock.patch.object(app.QMessageBox, "warning") as warning,
        ):
            self.window.open_update_download()

        opener.assert_called_once()
        self.assertEqual(opener.call_args.args[0].toString(), release_url)
        warning.assert_called_once()
        self.assertIn(release_url, warning.call_args.args[2])
        self.assertIn("Could not open update page", self.window.log_output.toPlainText())

    def test_preview_open_success_and_failure_use_one_absolute_local_url(self) -> None:
        preview = self.root / "Previews" / "preview_contract.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"preview")
        self.window.last_preview_path = str(preview)

        opened = []
        with (
            mock.patch.object(app.QDesktopServices, "openUrl", side_effect=lambda url: opened.append(url) or True),
            mock.patch.object(app.QMessageBox, "warning") as warning,
        ):
            self.window.open_preview()
        self.assertEqual(len(opened), 1)
        self.assertFalse(opened[0].isRelative())
        self.assertTrue(opened[0].isLocalFile())
        self.assertEqual(Path(opened[0].toLocalFile()), preview)
        warning.assert_not_called()

        with (
            mock.patch.object(app.QDesktopServices, "openUrl", return_value=False) as opener,
            mock.patch.object(app.QMessageBox, "warning") as warning,
        ):
            self.window.open_preview()
        opener.assert_called_once()
        warning.assert_called_once()
        self.assertIn(str(preview), warning.call_args.args[2])
        self.assertIn("Could not open preview", self.window.log_output.toPlainText())

    def test_manual_cache_cleanup_clears_stale_open_preview_state(self) -> None:
        preview = self.root / "Previews" / "preview_deleted.mp4"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_bytes(b"preview")
        self.window.last_preview_path = str(preview)
        self.window.open_preview_button.setEnabled(True)
        self.window.open_preview_button.show()
        preview.unlink()

        with mock.patch.object(app.QMessageBox, "information"):
            self.window._preview_cache_cleanup_finished(
                app.CacheCleanupSummary(files=1, bytes=7),
                True,
            )

        self.assertIsNone(self.window.last_preview_path)
        self.assertFalse(self.window.open_preview_button.isEnabled())
        self.assertTrue(self.window.open_preview_button.isHidden())


if __name__ == "__main__":
    unittest.main()
