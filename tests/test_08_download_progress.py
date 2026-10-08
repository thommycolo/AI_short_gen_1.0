"""Unit test for Video Download Progress UI and Modern FFmpeg Integration"""

import unittest
from PySide6.QtWidgets import QApplication
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.ui.modals.video_download_modal import VideoDownloadModal, _format_bytes, _format_seconds
from app.utils.ffmpeg_installer import find_system_ffmpeg

app = QApplication.instance() or QApplication([])

class TestDownloadProgressAndFFmpeg(unittest.TestCase):
    def test_formatting_helpers(self):
        # MiB formatting
        self.assertEqual(_format_bytes(2.25 * 1024 * 1024), "2.25MiB")
        self.assertEqual(_format_bytes(3.53 * 1024 * 1024), "3.53MiB")
        # Time formatting
        self.assertEqual(_format_seconds(0), "00:00")
        self.assertEqual(_format_seconds(125), "02:05")

    def test_ffmpeg_modern_priority(self):
        ff, _ = find_system_ffmpeg()
        self.assertIsNotNone(ff)
        # Assicura che non venga usato il vecchio ffmpeg KeyShot9 del 2016
        self.assertNotIn("KeyShot9", ff)

    def test_modal_progress_ui_signals(self):
        mgr = ContinuousVideoPoolManager()
        modal = VideoDownloadModal(mgr)

        # Test initial state
        self.assertEqual(modal.progress_bar.value(), 0)
        self.assertEqual(modal.lbl_percent_pill.text(), "0%")

        # Test progress update signal
        modal.signals.progress_updated.emit(
            45.2,
            "[download]  45.2% of 2.25MiB at 3.53MiB/s (ETA: 00:02)",
            "3.53MiB/s | ETA: 00:02",
            "Minecraft 100 Days Hardcore"
        )

        self.assertEqual(modal.progress_bar.value(), 45)
        self.assertEqual(modal.lbl_percent_pill.text(), "45%")
        self.assertIn("45.2%", modal.lbl_download_stats.text())
        self.assertIn("Minecraft", modal.lbl_current_title.text())
        self.assertIn("3.53MiB/s", modal.lbl_eta_speed.text())

        # Test 100% completed signal
        modal.signals.item_completed.emit("https://youtube.com/watch?v=123", "Master Intatto (ID: #1)")
        self.assertEqual(modal.progress_bar.value(), 100)
        self.assertEqual(modal.lbl_percent_pill.text(), "100%")
        self.assertIn("Completato", modal.lbl_current_title.text())
        modal.close()

if __name__ == "__main__":
    unittest.main()

