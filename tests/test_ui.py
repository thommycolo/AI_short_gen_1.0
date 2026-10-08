"""AI Short Generator 1.0 - Full UI Modals & Drawers Instantiation Suite"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication

from app.core.script_manager import ScriptRepository
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.core.preset_manager import PresetManager
from app.core.bgm_manager import BgmManager
from app.core.cancellation_manager import ProductionCancellationManager
from app.core.pre_review_engine import StoryReviewItem

from app.ui.modals.script_input_modal import ScriptInputModal
from app.ui.modals.script_library_modal import ScriptLibraryModal
from app.ui.modals.video_download_modal import VideoDownloadModal
from app.ui.modals.video_pool_modal import VideoPoolModal
from app.ui.modals.batch_queue_modal import BatchQueueModal
from app.ui.modals.review_modal import PreProductionReviewModal
from app.ui.modals.progress_dialog import ProductionProgressDialog
from app.ui.modals.first_run_wizard import FirstRunWizardModal
from app.ui.modals.category_continuity_dialog import CategoryContinuityWarningDialog
from app.ui.drawers.voice_settings_drawer import VoiceSettingsDrawer
from app.ui.drawers.audio_settings_drawer import AudioSettingsDrawer
from app.ui.drawers.video_settings_drawer import VideoSettingsDrawer
from app.ui.drawers.subtitle_drawer import SubtitleDrawer
from app.ui.main_window import MainWindow


class TestUIComponents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

        test_db = str(ROOT_DIR / "app_data" / "test_ui.db")
        cls.repo = ScriptRepository(db_path=test_db)
        cls.video_mgr = ContinuousVideoPoolManager(db_path=test_db)
        cls.preset_mgr = PresetManager(db_path=test_db)
        cls.bgm_mgr = BgmManager(db_path=test_db)
        cls.cancel_mgr = ProductionCancellationManager(db_path=test_db)

    def test_modals_instantiation(self):
        m1 = ScriptInputModal(self.repo)
        self.assertIsNotNone(m1)

        m2 = ScriptLibraryModal(self.repo)
        self.assertIsNotNone(m2)

        m3 = VideoDownloadModal(self.video_mgr)
        self.assertIsNotNone(m3)

        m4 = VideoPoolModal(self.video_mgr)
        self.assertIsNotNone(m4)

        m5 = BatchQueueModal(self.repo, self.video_mgr)
        self.assertIsNotNone(m5)

        dummy_item = StoryReviewItem(
            story_id=1,
            context_title="Test_Story",
            text_preview="Preview...",
            word_count=50,
            est_audio_dur=20.0,
            est_video_dur=22.0,
            voice_profile="Ryan",
            voice_instruct="Viral",
            source_video_title="Master.mp4",
            video_time_interval="00:00-00:22",
            intro_banner_text="Test part.1",
            outro_cta_text="Subscribe!",
            bgm_title="BGM",
            font_name="Montserrat Black",
            composite_frame_path="",
            thumbnail_cover_path=""
        )
        m6 = PreProductionReviewModal([dummy_item])
        self.assertIsNotNone(m6)

        m7 = ProductionProgressDialog(self.cancel_mgr, total_stories=1)
        self.assertIsNotNone(m7)

        m8 = FirstRunWizardModal()
        self.assertIsNotNone(m8)
        if hasattr(m8, "worker") and m8.worker.isRunning():
            m8.worker.wait(1000)

        m9 = CategoryContinuityWarningDialog("Minecraft", 45.0, 20.0)
        self.assertIsNotNone(m9)

        print("[OK] All 9 Modals instantiated successfully.")

    def test_drawers_instantiation(self):
        d0 = VoiceSettingsDrawer(preset_mgr=self.preset_mgr)
        self.assertIsNotNone(d0)

        d1 = AudioSettingsDrawer(self.bgm_mgr)
        self.assertIsNotNone(d1)

        d2 = VideoSettingsDrawer()
        self.assertIsNotNone(d2)

        d3 = SubtitleDrawer(self.preset_mgr)
        self.assertIsNotNone(d3)
        print("[OK] All 4 Drawers instantiated successfully.")

    def test_main_window_instantiation(self):
        win = MainWindow()
        self.assertIsNotNone(win)
        print("[OK] MainWindow instantiated successfully.")

    def test_script_selector_card_clear_and_button_text(self):
        from app.ui.components.script_selector_card import ScriptSelectorCard
        card = ScriptSelectorCard()
        card.set_script({"id": 1, "context_title": "Test", "word_count": 20, "est_duration_sec": 8.0, "status": "DISPONIBILE"})
        self.assertFalse(card.btn_clear.isHidden())
        self.assertIn("Rimuovi", card.btn_clear.text())
        # Test that clear does not crash or recurse
        card.clear_script()
        self.assertIsNone(card.get_active_script())
        self.assertTrue(card.btn_clear.isHidden())
        print("[OK] ScriptSelectorCard clear and button text PASSED")

    def test_video_download_modal_default_category(self):
        m = VideoDownloadModal(self.video_mgr, default_category="Gaming")
        self.assertIsNotNone(m)
        self.assertTrue(hasattr(m, "default_category"))
        print("[OK] VideoDownloadModal default_category PASSED")

    def test_subtitle_drawer_custom_font_support(self):
        d = SubtitleDrawer(self.preset_mgr)
        self.assertTrue(hasattr(d, "btn_import_font"))
        self.assertGreater(d.cmb_font.count(), 0)
        print("[OK] SubtitleDrawer font import PASSED")

    def test_script_input_metrics_clean(self):
        m = ScriptInputModal(self.repo)
        m.text_edit.setPlainText("One two three four five six seven eight nine ten.")
        metrics_text = m.lbl_metrics.text()
        self.assertIn("Numero di parole: 10", metrics_text)
        self.assertIn("Stima durata voce:", metrics_text)
        self.assertIn("Numero stimato di clip video:", metrics_text)
        self.assertNotIn("Caratteri:", metrics_text)
        self.assertNotIn("DEFAULT_WPS", metrics_text)
        print("[OK] ScriptInputModal clean metrics PASSED")


if __name__ == "__main__":
    unittest.main()


