"""Test verification for Voice Studio & Voice Intelligence UI updates."""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication
from app.ui.drawers.voice_settings_drawer import VoiceSettingsDrawer
from app.ui.components.voice_selector import VoiceSelectorCard
from app.ui.main_window import MainWindow


class TestVoiceStudioUpdates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_voice_studio_tab_titles(self):
        drawer = VoiceSettingsDrawer()
        tab_count = drawer.tabs.count()
        self.assertEqual(tab_count, 2)

        # Check tab 0 title is VOCI STANDARD (without 'tab 1')
        tab0_title = drawer.tabs.tabText(0)
        self.assertIn("VOCI STANDARD", tab0_title.upper())
        self.assertNotIn("TAB 1", tab0_title.upper())
        self.assertNotIn("TAB", tab0_title.upper())

        # Check all tabs do NOT have 'tab n'
        for i in range(tab_count):
            title = drawer.tabs.tabText(i).upper()
            self.assertFalse(any(f"TAB {n}" in title for n in range(1, 10)), f"Tab {i} has 'TAB n': {title}")

        # Check that voice clone and design tabs have been removed
        tab_titles = [drawer.tabs.tabText(i).upper() for i in range(tab_count)]
        self.assertNotIn("VOICE CLONE", tab_titles)
        self.assertNotIn("VOICE DESIGN", tab_titles)

    def test_tab_voci_standard_no_lingua_primaria(self):
        drawer = VoiceSettingsDrawer()
        # combo_lang must NOT exist
        self.assertFalse(hasattr(drawer, "combo_lang"))

    def test_audition_four_benchmark_buttons(self):
        drawer = VoiceSettingsDrawer()

        # Must have the 4 benchmark buttons
        self.assertTrue(hasattr(drawer, "btn_test_phonetic"))
        self.assertTrue(hasattr(drawer, "btn_test_context"))
        self.assertTrue(hasattr(drawer, "btn_test_emotion"))
        self.assertTrue(hasattr(drawer, "btn_test_format"))

        # Verify button tooltips or connected phrases
        self.assertIn("The box was thrown beside the parked truck.", drawer.btn_test_phonetic.toolTip())
        self.assertIn("The soldier decided to desert his post in the dry desert.", drawer.btn_test_context.toolTip())
        self.assertIn("Wait—don't tell me... they actually lost the game?!", drawer.btn_test_emotion.toolTip())
        self.assertIn("The update is live at example.com.", drawer.btn_test_format.toolTip())

    def test_voice_clone_and_design_tabs_removed(self):
        drawer = VoiceSettingsDrawer()

        # Voice clone and design elements must NOT exist in the drawer
        tab_titles = [drawer.tabs.tabText(i).upper() for i in range(drawer.tabs.count())]
        self.assertNotIn("VOICE CLONE", tab_titles)
        self.assertNotIn("VOICE DESIGN", tab_titles)
        self.assertFalse(hasattr(drawer, "prog_clone"))
        self.assertFalse(hasattr(drawer, "lbl_clone_status"))
        self.assertFalse(hasattr(drawer, "btn_test_clone"))

    def test_main_window_voice_selector_and_demo_phrase(self):
        card = VoiceSelectorCard()
        self.assertEqual(card.btn_audition.text(), "▶ Ascolta Demo")

        win = MainWindow()
        self.assertEqual(win.card_voice.btn_audition.text(), "▶ Ascolta Demo")


if __name__ == "__main__":
    unittest.main()

