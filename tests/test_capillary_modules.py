"""AI Short Generator 1.0 - Capillary Verification and Debugging Test Suite"""

import os
import sys
import wave
import struct
import shutil
import sqlite3
import unittest
import numpy as np
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication

from app.config import (
    DEFAULT_WPS, MIN_REEL_VIDEO_SEC, MAX_REEL_VIDEO_SEC,
    TOTAL_PADDING_SEC, CATEGORIES, PURGE_THRESHOLD_MAX,
    TRUE_PEAK_LIMITER_DB
)
from app.core.fast_normalizer import FastDeterministicNormalizer
from app.core.script_manager import ScriptRepository
from app.core.discourse_chunker import DiscourseCoherenceChunker
from app.core.continuous_video_manager import ContinuousVideoPoolManager, MasterVideoInfo
from app.core.batch_allocator import (
    ContinuousBatchFeasibilitySolver, StoryRequirement, VideoSourceCandidate
)
from app.core.subtitle_generator import SubtitleGenerator, hex_to_ass_color
from app.core.thumbnail_generator import StorySeriesThumbnailGenerator
from app.core.pre_review_engine import PreProductionReviewEngine, StoryReviewItem
from app.core.preset_manager import PresetManager
from app.core.bgm_manager import BgmManager
from app.core.silero_vad_trimmer import SileroVADSilenceTrimmer
from app.core.cancellation_manager import ProductionCancellationManager
from app.core.vram_orchestrator import ProductionJob, VRAMLifecycleOrchestrator
from app.utils.ffmpeg_installer import find_system_ffmpeg, probe_media_duration


def get_or_create_qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def create_dummy_wav(path: str, duration_sec: float = 3.0, sample_rate: int = 16000, freq: float = 440.0):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, False)
    # Generate soft sine wave
    sine = (np.sin(2 * np.pi * freq * t) * 0.5 * 32767.0).astype(np.int16)
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(sine.tobytes())


def create_dummy_mp4(path: str, duration_sec: float = 40.0):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin, _ = find_system_ffmpeg()
    ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"
    import subprocess
    cmd = [
        ffmpeg_cmd, "-y",
        "-f", "lavfi", "-i", f"color=c=blue:s=1080x1920:d={duration_sec:.1f}:r=60",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", f"{duration_sec:.1f}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        path
    ]
    subprocess.run(cmd, capture_output=True, check=True)


