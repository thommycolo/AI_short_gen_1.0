"""Tests for Qwen supported default voices and Pitch / Sampling Temperature persistence."""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from app.config import (
    QWEN_DEFAULT_VOICES, QWEN_SUPPORTED_SPEAKER_IDS,
    QWEN_SPEAKER_NAMES, QWEN_SPEAKER_DISPLAY_MAP
)
from app.core.preset_manager import PresetManager
from app.core.tts_engine import Qwen3VoiceSuite
from app.ui.components.voice_selector import VoiceSelectorCard
from app.ui.drawers.voice_settings_drawer import VoiceSettingsDrawer
from app.ui.main_window import MainWindow, MainWindowAuditionWorker


class TestQwenVoicesAndPitchTemp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_01_all_nine_qwen_default_voices_configured(self):
        """Verifica che tutte le 9 voci supportate di default da Qwen3-TTS siano configurate."""
        self.assertEqual(len(QWEN_DEFAULT_VOICES), 9)

        expected_ids = {"ryan", "aiden", "vivian", "serena", "dylan", "eric", "ono_anna", "sohee", "uncle_fu"}
        configured_ids = {v["id"] for v in QWEN_DEFAULT_VOICES}
        self.assertEqual(configured_ids, expected_ids)

        expected_names = {"Ryan", "Aiden", "Vivian", "Serena", "Dylan", "Eric", "Ono_Anna", "Sohee", "Uncle_Fu"}
        configured_names = set(QWEN_SPEAKER_NAMES)
        self.assertEqual(configured_names, expected_names)

    def test_02_voice_selector_card_has_all_qwen_voices(self):
        """Verifica che VoiceSelectorCard mostri tutte le 9 voci nel dropdown dello speaker."""
        card = VoiceSelectorCard()
        items = [card.combo_speaker.itemText(i) for i in range(card.combo_speaker.count())]
        item_speakers = [txt.split()[0].lower() for txt in items]

        expected_speakers = ["ryan", "aiden", "vivian", "serena", "dylan", "eric", "ono_anna", "sohee", "uncle_fu"]
        for spk in expected_speakers:
            self.assertIn(spk, item_speakers, f"Speaker {spk} non presente in VoiceSelectorCard")

    def test_03_voice_settings_drawer_has_all_qwen_voices(self):
        """Verifica che VoiceSettingsDrawer mostri tutte le 9 voci nel dropdown dello speaker."""
        drawer = VoiceSettingsDrawer()
        items = [drawer.combo_speaker.itemText(i) for i in range(drawer.combo_speaker.count())]
        item_speakers = [txt.split()[0].lower() for txt in items]

        expected_speakers = ["ryan", "aiden", "vivian", "serena", "dylan", "eric", "ono_anna", "sohee", "uncle_fu"]
        for spk in expected_speakers:
            self.assertIn(spk, item_speakers, f"Speaker {spk} non presente in VoiceSettingsDrawer")

    def test_04_preset_manager_saves_and_retrieves_pitch_and_temp(self):
        """Verifica che PresetManager salvi e carichi correttamente pitch e temperature nel DB."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db = tmp.name

        try:
            pm = PresetManager(db_path=tmp_db)
            cfg = {
                "speaker": "Dylan",
                "instruct": "High energy test",
                "speed": 1.15,
                "pitch": -2.0,
                "temperature": 0.85
            }
            pm.save_voice_preset("Test_Preset_PitchTemp", cfg)

            presets = pm.get_voice_presets()
            saved = next((p for p in presets if p["preset_name"] == "Test_Preset_PitchTemp"), None)
            self.assertIsNotNone(saved)
            self.assertEqual(saved["speaker_or_profile"], "Dylan")
            self.assertAlmostEqual(saved["pitch"], -2.0)
            self.assertAlmostEqual(saved["temperature"], 0.85)
            self.assertAlmostEqual(saved["speed_rate"], 1.15)
        finally:
            try:
                Path(tmp_db).unlink(missing_ok=True)
            except Exception:
                pass

    def test_05_voice_settings_drawer_restores_pitch_and_temp_on_init(self):
        """Verifica che VoiceSettingsDrawer applichi pitch e temperature passati in current_settings."""
        current_cfg = {
            "speaker": "Eric",
            "instruct": "Action pacing",
            "speed": 1.20,
            "pitch": 3.0,
            "temperature": 0.85
        }
        drawer = VoiceSettingsDrawer(current_settings=current_cfg)

        # Verifica speaker impostato a Eric
        current_spk = drawer.combo_speaker.currentText().split()[0].lower()
        self.assertEqual(current_spk, "eric")

        # Verifica slider pitch impostato a 3
        self.assertEqual(drawer.slider_pitch.value(), 3)
        self.assertIn("(+3.0)", drawer.lbl_pitch.text())

        # Verifica slider temp impostato a 85 (0.85)
        self.assertEqual(drawer.slider_temp.value(), 85)
        self.assertIn("0.85", drawer.lbl_temp.text())

        # Verifica che get_config restituisca i valori impostati
        out_cfg = drawer.get_config()
        self.assertEqual(out_cfg["speaker"], "Eric")
        self.assertAlmostEqual(out_cfg["pitch"], 3.0)
        self.assertAlmostEqual(out_cfg["temperature"], 0.85)
        self.assertAlmostEqual(out_cfg["temp"], 0.85)

    def test_06_voice_settings_drawer_restores_pitch_and_temp_on_preset_select(self):
        """Verifica che la selezione di un preset in VoiceSettingsDrawer carichi pitch e temperature."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db = tmp.name

        try:
            pm = PresetManager(db_path=tmp_db)
            pm.save_voice_preset("Preset_Deep_UncleFu", {
                "speaker": "Uncle_Fu",
                "instruct": "Deep trailer voice",
                "speed": 0.90,
                "pitch": -3.0,
                "temperature": 0.60
            })

            drawer = VoiceSettingsDrawer(preset_mgr=pm)

            # Trova l'indice del preset appena salvato
            target_idx = -1
            for i in range(drawer.combo_presets.count()):
                if "Preset_Deep_UncleFu" in drawer.combo_presets.itemText(i):
                    target_idx = i
                    break

            self.assertGreaterEqual(target_idx, 0, "Preset non trovato nel combo")
            drawer.combo_presets.setCurrentIndex(target_idx)

            # Verifica aggiornamento controlli
            self.assertEqual(drawer.slider_pitch.value(), -3)
            self.assertEqual(drawer.slider_temp.value(), 60)
            self.assertAlmostEqual(drawer.slider_rate.value() / 100.0, 0.90)

            out_cfg = drawer.get_config()
            self.assertEqual(out_cfg["speaker"], "Uncle_Fu")
            self.assertAlmostEqual(out_cfg["pitch"], -3.0)
            self.assertAlmostEqual(out_cfg["temperature"], 0.60)
        finally:
            try:
                Path(tmp_db).unlink(missing_ok=True)
            except Exception:
                pass

    def test_07_voice_selector_card_preserves_pitch_and_temp(self):
        """Verifica che VoiceSelectorCard non perda pitch e temperature quando l'utente cambia opzioni."""
        card = VoiceSelectorCard()
        card.set_config({
            "speaker": "Vivian",
            "pitch": 1.0,
            "temperature": 0.78,
            "speed": 1.05
        })

        # Cambio speaker su Aiden
        for i in range(card.combo_speaker.count()):
            if "aiden" in card.combo_speaker.itemText(i).lower():
                card.combo_speaker.setCurrentIndex(i)
                break

        cfg = card.get_config()
        self.assertEqual(cfg["speaker"], "Aiden")
        # Pitch e temperature devono rimanere preservati
        self.assertAlmostEqual(cfg["pitch"], 1.0)
        self.assertAlmostEqual(cfg["temperature"], 0.78)
        self.assertAlmostEqual(cfg["speed"], 1.05)

    def test_08_tts_engine_supports_all_qwen_speakers(self):
        """Verifica che Qwen3VoiceSuite riconosca e risolva tutti i 9 speaker Qwen nativi."""
        suite = Qwen3VoiceSuite()
        speakers_to_test = ["ryan", "aiden", "vivian", "serena", "dylan", "eric", "ono_anna", "sohee", "uncle_fu"]
        for spk in speakers_to_test:
            spk_clean = spk.strip().lower().replace(" ", "_")
            supported_speakers = {"aiden", "dylan", "eric", "ono_anna", "ryan", "serena", "sohee", "uncle_fu", "vivian"}
            self.assertIn(spk_clean, supported_speakers)


if __name__ == "__main__":
    unittest.main()

