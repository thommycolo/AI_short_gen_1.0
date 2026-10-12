"""Test suite for Gemini TTS Modular Architecture, Quota Tracker (95% Safeguard), and API Key Manager."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from app.core.tts.base import BaseTTSProvider, TTSVoiceConfig, TTSAudioResult, VoiceInfo
from app.core.tts.factory import TTSFactory
from app.core.tts.quota_tracker import QuotaTracker, QuotaSafeguardExceededError
from app.core.tts.key_manager import APIKeyManager
from app.core.tts.gemini_provider import GeminiTTSProvider
from app.core.tts.system_provider import SystemTTSProvider
from app.core.tts_engine import VoiceIntelligenceEngine
from app.ui.drawers.voice_settings_drawer import VoiceSettingsDrawer
from app.ui.components.voice_selector import VoiceSelectorCard


class TestGeminiTTSModular(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_01_quota_tracker_and_95_percent_safeguard(self):
        """Verifica che il QuotaTracker blocchi rigorosamente al superamento del 95% del limite mensile."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tracker_file = Path(tmp_dir) / "test_quota.json"
            tracker = QuotaTracker(storage_path=tracker_file)
            tracker.DEFAULT_MONTHLY_LIMITS["test_provider"] = 100_000 # 100k limite, 95k soglia 95%

            # Inizialmente 0 consumati
            stats = tracker.get_monthly_usage("test_provider")
            self.assertEqual(stats["characters_used"], 0)
            self.assertEqual(stats["safety_limit_95"], 95_000)
            self.assertFalse(stats["is_locked"])

            # Richiesta sicura: 50.000 caratteri -> OK
            tracker.check_and_reserve("test_provider", 50_000)
            tracker.record_usage("test_provider", 50_000, tokens_count=12_500)

            stats = tracker.get_monthly_usage("test_provider")
            self.assertEqual(stats["characters_used"], 50_000)
            self.assertEqual(stats["remaining_safe_characters"], 45_000)

            # Richiesta che porta a 94.000 (sotto i 95.000) -> OK
            tracker.check_and_reserve("test_provider", 44_000)
            tracker.record_usage("test_provider", 44_000, tokens_count=11_000)

            stats = tracker.get_monthly_usage("test_provider")
            self.assertEqual(stats["characters_used"], 94_000)
            self.assertEqual(stats["remaining_safe_characters"], 1_000)

            # Richiesta che supererebbe la soglia del 95% (94.000 + 1.500 = 95.500 > 95.000) -> ECCEZIONE
            with self.assertRaises(QuotaSafeguardExceededError) as ctx:
                tracker.check_and_reserve("test_provider", 1_500)

            self.assertIn("BLOCCO DI SICUREZZA 95%", str(ctx.exception))
            self.assertIn("94,000", str(ctx.exception))

            # Verifica persistenza su file JSON
            self.assertTrue(tracker_file.exists())
            tracker_reload = QuotaTracker(storage_path=tracker_file)
            stats_reload = tracker_reload.get_monthly_usage("test_provider")
            self.assertEqual(stats_reload["characters_used"], 94_000)

    def test_02_api_key_manager_persistence_and_masking(self):
        """Verifica la persistenza e mascheramento della API Key."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cred_file = Path(tmp_dir) / "credentials.json"
            orig_file = APIKeyManager.CREDENTIALS_FILE
            try:
                APIKeyManager.CREDENTIALS_FILE = cred_file
                test_key = "AIzaSyFakeSecretKeyForTesting123456"

                APIKeyManager.save_api_key(test_key, provider="gemini")
                self.assertTrue(cred_file.exists())

                resolved_key = APIKeyManager.get_api_key("gemini", allow_interactive=False)
                self.assertEqual(resolved_key, test_key)

                masked = APIKeyManager.mask_key(test_key)
                self.assertEqual(masked, "AIza••••••••3456")
            finally:
                APIKeyManager.CREDENTIALS_FILE = orig_file

    def test_03_tts_factory_and_providers_registration(self):
        """Verifica che la Factory registri e crei correttamente i provider."""
        providers = TTSFactory.get_registered_providers()
        prov_ids = [p["id"] for p in providers]
        self.assertIn("gemini_tts", prov_ids)
        self.assertIn("system_tts", prov_ids)

        gemini_p = TTSFactory.create("gemini_tts")
        self.assertIsInstance(gemini_p, GeminiTTSProvider)
        voices = gemini_p.get_available_voices()
        self.assertTrue(len(voices) >= 5)
        voice_ids = [v.id for v in voices]
        self.assertIn("Puck", voice_ids)
        self.assertIn("Charon", voice_ids)
        self.assertIn("Kore", voice_ids)

        sys_p = TTSFactory.create("system_tts")
        self.assertIsInstance(sys_p, SystemTTSProvider)

    def test_04_system_tts_synthesis_and_voice_engine(self):
        """Verifica che VoiceIntelligenceEngine sintetizzi correttamente file audio."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = str(Path(tmp_dir) / "test_synth.wav")
            engine = VoiceIntelligenceEngine(default_provider_id="system_tts")

            dur = engine.generate_custom(
                text="Testing speech synthesis with modular voice engine.",
                output_path=out_file,
                speaker="Puck",
                speed=1.10,
                pitch=1.0,
                volume_gain_db=2.0
            )

            self.assertTrue(os.path.exists(out_file))
            self.assertGreater(os.path.getsize(out_file), 100)
            self.assertGreater(dur, 0.5)

    def test_05_voice_settings_drawer_new_ui_elements(self):
        """Verifica che VoiceSettingsDrawer contenga i controlli API Key, Quota e Guadagno Volume."""
        drawer = VoiceSettingsDrawer()

        # Controlli di Provider e Volume
        self.assertTrue(hasattr(drawer, "combo_provider"))
        self.assertTrue(hasattr(drawer, "slider_volume"))
        self.assertTrue(hasattr(drawer, "lbl_volume"))

        # Controlli API Key
        self.assertTrue(hasattr(drawer, "txt_api_key"))
        self.assertTrue(hasattr(drawer, "btn_test_conn"))
        self.assertTrue(hasattr(drawer, "lbl_key_status"))

        # Controlli Quota Safeguard 95%
        self.assertTrue(hasattr(drawer, "prog_quota"))
        self.assertTrue(hasattr(drawer, "lbl_quota_stats"))
        self.assertTrue(hasattr(drawer, "lbl_quota_warning"))

        # Verifica get_config
        cfg = drawer.get_config()
        self.assertIn("provider", cfg)
        self.assertIn("volume_gain_db", cfg)
        self.assertIn("speaker", cfg)
        self.assertIn("speed", cfg)
        self.assertIn("pitch", cfg)


if __name__ == "__main__":
    unittest.main()