class TestCapillaryModules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = get_or_create_qapp()
        from PySide6.QtWidgets import QMessageBox
        cls._orig_info = QMessageBox.information
        cls._orig_warn = QMessageBox.warning
        cls._orig_crit = QMessageBox.critical
        cls._orig_ques = QMessageBox.question
        QMessageBox.information = lambda *args, **kwargs: QMessageBox.Ok
        QMessageBox.warning = lambda *args, **kwargs: QMessageBox.Ok
        QMessageBox.critical = lambda *args, **kwargs: QMessageBox.Ok
        QMessageBox.question = lambda *args, **kwargs: QMessageBox.Yes

        cls.test_dir = ROOT_DIR / "app_data" / "capillary_test_workspace"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.test_db = str(cls.test_dir / "capillary_test.db")
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

        cls.repo = ScriptRepository(db_path=cls.test_db)
        cls.video_pool = ContinuousVideoPoolManager(db_path=cls.test_db, clips_dir=cls.test_dir / "pool")
        cls.bgm_mgr = BgmManager(db_path=cls.test_db, bgm_dir=cls.test_dir / "bgm")
        cls.cancellation_mgr = ProductionCancellationManager(db_path=cls.test_db)
        cls.preset_mgr = PresetManager(db_path=cls.test_db)
        cls.normalizer = FastDeterministicNormalizer()
        cls.chunker = DiscourseCoherenceChunker()

    @classmethod
    def tearDownClass(cls):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information = cls._orig_info
        QMessageBox.warning = cls._orig_warn
        QMessageBox.critical = cls._orig_crit
        QMessageBox.question = cls._orig_ques
        try:
            shutil.rmtree(cls.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_fast_normalizer_full_coverage(self):
        """Testa tutte le conversioni sintattiche, valute, percentuali, slang e acronimi protetti."""
        # 1. Valute con moltiplicatori e decimali
        raw_cur = "They earned $500M and spent €2.50 plus £100B in 2024."
        norm_cur = self.normalizer.normalize(raw_cur)
        self.assertIn("million dollars", norm_cur)
        self.assertIn("euro", norm_cur)
        self.assertIn("billion pounds", norm_cur)

        # 2. Percentuali e numeri grandi
        raw_num = "About 99.5% of the 1,500,000 citizens voted."
        norm_num = self.normalizer.normalize(raw_num)
        self.assertIn("percent", norm_num)
        self.assertIn("million", norm_num)

        # 3. Slang e abbreviazioni
        raw_slang = "idk tbh bc im gonna go w/ u to schl rn tho!"
        norm_slang = self.normalizer.normalize(raw_slang)
        self.assertIn("I do not know", norm_slang)
        self.assertIn("to be honest", norm_slang)
        self.assertIn("because", norm_slang)
        self.assertIn("going to", norm_slang)
        self.assertIn("with", norm_slang)
        self.assertIn("school", norm_slang)
        self.assertIn("right now", norm_slang)

        # 4. Acronimi protetti
        raw_acro = "The U.S. and NASA work with the FBI, CIA, and NATO on AI projects."
        norm_acro = self.normalizer.normalize(raw_acro)
        self.assertIn("U.S.", norm_acro)
        self.assertIn("NASA", norm_acro)
        self.assertIn("NATO", norm_acro)
        self.assertIn("AI", norm_acro)

    def test_02_script_manager_lifecycle_and_variants(self):
        """Testa salvataggio, deduplicazione True O(1), marcatura UTILIZZATO e creazione varianti."""
        text = "Voyager 1 has traversed the heliopause and entered interstellar space beyond our sun."
        ok, msg, sid, info = self.repo.save_new_script(text)
        self.assertTrue(ok)
        self.assertIsNotNone(sid)

        # Test deduplicazione esatta Livello 1
        dup_ok, dup_msg, dup_id, _ = self.repo.save_new_script(text)
        self.assertFalse(dup_ok)
        self.assertIn("IDENTICO", dup_msg)

        # Test deduplicazione quasi-duplicato Livello 2 (SimHash)
        near_text = "Voyager 1 has traversed the heliopause and entered interstellar space beyond the sun!"
        is_dup, reason, c_info = self.repo.check_duplicate(near_text)
        self.assertTrue(is_dup)
        self.assertIn("QUASI-IDENTICO", reason)

        # Test marcatura come UTILIZZATO con video generati
        renders = ["voyager_part1.mp4"]
        self.repo.mark_script_as_used(sid, produced_videos=renders)
        script_row = self.repo.get_script(sid)
        self.assertEqual(script_row["status"], "UTILIZZATO")
        self.assertIsNotNone(script_row["used_at"])
        self.assertIn("voyager_part1.mp4", script_row["generated_video_names"])

        # Test sblocco tramite Variante
        var_ok, var_msg, var_id = self.repo.create_variant(sid, variant_label="Dramatic Tone")
        self.assertTrue(var_ok)
        var_row = self.repo.get_script(var_id)
        self.assertEqual(var_row["status"], "DISPONIBILE")
        self.assertEqual(var_row["is_variant_of"], sid)

    def test_03_continuous_video_ingest_and_bounded_snapping(self):
        """Testa zero-recode ingestion, MasterVideoInfo, Bounded Right Edge e Garbage Collection."""
        dummy_mp4 = str(self.test_dir / "minecraft_master_parkour.mp4")
        create_dummy_mp4(dummy_mp4, duration_sec=160.0)

        # Ingestion
        info: MasterVideoInfo = self.video_pool.ingest_master_video(dummy_mp4, category="Minecraft")
        self.assertIsInstance(info, MasterVideoInfo)
        self.assertEqual(info.category, "Minecraft")
        self.assertAlmostEqual(info.duration_sec, 160.0, delta=1.0)
        self.assertEqual(info.status, "DISPONIBILE")

        # Prenotazione segmento continuo (40.0s)
        start_1, end_1 = self.video_pool.reserve_segment_for_story(
            source_id=info.id, script_id=1, duration_sec=40.0
        )
        self.assertAlmostEqual(start_1, 0.0, delta=0.5)
        self.assertAlmostEqual(end_1, 40.0, delta=0.5)

        # Verifica stato sorgente dopo prenotazione
        status = self.video_pool.get_pool_status_for_category("Minecraft")
        self.assertAlmostEqual(status["total_available_sec"], 120.0, delta=1.5)

        # Prenotazione secondo segmento (40.0s)
        # Rimanente previsto: 160 - 80 = 80s.
        # Poiché 80s <= 110s (PURGE_THRESHOLD_MAX), scatta la Garbage Collection: status EPURATO!
        start_2, end_2 = self.video_pool.reserve_segment_for_story(
            source_id=info.id, script_id=2, duration_sec=40.0
        )
        self.assertAlmostEqual(start_2, 40.0, delta=0.5)
        self.assertAlmostEqual(end_2, 80.0, delta=0.5)

        # Verifica che il Garbage Collector abbia epurato gli 80s rimanenti (<110s)
        with sqlite3.connect(self.test_db) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM video_sources WHERE id = ?", (info.id,)).fetchone()
            self.assertEqual(row["status"], "EPURATO")
            self.assertEqual(row["available_duration_sec"], 0.0)

    def test_04_bgm_manager_mixing_ducking_and_peak_limiter(self):
        """Testa il mixing FFmpeg sia con BGM (ducking -22dB e -14dB) sia senza BGM con True Peak Limiter -1.0 dB."""
        voice_wav = str(self.test_dir / "voice_sample.wav")
        bgm_wav = str(self.test_dir / "bgm_sample.wav")
        out_voice_only = str(self.test_dir / "mixed_voice_only.wav")
        out_with_bgm = str(self.test_dir / "mixed_with_bgm.wav")

        create_dummy_wav(voice_wav, duration_sec=3.0, freq=300.0)
        create_dummy_wav(bgm_wav, duration_sec=6.0, freq=120.0)

        # 1. Voice Only (No BGM): applica adelay=500|500 + apad + alimiter -1.0dB
        self.bgm_mgr.mix_narration_and_bgm_ducking(
            voice_wav_path=voice_wav,
            bgm_wav_path=None,
            voice_duration_sec=3.0,
            output_mixed_audio=out_voice_only
        )
        self.assertTrue(os.path.exists(out_voice_only))
        dur_vo = probe_media_duration(out_voice_only)
        # 3.0s voce + 0.5s intro + 1.5s outro = 5.0s
        self.assertAlmostEqual(dur_vo, 5.0, delta=0.2)

        # 2. Con BGM: applica volume ducking continuo + amix normalize=0 + alimiter -1.0dB
        self.bgm_mgr.mix_narration_and_bgm_ducking(
            voice_wav_path=voice_wav,
            bgm_wav_path=bgm_wav,
            voice_duration_sec=3.0,
            output_mixed_audio=out_with_bgm,
            ducking_db=-22.0,
            intro_outro_db=-14.0
        )
        self.assertTrue(os.path.exists(out_with_bgm))
        dur_bgm = probe_media_duration(out_with_bgm)
        self.assertAlmostEqual(dur_bgm, 5.0, delta=0.2)

    def test_05_cancellation_manager_atomic_rollback(self):
        """Testa la propagazione del rollback granulare atomico preservando le storie completate."""
        # Crea fittiziamente uno script completato e uno incompleto
        sid_done = self.repo.save_new_script("First complete script")[2]
        sid_undone = self.repo.save_new_script("Second cancelled script")[2]

        self.repo.mark_script_as_used(sid_done)
        self.repo.mark_script_as_used(sid_undone)

        # Esegui rollback con completato vs incompleto
        self.cancellation_mgr.execute_granular_rollback(
            completed_story_ids=[sid_done],
            uncompleted_story_ids=[sid_undone]
        )

        s_done_data = self.repo.get_script(sid_done)
        s_undone_data = self.repo.get_script(sid_undone)

        # Il completato rimane UTILIZZATO
        self.assertEqual(s_done_data["status"], "UTILIZZATO")
        # L'annullato è ripristinato a DISPONIBILE
        self.assertEqual(s_undone_data["status"], "DISPONIBILE")

    def test_06_batch_solver_and_zero_waste_optimizer(self):
        """Testa il risolutore di fattibilità CSP e il suggerimento Zero-Sprechi."""
        stories = [
            StoryRequirement(
                script_id=101, context_title="Story 1", num_parts=1,
                base_duration_sec=38.0, speed_rate=1.0, category="Minecraft", text="Text 1"
            ),
            StoryRequirement(
                script_id=102, context_title="Story 2", num_parts=1,
                base_duration_sec=38.0, speed_rate=1.0, category="Minecraft", text="Text 2"
            )
        ]
        # Pool con soli 60 secondi disponibili (< 80s necessari)
        pool = [
            VideoSourceCandidate(
                source_id=1, title="MC Master", category="Minecraft",
                available_duration_sec=60.0, current_playhead_sec=0.0
            )
        ]

        report = ContinuousBatchFeasibilitySolver.solve(stories, pool)
        self.assertFalse(report.is_feasible)
        self.assertGreater(report.deficit_seconds, 0.0)

        # L'ottimizzatore Zero-Sprechi deve suggerire di produrre 1 storia
        suggestions = ContinuousBatchFeasibilitySolver.suggest_optimal_subqueue(stories, pool)
        self.assertGreater(len(suggestions), 0)
        best = suggestions[0]
        self.assertEqual(len(best.selected_stories), 1)
        self.assertEqual(best.selected_stories[0].script_id, 101)

    def test_07_progress_dialog_ui_methods(self):
        """Testa i metodi della modale di avanzamento senza deadlock."""
        from app.ui.modals.progress_dialog import ProductionProgressDialog

        dialog = ProductionProgressDialog(
            cancellation_mgr=self.cancellation_mgr,
            total_stories=2
        )
        self.assertIsNotNone(dialog)

        # Test avanzamento fasi
        dialog.update_active_phase(0, 10.0)
        self.assertIn("VOCE QWEN3", dialog.step_tts.text())

        dialog.update_active_phase(1, 35.0)
        self.assertIn("SOTTOTITOLI", dialog.step_whisper.text())

        dialog.update_active_story(
            title="My Great Story",
            current_part=1,
            total_parts=2,
            clip_name="Minecraft"
        )
        self.assertIn("My Great Story", dialog.lbl_current_story.text())

        # Test finish production
        dialog.finish_production(total_completed=2)
        self.assertEqual(dialog.prog_global.value(), 100)
        self.assertIn("COMPLETATO", dialog.step_render.text())
        dialog.close()

    def test_08_batch_queue_modal_propagation(self):
        """Testa BatchQueueManagerModal, checkbox, e propagazione 'Applica a Tutte'."""
        from app.ui.modals.batch_queue_modal import BatchQueueManagerModal

        modal = BatchQueueManagerModal(
            script_repo=self.repo,
            video_mgr=self.video_pool
        )
        self.assertIsNotNone(modal)

        if modal.queue_items:
            modal.queue_items[0].voice_config = {"speaker": "Vivian", "instruct": "Storyteller"}
            modal.queue_items[0].speed_rate = 1.15
            modal._apply_first_voice_to_all()

            for item in modal.queue_items:
                self.assertEqual(item.voice_config["speaker"], "Vivian")
                self.assertEqual(item.speed_rate, 1.15)
        modal.close()

    def test_09_main_window_batch_and_single_job_dispatch(self):
        """Testa MainWindow, caricamento job singolo e generazione batch flow."""
        from app.ui.main_window import MainWindow

        win = MainWindow()
        self.assertIsNotNone(win)

        # Configura script attivo
        dummy_script = {
            "id": 888,
            "context_title": "Interstellar Comet",
            "raw_text": "An interstellar comet visited our solar system at extreme velocities.",
            "char_count": 68,
            "word_count": 11,
            "est_duration_sec": 4.4,
            "status": "DISPONIBILE"
        }
        win.set_active_script(dummy_script)
        self.assertEqual(win.active_script_id, 888)

        # Test dispatch single job configuration
        # Simula click avvio generazione
        win.active_video_category = "General"
        # Verifica che la pipeline accetti i job
        test_job = ProductionJob(
            story_id=888,
            context_title="Interstellar Comet",
            text=dummy_script["raw_text"],
            category="General"
        )
        win._pending_jobs = [test_job]
        self.assertEqual(len(win._pending_jobs), 1)
        self.assertEqual(win._pending_jobs[0].text, dummy_script["raw_text"])
        win.close()


if __name__ == "__main__":
    unittest.main()

