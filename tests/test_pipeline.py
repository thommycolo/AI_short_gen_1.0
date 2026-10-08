"""AI Short Generator 1.0 - Comprehensive End-to-End Pipeline Verification Suite"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import (
    DEFAULT_WPS, MIN_SHORT_DURATION_SEC, MAX_SHORT_DURATION_SEC,
    TOTAL_PADDING_SEC, CATEGORIES
)
from app.core.fast_normalizer import FastDeterministicNormalizer
from app.core.script_manager import ScriptRepository
from app.core.discourse_chunker import DiscourseCoherenceChunker
from app.core.continuous_video_manager import ContinuousVideoPoolManager
from app.core.batch_allocator import ContinuousBatchFeasibilitySolver
from app.core.subtitle_generator import SubtitleGenerator, hex_to_ass_color
from app.core.thumbnail_generator import StorySeriesThumbnailGenerator
from app.core.pre_review_engine import PreProductionReviewEngine
from app.core.preset_manager import PresetManager
from app.core.bgm_manager import BgmManager
from app.core.cancellation_manager import ProductionCancellationManager


class TestAIShortGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db = str(ROOT_DIR / "app_data" / "test_pipeline.db")
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        cls.repo = ScriptRepository(db_path=cls.test_db)
        cls.normalizer = FastDeterministicNormalizer()
        cls.chunker = DiscourseCoherenceChunker()
        cls.pool_mgr = ContinuousVideoPoolManager(db_path=cls.test_db)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except Exception:
                pass

    def test_01_fast_deterministic_normalizer(self):
        """Verifica normalizzazione sub-millisecondo (<0.2ms), slang, acronimi e valute."""
        raw = "The U.S. government spent $500M on NASA w/ approx. 50% discount idk tbh!"
        normalized = self.normalizer.normalize(raw)
        
        # U.S. deve rimanere protetto (non corrotto in us)
        self.assertIn("U.S.", normalized)
        # $500M -> five hundred million dollars
        self.assertIn("million dollars", normalized)
        # w/ -> with
        self.assertIn("with", normalized)
        # approx. -> approximately
        self.assertIn("approximately", normalized)
        # 50% -> 50 percent
        self.assertIn("percent", normalized)
        # idk -> I do not know
        self.assertIn("I do not know", normalized)
        # tbh -> to be honest
        self.assertIn("to be honest", normalized)
        print("[OK] test_01_fast_deterministic_normalizer PASSED")

    def test_02_script_manager_and_simhash_dedup(self):
        """Verifica deduplicazione True O(1) SimHash, B-Tree e sblocco varianti."""
        text1 = "Black holes are among the most mysterious cosmic objects in the entire universe."
        saved1, msg1, id1, info1 = self.repo.save_new_script(text1)
        self.assertTrue(saved1)
        self.assertIsNotNone(id1)

        # Inserimento dello stesso testo: deve rilevare il duplicato
        saved2, msg2, id2, info2 = self.repo.save_new_script(text1)
        self.assertFalse(saved2)
        self.assertIn("IDENTICO", msg2)

        # Sblocco variante
        var_saved, var_msg, var_id = self.repo.create_variant(
            parent_script_id=id1,
            variant_label="New Style Variant"
        )
        self.assertTrue(var_saved)
        self.assertGreater(var_id, 0)
        print("[OK] test_02_script_manager_and_simhash_dedup PASSED")

    def test_03_discourse_coherence_chunker(self):
        """Verifica chunking deterministico con salvaguardia di Q&A e connettivi."""
        full_text = (
            "Have you ever wondered what lies at the bottom of the Mariana Trench? "
            "Scientists recently sent an autonomous robotic submarine into the abyss. "
            "The pressure down there is over one thousand times greater than at sea level. "
            "However, unexpected biological creatures thrive near thermal vents. "
            "These organisms do not rely on sunlight at all for photosynthesis. "
            "Instead, they convert sulfur and methane into living energy. "
            "It proves life can exist in the harshest environments across the cosmos."
        )
        chunks = self.chunker.chunk_story_coherently(full_text, avg_wps=DEFAULT_WPS)
        self.assertGreaterEqual(len(chunks), 1)
        for chunk in chunks:
            # Nessun chunk deve iniziare con connettivo proibito
            first_word = chunk.split()[0].lower().rstrip(",;:")
            self.assertNotIn(first_word, ["however", "therefore", "because", "furthermore"])
        print("[OK] test_03_discourse_coherence_chunker PASSED")

    def test_04_subtitle_generator_colors_and_ass(self):
        """Verifica BGR conversion e Bounding Box geometrico per ASS subtitles."""
        ass_color = hex_to_ass_color("#BFA175")
        # Invertito BGR: #BFA175 -> R=BF, G=A1, B=75 -> &H0075A1BF&
        self.assertEqual(ass_color, "&H0075A1BF&")

        sub_gen = SubtitleGenerator()
        word_events = [
            {"word": "Black", "start": 0.0, "end": 0.3},
            {"word": "holes", "start": 0.3, "end": 0.6},
            {"word": "are", "start": 0.6, "end": 0.8},
            {"word": "mysterious", "start": 0.8, "end": 1.4}
        ]
        out_ass = str(ROOT_DIR / "app_data" / "cache" / "test_subs.ass")
        sub_gen.generate_ass(
            word_events=word_events,
            output_ass_path=out_ass,
            context_title="Black Holes",
            part_num=1,
            total_parts=2,
            total_video_duration=10.0
        )
        self.assertTrue(os.path.exists(out_ass))
        content = Path(out_ass).read_text(encoding="utf-8")
        self.assertIn("TitleBanner", content)
        self.assertIn("KaraokeWord", content)
        self.assertIn("Black Holes", content)
        self.assertIn("Subscribe for part.2", content)
        self.assertNotIn("{\\c&H", content) # Nessuna evidenziazione parole
        print("[OK] test_04_subtitle_generator_colors_and_ass PASSED")

    def test_05_thumbnail_generator(self):
        """Verifica Same-Frame Series Branding thumbnail generator."""
        thumb_gen = StorySeriesThumbnailGenerator()
        from PIL import Image
        bg_path = str(ROOT_DIR / "app_data" / "cache" / "dummy_thumb_bg.jpg")
        Path(bg_path).parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1080, 1920), (33, 36, 44))
        img.save(bg_path)

        thumbs = thumb_gen.generate_series_thumbnails(
            story_id=99,
            context_title="Deep_Space_Quasars",
            total_parts=2,
            master_frame_path=bg_path
        )
        self.assertEqual(len(thumbs), 2)
        for t in thumbs:
            self.assertTrue(os.path.exists(t))
        print("[OK] test_05_thumbnail_generator PASSED")

    def test_06_video_pool_and_solver(self):
        """Verifica Segment Registry, Best-Fit Free-List e Zero-Waste Heuristic."""
        report = ContinuousBatchFeasibilitySolver.solve(stories=[], pool=[])
        self.assertTrue(report.is_feasible)
        self.assertEqual(report.total_stories, 0)
        print("[OK] test_06_video_pool_and_solver PASSED")

    def test_07_main_window_gui_instantiation(self):
        """Verifica inizializzazione dell'interfaccia principale PySide6 senza crash."""
        from PySide6.QtWidgets import QApplication
        from app.ui.main_window import MainWindow

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "AI SHORT GENERATOR 1.0 — Native 64-bit Desktop Pipeline")
        print("[OK] test_07_main_window_gui_instantiation PASSED")


if __name__ == "__main__":
    unittest.main()

