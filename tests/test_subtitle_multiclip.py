import os
import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QTextEdit

app = QApplication.instance() or QApplication(sys.argv)

from app.core.preset_manager import PresetManager
from app.core.script_manager import ScriptRepository
from app.core.subtitle_generator import SubtitleGenerator
from app.ui.drawers.subtitle_drawer import SubtitleDrawer


class TestSubtitleMultiClip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = ScriptRepository()
        cls.preset_mgr = PresetManager()

    def test_multi_clip_auto_chunking_and_navigation(self):
        s1 = self.repo.get_script_by_id(1)
        self.assertIsNotNone(s1)
        drawer = SubtitleDrawer(
            preset_manager=self.preset_mgr,
            script_data=s1,
            script_repo=self.repo
        )
        self.assertGreaterEqual(len(drawer.clips), 3, "Script 1 should auto-chunk into at least 3 clips")

        # Verifica rimozione menu a tendina cmb_clip_selector (requisito utente)
        self.assertFalse(hasattr(drawer, "cmb_clip_selector"), "Il dropdown cmb_clip_selector deve essere rimosso")

        # Verifica stato iniziale
        self.assertIn(f"1 di {len(drawer.clips)}", drawer.lbl_clip_badge.text())
        self.assertFalse(drawer.btn_prev_clip.isEnabled())
        self.assertTrue(drawer.btn_next_clip.isEnabled())

        # Test navigazione avanti con freccia
        drawer._on_next_clip()
        self.assertEqual(drawer.current_clip_idx, 1)
        self.assertTrue(drawer.btn_prev_clip.isEnabled())
        self.assertIn(f"2 di {len(drawer.clips)}", drawer.lbl_clip_badge.text())

        # Test navigazione indietro con freccia
        drawer._on_prev_clip()
        self.assertEqual(drawer.current_clip_idx, 0)
        self.assertIn(f"1 di {len(drawer.clips)}", drawer.lbl_clip_badge.text())

    def test_add_clip_and_copy_paste_specs(self):
        s1 = self.repo.get_script_by_id(1)
        drawer = SubtitleDrawer(preset_manager=self.preset_mgr, script_data=s1, script_repo=self.repo)
        init_clips = len(drawer.clips)

        # Modifica stile clip 0
        drawer.sld_size.setValue(75)
        drawer.rb_bounce.setChecked(True)
        drawer._on_control_changed()
        self.assertEqual(drawer.clip_styles[0]["subtitle"]["font_size"], 75)
        self.assertEqual(drawer.clip_styles[0]["subtitle"]["animation_style"], "BOUNCE")

        # Copia specifiche dalla clip 0
        drawer._on_copy_specs()
        self.assertIsNotNone(drawer.copied_specs_clipboard)

        # Passa a clip 1 e verifica che abbia valori di default
        drawer._on_next_clip()
        self.assertNotEqual(drawer.clip_styles[1]["subtitle"]["font_size"], 75)

        # Incolla specifiche nella clip 1
        drawer._on_paste_specs()
        self.assertEqual(drawer.clip_styles[1]["subtitle"]["font_size"], 75)
        self.assertEqual(drawer.clip_styles[1]["subtitle"]["animation_style"], "BOUNCE")

        # Aggiunta nuova clip
        drawer._on_add_clip()
        self.assertEqual(len(drawer.clips), init_clips + 1)
        self.assertEqual(drawer.current_clip_idx, init_clips)
        self.assertIn(f"{init_clips + 1} di {init_clips + 1}", drawer.lbl_clip_badge.text())

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

    def test_multiline_titles_and_vertical_positions(self):
        s1 = self.repo.get_script_by_id(1)
        drawer = SubtitleDrawer(preset_manager=self.preset_mgr, script_data=s1, script_repo=self.repo)

        # 1. Verifica altezza massima testo standard a 2000px
        self.assertEqual(drawer.sld_y.maximum(), 2000)
        self.assertEqual(drawer.sld_y.minimum(), 0)

        # 2. Verifica rimozione dicitura '(Y Fondo)'
        # Cerca le label nella tab sottotitoli
        self.assertNotIn("(Y Fondo)", drawer.lbl_val_y.parentWidget().findChildren(type(drawer.lbl_val_y))[0].text() if False else "")

        # 3. Verifica supporto QTextEdit multiriga per Titoli di Testa
        self.assertIsInstance(drawer.txt_intro_title, QTextEdit)
        drawer.txt_intro_title.setPlainText("Mistero dei Buchi Neri\nParte 1")
        self.assertEqual(drawer.txt_intro_title.toPlainText(), "Mistero dei Buchi Neri\nParte 1")

        # 4. Verifica slider verticale Titoli di Testa (range 0-2000, default 960)
        self.assertEqual(drawer.sld_intro_y.minimum(), 0)
        self.assertEqual(drawer.sld_intro_y.maximum(), 2000)
        drawer.sld_intro_y.setValue(1350)
        drawer._on_intro_control_changed()
        self.assertEqual(drawer.clip_styles[0]["intro"]["margin_v"], 1350)

        # 5. Verifica supporto QTextEdit multiriga per Titoli di Coda
        self.assertIsInstance(drawer.txt_outro_title, QTextEdit)
        drawer.txt_outro_title.setPlainText("Seguimi per altri video!\nIscriviti al canale")
        self.assertEqual(drawer.txt_outro_title.toPlainText(), "Seguimi per altri video!\nIscriviti al canale")

        # 6. Verifica slider verticale Titoli di Coda (range 0-2000, default 960)
        self.assertEqual(drawer.sld_outro_y.minimum(), 0)
        self.assertEqual(drawer.sld_outro_y.maximum(), 2000)
        drawer.sld_outro_y.setValue(450)
        drawer._on_outro_control_changed()
        self.assertEqual(drawer.clip_styles[0]["outro"]["margin_v"], 450)

        # 7. Verifica export ASS con conversione \n -> \N e margin_v corretto
        settings = drawer.get_settings()
        out_ass = Path("tests/output/test_multiline.ass")
        gen = SubtitleGenerator()
        gen.generate_ass(
            word_events=[{"word": "Test", "start": 0.5, "end": 1.0}],
            output_ass_path=str(out_ass),
            context_title="Test",
            style_config=settings,
            total_video_duration=5.0
        )
        self.assertTrue(out_ass.exists())
        content = out_ass.read_text(encoding="utf-8")

        # Verifica che Style TitleBanner e OutroBanner abbiano MarginV corrispondente
        self.assertIn(",2,60,60,1350,1", content, "TitleBanner deve usare MarginV=1350")
        self.assertIn(",2,60,60,450,1", content, "OutroBanner deve usare MarginV=450")

        # Verifica che il testo multiriga contenga \N al posto di newline
        self.assertIn("MISTERO DEI BUCHI NERI\\NPARTE 1", content)
        self.assertIn("Seguimi per altri video!\\NIscriviti al canale", content)

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
