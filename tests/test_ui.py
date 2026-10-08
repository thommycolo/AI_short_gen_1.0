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
from app.ui.modals.clip_split_modal import ClipSplitAnalysisModal
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
            outro_cta_text="Follow for more!",
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

    def test_clip_split_modal_instantiation_and_recalc(self):
        from app.ui.modals.clip_split_modal import IntroOutroEditDialog, ClipCardWidget
        sample_script = {
            "id": 10,
            "context_title": "Test_Black_Holes",
            "raw_text": (
                "Black holes are fascinating celestial phenomena. "
                "Their gravity prevents light from escaping beyond the event horizon. "
                "However, astrophysics continues to study Hawking radiation and gravitational waves. "
                "Will future explorers ever penetrate their boundary? Only time will tell."
            ),
            "word_count": 35
        }
        modal = ClipSplitAnalysisModal(script_data=sample_script, script_repo=self.repo)
        self.assertIsNotNone(modal)
        self.assertGreater(len(modal.full_text), 10)
        self.assertGreater(modal.clips_layout.count(), 1) # Has clip cards + stretch

        # 1. Test altezza minima casella di testo (almeno 6 righe, >= 130px)
        first_card = modal.clips_layout.itemAt(0).widget()
        self.assertIsInstance(first_card, ClipCardWidget)
        self.assertGreaterEqual(first_card.txt_box.minimumHeight(), 130)

        # 2. Test modifica del titolo progetto
        modal.txt_project_title.setText("Space_BlackHoles_Custom")
        self.assertEqual(modal.get_context_title(), "Space_BlackHoles_Custom")

        # 3. Test spostamento autonomo frasi tra le clip
        modal._add_new_empty_clip()
        total_clips = len(modal.clip_texts)
        self.assertGreaterEqual(total_clips, 2)
        initial_first_len = len(modal.clip_texts[0].split())
        modal._move_last_sentence_down(1)
        # La prima clip deve aver ceduto la sua ultima frase alla seconda
        self.assertLess(len(modal.clip_texts[0].split()), initial_first_len)

        # 4. Test separazione Outro Intermedia vs Finale & Avviso in Rosso
        # Modifica solo l'intermedia: la finale deve mostrare avviso in rosso
        modal._on_apply_all_project({
            "is_final": False,
            "spoken": "Follow for part {next_part} right now!",
            "banner": "Follow part.{next_part} now!"
        })
        self.assertTrue(modal.intermediate_outro_modified)
        self.assertFalse(modal.final_outro_modified)

        # Ultima card deve avere show_red_warning = True (not isHidden)
        last_card = modal.clips_layout.itemAt(len(modal.clip_texts) - 1).widget()
        self.assertFalse(last_card.lbl_red_warning.isHidden())
        self.assertIn("Outro finale", last_card.lbl_red_warning.text())

        # Ora modifichiamo anche la finale: l'avviso in rosso deve sparire su entrambe
        modal._on_apply_all_project({
            "is_final": True,
            "spoken": "Follow for more cosmic mysteries!",
            "banner": "Follow for more mysteries!"
        })
        self.assertTrue(modal.intermediate_outro_modified)
        self.assertTrue(modal.final_outro_modified)
        last_card_after = modal.clips_layout.itemAt(len(modal.clip_texts) - 1).widget()
        self.assertTrue(last_card_after.lbl_red_warning.isHidden())

        # 5. Test IntroOutroEditDialog
        dlg = IntroOutroEditDialog(
            clip_idx=1,
            total_clips=2,
            is_final=False,
            intro_title="Test part.1",
            outro_spoken="Follow for part 2.",
            outro_banner="Follow for part.2"
        )
        self.assertIsNotNone(dlg)
        payload = dlg._get_current_payload()
        self.assertEqual(payload["intro"], "Test part.1")
        self.assertEqual(payload["spoken"], "Follow for part 2.")

        # Test preset application
        modal._apply_preset(30.0, 5.0, 2.65, 0.8, 0.8, 0.8)
        self.assertEqual(modal.target_video_max, 30.0)
        self.assertEqual(modal.allowed_delta, 5.0)
        self.assertEqual(modal.wps, 2.65)
        self.assertEqual(modal.padding_intro, 0.8)

        # Test timing config export
        cfg = modal.get_timing_config()
        self.assertEqual(cfg["target_video_max"], 30.0)
        self.assertEqual(cfg["allowed_delta_sec"], 5.0)
        self.assertEqual(cfg["wps"], 2.65)
        self.assertEqual(cfg["padding_intro_sec"], 0.8)
        self.assertIn("custom_chunks", cfg)
        self.assertIn("custom_intros", cfg)
        self.assertIn("custom_outros", cfg)
        print("[OK] ClipSplitAnalysisModal all requirements & tests PASSED")

    def test_script_selector_card_clip_split_button(self):
        from app.ui.components.script_selector_card import ScriptSelectorCard
        card = ScriptSelectorCard()
        self.assertIsNotNone(card.btn_clip_split)
        self.assertIn("Suddivisione", card.btn_clip_split.text())
        self.assertIsNotNone(card.btn_mini_split)

        # Test signal emission
        emitted = []
        card.clip_split_requested.connect(lambda: emitted.append(True))
        card.btn_clip_split.click()
        self.assertTrue(len(emitted) > 0)
        print("[OK] ScriptSelectorCard clip split button and signal PASSED")

    def test_clip_split_updates_home_page_metrics(self):
        """Verifica che le modifiche apportate nel ClipSplitModal si riflettano fedelmente nella home page."""
        from app.ui.main_window import MainWindow
        from app.ui.modals.clip_split_modal import ClipSplitAnalysisModal

        win = MainWindow()
        sample_script = {
            "id": 99,
            "context_title": "Original_Project_Title",
            "raw_text": "Sentence one is here. Sentence two follows it. Sentence three closes.",
            "word_count": 11,
            "est_duration_sec": 4.4,
            "status": "DISPONIBILE"
        }
        win.set_active_script(sample_script)

        modal = ClipSplitAnalysisModal(
            script_data=sample_script,
            current_timing=win.active_timing_config,
            script_repo=win.script_repo
        )
        # Modifica il titolo del progetto
        modal.txt_project_title.setText("New_Updated_Title")
        # Aggiungi una clip per forzare la suddivisione
        modal._add_new_empty_clip()
        self.assertGreaterEqual(len(modal.clip_texts), 2)

        # Applica i risultati
        stats = modal.get_summary_stats()
        cfg = modal.get_timing_config()
        win._apply_clip_split_results(stats, cfg)

        # Controlla l'aggiornamento sulla home page (card_script)
        self.assertIn("New_Updated_Title", win.card_script.lbl_title.text())
        metrics_text = win.card_script.lbl_metrics.text()
        self.assertIn(f"{len(modal.clip_texts)} Clip Short", metrics_text)
        self.assertIn(f"{stats['word_count']} Words", metrics_text)
        self.assertEqual(win.active_timing_config["num_clips"], len(modal.clip_texts))
        print("[OK] test_clip_split_updates_home_page_metrics PASSED")

    def test_session_persistence_and_empty_after_render(self):
        """Verifica persistenza della sessione e stato vuoto all'avvio successivo a un render."""
        import os
        from app.config import SESSION_STATE_PATH
        from app.ui.main_window import MainWindow

        win1 = MainWindow()
        test_script = {
            "id": 105,
            "context_title": "Project_In_Progress",
            "raw_text": "This is a great story about deep universe stars.",
            "word_count": 9,
            "est_duration_sec": 3.6,
            "status": "DISPONIBILE",
            "custom_chunks": ["This is a great story", "about deep universe stars."],
            "num_clips": 2
        }
        win1.set_active_script(test_script)
        win1.active_timing_config["custom_chunks"] = test_script["custom_chunks"]
        win1.active_timing_config["num_clips"] = 2
        win1.card_script.update_metrics(num_clips=2, total_duration_sec=35.0, word_count=9)
        win1._save_session_state()

        self.assertTrue(os.path.exists(SESSION_STATE_PATH))

        # Riapertura dell'app con progetto in sospeso: deve ripristinare il progetto da dove era rimasto
        win2 = MainWindow()
        self.assertIsNotNone(win2.active_script_data)
        self.assertEqual(win2.active_script_data.get("context_title"), "Project_In_Progress")
        self.assertIn("Project_In_Progress", win2.card_script.lbl_title.text())
        self.assertIn("2 Clip Short", win2.card_script.lbl_metrics.text())

        # Simulazione render completato con successo
        win2._on_worker_completed(["dummy_output.mp4"])
        # Subito dopo il render, il progetto deve risultare vuoto
        self.assertIsNone(win2.active_script_data)
        self.assertIn("Nessun testo selezionato", win2.card_script.lbl_title.text())
        self.assertIn("0 Clip Short", win2.card_script.lbl_metrics.text())

        # Riapertura dell'app dopo il render: deve risultare vuoto senza nulla di pre-caricato
        win3 = MainWindow()
        self.assertIsNone(win3.active_script_data)
        self.assertIn("Nessun testo selezionato", win3.card_script.lbl_title.text())
        self.assertIn("0 Clip Short", win3.card_script.lbl_metrics.text())
        print("[OK] test_session_persistence_and_empty_after_render PASSED")


if __name__ == "__main__":
    unittest.main()



