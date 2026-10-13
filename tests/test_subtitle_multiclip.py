import sys
import unittest
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from app.core.preset_manager import PresetManager
from app.core.script_manager import ScriptRepository
from app.ui.drawers.subtitle_drawer import SubtitleDrawer
from app.ui.main_window import MainWindow

class TestSubtitleMultiClip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = ScriptRepository()
        cls.preset_mgr = PresetManager()

    def test_multi_clip_auto_chunking(self):
        s1 = self.repo.get_script_by_id(1)
        self.assertIsNotNone(s1)
        # s1 has 288 words and no pre-existing custom_chunks
        drawer = SubtitleDrawer(
            preset_manager=self.preset_mgr,
            script_data=s1,
            script_repo=self.repo
        )
        self.assertGreaterEqual(len(drawer.clips), 3, "Script 1 should auto-chunk into at least 3 clips")
        self.assertEqual(drawer.cmb_clip_selector.count(), len(drawer.clips))
        self.assertIn(f"1 di {len(drawer.clips)}", drawer.lbl_clip_badge.text())
        self.assertFalse(drawer.btn_prev_clip.isEnabled())
        self.assertTrue(drawer.btn_next_clip.isEnabled())

        # Test forward navigation
        drawer._on_next_clip()
        self.assertEqual(drawer.current_clip_idx, 1)
        self.assertEqual(drawer.cmb_clip_selector.currentIndex(), 1)
        self.assertTrue(drawer.btn_prev_clip.isEnabled())
        self.assertIn(f"2 di {len(drawer.clips)}", drawer.lbl_clip_badge.text())

        # Test backward navigation
        drawer._on_prev_clip()
        self.assertEqual(drawer.current_clip_idx, 0)
        self.assertEqual(drawer.cmb_clip_selector.currentIndex(), 0)

        # Test direct combobox jump
        drawer._on_clip_combo_changed(2)
        self.assertEqual(drawer.current_clip_idx, 2)
        self.assertEqual(drawer.cmb_clip_selector.currentIndex(), 2)

    def test_add_clip_and_copy_paste_specs(self):
        s1 = self.repo.get_script_by_id(1)
        drawer = SubtitleDrawer(preset_manager=self.preset_mgr, script_data=s1, script_repo=self.repo)
        init_clips = len(drawer.clips)

        # Modify clip 0 settings
        drawer.sld_size.setValue(75)
        drawer.rb_bounce.setChecked(True)
        drawer._on_control_changed()
        self.assertEqual(drawer.clip_styles[0]["subtitle"]["font_size"], 75)
        self.assertEqual(drawer.clip_styles[0]["subtitle"]["animation_style"], "BOUNCE")

        # Copy specs from clip 0
        drawer._on_copy_specs()
        self.assertIsNotNone(drawer.copied_specs_clipboard)

        # Move to clip 1 and verify it has default values, not 75
        drawer._on_next_clip()
        self.assertNotEqual(drawer.clip_styles[1]["subtitle"]["font_size"], 75)

        # Paste specs into clip 1
        drawer._on_paste_specs()
        self.assertEqual(drawer.clip_styles[1]["subtitle"]["font_size"], 75)
        self.assertEqual(drawer.clip_styles[1]["subtitle"]["animation_style"], "BOUNCE")

        # Add new clip
        drawer._on_add_clip()
        self.assertEqual(len(drawer.clips), init_clips + 1)
        self.assertEqual(drawer.current_clip_idx, init_clips)
        self.assertEqual(drawer.cmb_clip_selector.count(), init_clips + 1)

    def test_story_switching_inside_drawer(self):
        scripts = self.repo.get_scripts()
        if len(scripts) >= 2:
            s1 = scripts[0]
            s2 = scripts[1]
            drawer = SubtitleDrawer(preset_manager=self.preset_mgr, script_data=s1, script_repo=self.repo)
            idx_s2 = -1
            for i, s in enumerate(drawer.available_scripts):
                if s["id"] == s2["id"]:
                    idx_s2 = i
                    break
            if idx_s2 >= 0:
                drawer._on_story_selected(idx_s2)
                self.assertEqual(drawer.script_data["id"], s2["id"])
                self.assertGreaterEqual(len(drawer.clips), 2)
                self.assertEqual(drawer.current_clip_idx, 0)

    def test_get_settings_payload(self):
        s1 = self.repo.get_script_by_id(1)
        drawer = SubtitleDrawer(preset_manager=self.preset_mgr, script_data=s1, script_repo=self.repo)
        settings = drawer.get_settings()
        self.assertIn("custom_chunks", settings)
        self.assertIn("num_clips", settings)
        self.assertIn("clip_settings", settings)
        self.assertIn("custom_intros", settings)
        self.assertIn("custom_outros", settings)
        self.assertEqual(settings["num_clips"], len(drawer.clips))
        self.assertEqual(len(settings["custom_chunks"]), len(drawer.clips))

if __name__ == "__main__":
    unittest.main()
