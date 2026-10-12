"""AI Short Generator 1.0 - Unit Tests for Video Pool, Category Flags & Subfolders, Playback and Deletion"""

import os
import sys
import shutil
import sqlite3
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from app.config import APP_DATA_DIR, CATEGORIES
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.core.batch_allocator import StoryRequirement, VideoSourceCandidate, ContinuousBatchFeasibilitySolver
from app.ui.modals.video_download_modal import VideoDownloadModal
from app.ui.modals.video_pool_modal import VideoPoolModal
from app.ui.modals.video_playback_modal import VideoPlaybackModal
from app.ui.modals.category_continuity_dialog import CategoryContinuityWarningDialog
from app.ui.components.video_source_card import VideoSourceCard
from app.ui.components.voice_selector import VoiceSelectorCard
from app.ui.drawers.voice_settings_drawer import VoiceSettingsDrawer
from app.ui.modals.progress_dialog import ProductionProgressDialog
from app.core.vram_orchestrator import ProductionCancellationManager
from app.utils.ffmpeg_installer import find_system_ffmpeg


class TestVideoPoolAndCategories(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.test_dir = APP_DATA_DIR / "test_pool_suite"
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.test_db = str(cls.test_dir / "test_pool.db")
        cls.clips_dir = cls.test_dir / "videos"
        cls.clips_dir.mkdir(parents=True, exist_ok=True)
        cls.video_mgr = ContinuousVideoPoolManager(db_path=cls.test_db, clips_dir=cls.clips_dir)

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_category_subfolders_creation(self):
        """Verifica che ogni categoria crei una sottocartella fisica con il suo nome."""
        cat_name = "Satisfying"
        cat_dir = self.video_mgr.ensure_category_dir(cat_name)
        self.assertTrue(cat_dir.exists())
        self.assertTrue(cat_dir.is_dir())
        self.assertEqual(cat_dir.name, cat_name)

        # Test categoria personalizzata con caratteri sicuri
        custom_cat = "Test Category 123"
        custom_dir = self.video_mgr.ensure_category_dir(custom_cat)
        self.assertTrue(custom_dir.exists())
        self.assertEqual(custom_dir.name, custom_cat)

    def test_02_available_categories_dynamic(self):
        """Verifica che get_available_categories raccolga categorie da config, cartelle e db."""
        self.video_mgr.ensure_category_dir("CustomPhysics")
        cats = self.video_mgr.get_available_categories()
        self.assertIn("Minecraft", cats)
        self.assertIn("CustomPhysics", cats)

    def test_03_no_automatic_classification(self):
        """Verifica che l'auto-categorizzazione sia rimossa: non c'è classify_category."""
        self.assertFalse(hasattr(self.video_mgr, "classify_category"))

    def test_04_local_import_removed_from_ui(self):
        """Verifica che 'Importa Locale' sia rimosso da VideoSourceCard, VideoDownloadModal e CategoryContinuityDialog."""
        card = VideoSourceCard()
        self.assertFalse(hasattr(card, "btn_local"))
        self.assertFalse(hasattr(card, "import_local_requested"))

        dl_modal = VideoDownloadModal(self.video_mgr)
        self.assertFalse(hasattr(dl_modal, "btn_local_file"))
        self.assertFalse(hasattr(dl_modal, "_import_local_files"))
        # Verifica presenza del pulsante Nuova Categoria
        self.assertTrue(hasattr(dl_modal, "btn_add_category"))
        # Verifica assenza di "Auto-Rileva Categoria"
        for i in range(dl_modal.combo_cat.count()):
            self.assertNotIn("Auto", dl_modal.combo_cat.itemText(i))

        diag = CategoryContinuityWarningDialog("Minecraft", 45.0, 10.0)
        self.assertFalse(hasattr(diag, "btn_local"))
        self.assertFalse(hasattr(diag, "ACTION_IMPORT_LOCAL"))

    def test_05_video_deletion_and_disk_cleanup(self):
        """Verifica che l'eliminazione dal pool cancelli record nel DB e file sul disco."""
        cat_dir = self.video_mgr.ensure_category_dir("Minecraft")
        dummy_file = cat_dir / "dummy_video_del.mp4"
        dummy_file.write_text("dummy content")

        with sqlite3.connect(self.test_db) as conn:
            cur = conn.execute("""
                INSERT INTO video_sources (
                    source_type, source_uri, video_title, category,
                    total_duration_sec, frontier_playhead_sec, available_duration_sec,
                    file_path, status
                ) VALUES ('YOUTUBE', 'https://youtu.be/dummy', 'Dummy To Delete', 'Minecraft',
                          60.0, 0.0, 60.0, ?, 'DISPONIBILE')
            """, (str(dummy_file.resolve()),))
            source_id = cur.lastrowid

        self.assertTrue(dummy_file.exists())

        # Elimina tramite manager
        success = self.video_mgr.delete_source(source_id, delete_file=True)
        self.assertTrue(success)

        # File su disco rimosso
        self.assertFalse(dummy_file.exists())

        # Record nel DB rimosso
        with sqlite3.connect(self.test_db) as conn:
            row = conn.execute("SELECT id FROM video_sources WHERE id = ?", (source_id,)).fetchone()
            self.assertIsNone(row)

    def test_06_video_playback_modal_instantiation(self):
        """Verifica che VideoPlaybackModal si istanzi correttamente con controlli e player."""
        cat_dir = self.video_mgr.ensure_category_dir("GTA V")
        test_video = cat_dir / "test_play.mp4"
        test_video.write_bytes(b"\x00" * 1024)

        modal = VideoPlaybackModal(str(test_video), video_title="GTA Test", parent=None)
        self.assertIsNotNone(modal.player)
        self.assertIsNotNone(modal.video_widget)
        self.assertIsNotNone(modal.slider_pos)
        self.assertIsNotNone(modal.btn_play)
        self.assertIsNotNone(modal.btn_external)
        modal.close()

    def test_07_strict_category_selection_in_clip_generation(self):
        """Verifica che la selezione automatica video per clip series rispetti rigorosamente la categoria scelta."""
        pool_candidates = [
            VideoSourceCandidate(
                source_id=1,
                title="Minecraft Parkour Master",
                category="Minecraft",
                available_duration_sec=120.0,
                current_playhead_sec=0.0
            ),
            VideoSourceCandidate(
                source_id=2,
                title="Subway Surfers Master",
                category="Subway Surfers",
                available_duration_sec=120.0,
                current_playhead_sec=0.0
            )
        ]

        # Storia con categoria "Minecraft"
        story_mc = StoryRequirement(
            script_id=10,
            context_title="Minecraft Story Series",
            num_parts=2,
            base_duration_sec=38.0,
            speed_rate=1.0,
            category="Minecraft"
        )

        report = ContinuousBatchFeasibilitySolver.solve([story_mc], pool_candidates)
        self.assertTrue(report.is_feasible)
        self.assertEqual(len(report.plans), 1)
        # Deve essere assegnato il video di Minecraft (id: 1)
        self.assertEqual(report.plans[0].assigned_source_id, 1)
        self.assertEqual(report.plans[0].category, "Minecraft")

        # Storia con categoria "Subway Surfers"
        story_ss = StoryRequirement(
            script_id=20,
            context_title="Subway Story Series",
            num_parts=2,
            base_duration_sec=38.0,
            speed_rate=1.0,
            category="Subway Surfers"
        )

        report_ss = ContinuousBatchFeasibilitySolver.solve([story_ss], pool_candidates)
        self.assertTrue(report_ss.is_feasible)
        self.assertEqual(len(report_ss.plans), 1)
        # Deve essere assegnato il video di Subway Surfers (id: 2)
        self.assertEqual(report_ss.plans[0].assigned_source_id, 2)
        self.assertEqual(report_ss.plans[0].category, "Subway Surfers")

    def test_08_mute_video_file(self):
        """Verifica che mute_video_file rimuova l'audio da un file MP4 a ricodifica zero."""
        # Test file inesistente
        self.assertFalse(ContinuousVideoPoolManager.mute_video_file("non_existent_file.mp4"))

        # Test con video reale generato con FFmpeg se disponibile
        ffmpeg_bin, _ = find_system_ffmpeg()
        if ffmpeg_bin:
            import subprocess
            cat_dir = self.video_mgr.ensure_category_dir("General")
            test_raw = cat_dir / "test_with_audio.mp4"
            # Genera 1 secondo di video con traccia audio
            cmd_gen = [
                ffmpeg_bin, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=10",
                "-f", "lavfi", "-i", "sine=duration=1:frequency=440",
                "-c:v", "libx264", "-c:a", "aac",
                str(test_raw)
            ]
            res = subprocess.run(cmd_gen, capture_output=True, text=True)
            if res.returncode == 0 and test_raw.exists():
                success = ContinuousVideoPoolManager.mute_video_file(str(test_raw))
                self.assertTrue(success)
                self.assertTrue(test_raw.exists())
                test_raw.unlink(missing_ok=True)

    def test_09_ui_clean_titles_no_link_no_id_no_gemini_tts(self):
        """Verifica rimozione scritte (Link), (Download da link), (Gemini TTS), scroll orizzontale e ID nel titolo."""
        # 1. VideoSourceCard: no (Link), no (Download da link)
        v_card = VideoSourceCard()
        self.assertNotIn("(Link)", v_card.btn_yt.text())
        self.assertEqual(v_card.btn_yt.text(), "⬇️ Scarica Video")
        header = v_card.findChild(QLabel, "SectionHeader")
        self.assertIsNotNone(header)
        self.assertEqual(header.text(), "3. BACKGROUND VIDEO POOL")
        self.assertNotIn("(Download da link)", header.text())
        self.assertFalse(hasattr(v_card, "combo_alloc"))
        self.assertNotIn("Assegnazione:", [lbl.text() for lbl in v_card.findChildren(QLabel)])

        # 2. VoiceSelectorCard: no (Gemini TTS), no slot lingua
        voice_card = VoiceSelectorCard()
        v_header = voice_card.findChild(QLabel, "SectionHeader")
        self.assertIsNotNone(v_header)
        self.assertEqual(v_header.text(), "2. GENERATORE VOCALE")
        self.assertNotIn("Gemini TTS", v_header.text())
        self.assertFalse(hasattr(voice_card, "combo_lang"))
        self.assertNotIn("Lingua:", [lbl.text() for lbl in voice_card.findChildren(QLabel)])

        # 3. VoiceSettingsDrawer: no (Gemini TTS)
        drawer = VoiceSettingsDrawer()
        self.assertNotIn("Gemini TTS", drawer.windowTitle())
        self.assertEqual(drawer.windowTitle(), "VOICE STUDIO & IMPOSTAZIONI SINTESI VOCALE")
        drawer.close()

        # 4. VideoPoolModal: scroll orizzontale rimosso, titolo tranciato e nessun ID visibile
        pool_modal = VideoPoolModal(self.video_mgr, required_duration_sec=30.0)
        self.assertEqual(pool_modal.scroll.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOff)

        long_title = "QuestoEUnTitoloMoltoLungoPerTestareIlTroncamentoDelTitoloNelVideoPool"
        sample_src = {
            "id": 999,
            "video_title": long_title,
            "category": "Minecraft",
            "total_duration_sec": 120.0,
            "available_duration_sec": 120.0,
            "frontier_playhead_sec": 0.0,
            "file_path": "dummy.mp4"
        }
        card_widget = pool_modal._create_source_card(sample_src)
        title_labels = [lbl for lbl in card_widget.findChildren(QLabel) if "🎬" in lbl.text()]
        self.assertEqual(len(title_labels), 1)
        displayed_title = title_labels[0].text()
        self.assertNotIn("999", displayed_title)
        self.assertNotIn("ID:", displayed_title)
        self.assertTrue(displayed_title.endswith('..."'))
        self.assertEqual(title_labels[0].toolTip(), long_title)
        pool_modal.close()

        # 5. ProductionProgressDialog: no 'Gemini TTS' nel nome fase
        prog_diag = ProductionProgressDialog(cancellation_mgr=ProductionCancellationManager(), total_stories=1)
        prog_diag.update_active_phase(0, 20.0)
        self.assertNotIn("Gemini TTS", prog_diag.lbl_console.text())
        self.assertIn("Sintesi Vocale", prog_diag.lbl_console.text())
        prog_diag.close()

    def test_10_category_selection_displays_video_or_warning(self):
        """Verifica che la selezione categoria mostri il titolo del video se presente o la scritta '- Nessun Video disponibile -' se vuota."""
        v_card = VideoSourceCard()

        # 1. Categoria vuota -> compare '- Nessun Video disponibile -'
        v_card.show_no_video_warning("EmptyCat")
        self.assertEqual(v_card.lbl_active_video.text(), "- Nessun Video disponibile -")
        self.assertIn("EmptyCat", v_card.lbl_avail_dur.text())
        self.assertEqual(v_card.badge_status.text(), "Nessun Video ⚠️")
        self.assertEqual(v_card.badge_status.objectName(), "BadgeWarning")

        # 2. Categoria con video -> titolo video mostrato nella barra
        v_card.update_video_info(title="Minecraft_Parkour_Test_Video", duration_str="08m 45s disponibili", has_video=True)
        self.assertIn("Minecraft_Parkour_Test_Video", v_card.lbl_active_video.text())
        self.assertEqual(v_card.badge_status.text(), "Video Pronto 🟢")
        self.assertEqual(v_card.badge_status.objectName(), "BadgeAvailable")

        # 3. get_pool_status_for_category su categoria senza video
        empty_status = self.video_mgr.get_pool_status_for_category("NonExistentCategory")
        self.assertEqual(empty_status["source_count"], 0)
        self.assertEqual(empty_status["total_available_sec"], 0.0)

        # 4. Inserimento video e query get_pool_status_for_category
        cat_dir = self.video_mgr.ensure_category_dir("Satisfying")
        dummy_f = cat_dir / "sat_vid.mp4"
        dummy_f.write_text("dummy")
        with sqlite3.connect(self.test_db) as conn:
            conn.execute("""
                INSERT INTO video_sources (
                    source_type, source_uri, video_title, category,
                    total_duration_sec, frontier_playhead_sec, available_duration_sec,
                    file_path, status
                ) VALUES ('LOCAL_FILE', 'local', 'Satisfying Soap Cutting', 'Satisfying', 90.0, 10.0, 80.0, ?, 'DISPONIBILE')
            """, (str(dummy_f.resolve()),))

        sat_status = self.video_mgr.get_pool_status_for_category("Satisfying")
        self.assertGreaterEqual(sat_status["source_count"], 1)
        self.assertEqual(sat_status["best_video_title"], "Satisfying Soap Cutting")
        self.assertEqual(sat_status["best_frontier_sec"], 10.0)
        self.assertEqual(sat_status["best_available_sec"], 80.0)

    def test_11_video_pool_modal_category_filter_and_selection_sync(self):
        """Verifica il filtro categorie nella scheda pool e la sincronizzazione della categoria con la Home Page."""
        from app.ui.main_window import MainWindow

        # 1. Istanza di VideoPoolModal con filtro categoria
        modal = VideoPoolModal(self.video_mgr, active_category="Minecraft", required_duration_sec=30.0)
        self.assertTrue(hasattr(modal, "combo_filter_category"))

        # Filtro per categoria specifica 'Satisfying'
        idx = modal.combo_filter_category.findData("Satisfying")
        self.assertGreaterEqual(idx, 0)
        modal.combo_filter_category.setCurrentIndex(idx)
        self.assertEqual(modal.combo_filter_category.currentData(), "Satisfying")

        # Filtro per 'Tutte le categorie'
        modal.combo_filter_category.setCurrentIndex(0)
        self.assertEqual(modal.combo_filter_category.currentData(), "")

        # 2. Selezione di un video appartenente a categoria diversa ('Satisfying')
        sat_src = self.video_mgr.get_sources(category="Satisfying", available_only=False)[0]
        from unittest.mock import patch
        with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
            modal._on_select_source(sat_src)
            # Nessun popup informativo mostrato (come richiesto)
            mock_info.assert_not_called()

        self.assertEqual(modal.selected_category, "Satisfying")
        self.assertEqual(modal.selected_source_id, sat_src["id"])
        self.assertEqual(modal.active_category, "Satisfying")

        # Verifica presenza icona/badge SELEZIONATO sulla card
        card_widget = modal._create_source_card(sat_src)
        badges = [lbl.text() for lbl in card_widget.findChildren(QLabel)]
        self.assertIn("✅ SELEZIONATO", badges)
        btn_sel = [b for b in card_widget.findChildren(QPushButton) if "ATTIVO" in b.text()]
        self.assertEqual(len(btn_sel), 1)
        self.assertEqual(btn_sel[0].text(), "✅ ATTIVO")
        modal.close()

        # 3. Test sincronizzazione con MainWindow
        win = MainWindow()
        win.active_video_category = "Minecraft"
        self.assertEqual(win.active_video_category, "Minecraft")

        # Applica selezione video di 'Satisfying'
        win._apply_pool_video_selection(sat_src)
        self.assertEqual(win.active_video_category, "Satisfying")
        self.assertEqual(win.card_video.get_selected_category(), "Satisfying")
        self.assertIn("Satisfying Soap Cutting", win.card_video.lbl_active_video.text())
        win.close()

    def test_12_home_category_change_auto_assigns_and_displays_video(self):
        """Verifica che cambiando categoria nella Home Page zona 3, il video venga selezionato con criteri auto-assegnazione."""
        from app.ui.main_window import MainWindow

        win = MainWindow()
        win.video_pool = self.video_mgr
        win.card_video.set_categories(self.video_mgr.get_available_categories(), current="Satisfying")
        # Imposta categoria Satisfying nella Home Page
        win.card_video.combo_category.setCurrentText("Satisfying")
        win._on_video_category_changed("Satisfying")

        # Il video deve essere selezionato in preferred_video_source_id
        self.assertIsNotNone(win.preferred_video_source_id)
        # Il titolo deve comparire nella barra sotto la scelta della categoria
        bar_text = win.card_video.lbl_active_video.text()
        self.assertIn("Satisfying Soap Cutting", bar_text)
        self.assertNotIn("- Nessun Video disponibile -", bar_text)

        # Se passiamo a una categoria vuota
        win.card_video.combo_category.setCurrentText("General")
        win._on_video_category_changed("General")
        # In assenza di video deve comparire l'avviso
        if win.video_pool.get_pool_status_for_category("General")["source_count"] == 0:
            self.assertEqual(win.card_video.lbl_active_video.text(), "- Nessun Video disponibile -")
            self.assertIsNone(win.preferred_video_source_id)

        win.close()


if __name__ == "__main__":
    unittest.main()

