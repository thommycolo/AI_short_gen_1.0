"""AI Short Generator 1.0 - Preset Manager (Voice & Subtitle Styles) & Audio Demo Clamp"""

import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
from app.config import SCRIPTS_DB_PATH
from app.core.silero_vad_trimmer import SileroVADSilenceTrimmer


class PresetManager:
    def __init__(self, db_path: str = SCRIPTS_DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_name TEXT NOT NULL UNIQUE,
                    language TEXT NOT NULL DEFAULT 'English',
                    speaker_or_profile TEXT NOT NULL,
                    voice_type TEXT NOT NULL,
                    instruct_prompt TEXT NULL,
                    speed_rate REAL DEFAULT 1.00,
                    pitch REAL DEFAULT 0.0,
                    temperature REAL DEFAULT 0.70,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subtitle_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_name TEXT NOT NULL UNIQUE,
                    font_name TEXT NOT NULL DEFAULT 'Montserrat Black',
                    font_size INTEGER DEFAULT 68,
                    is_all_caps BOOLEAN DEFAULT 1,
                    animation_style TEXT DEFAULT 'WORD_POP',
                    primary_color_hex TEXT DEFAULT '#DCE0EA',
                    highlight_color_hex TEXT DEFAULT '#BFA175',
                    outline_color_hex TEXT DEFAULT '#181A20',
                    outline_width INTEGER DEFAULT 5,
                    shadow_radius INTEGER DEFAULT 3,
                    margin_v INTEGER DEFAULT 440,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        self._seed_default_presets()

    def _seed_default_presets(self):
        import json
        voice_json = Path("assets/presets/voice_presets.json")
        if voice_json.exists():
            with sqlite3.connect(self.db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM voice_presets").fetchone()[0]
                if count == 0:
                    try:
                        data = json.loads(voice_json.read_text(encoding="utf-8"))
                        for item in data:
                            conn.execute("""
                                INSERT OR IGNORE INTO voice_presets 
                                (preset_name, language, speaker_or_profile, voice_type, instruct_prompt, speed_rate, pitch, temperature)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item.get("preset_name"), item.get("language", "English"),
                                item.get("speaker_or_profile", "Ryan"), item.get("voice_type", "CUSTOM"),
                                item.get("instruct_prompt", ""), float(item.get("speed_rate", 1.0)),
                                float(item.get("pitch", 0.0)), float(item.get("temperature", 0.7))
                            ))
                    except Exception:
                        pass

        sub_json = Path("assets/presets/subtitle_presets.json")
        if sub_json.exists():
            with sqlite3.connect(self.db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM subtitle_presets").fetchone()[0]
                if count == 0:
                    try:
                        data = json.loads(sub_json.read_text(encoding="utf-8"))
                        for item in data:
                            conn.execute("""
                                INSERT OR IGNORE INTO subtitle_presets
                                (preset_name, font_name, font_size, is_all_caps, animation_style,
                                 primary_color_hex, highlight_color_hex, outline_color_hex, outline_width, shadow_radius, margin_v)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item.get("preset_name"), item.get("font_name", "Montserrat Black"),
                                int(item.get("font_size", 68)), int(bool(item.get("is_all_caps", True))),
                                item.get("animation_style", "WORD_POP"), item.get("primary_color_hex", "#DCE0EA"),
                                item.get("highlight_color_hex", "#BFA175"), item.get("outline_color_hex", "#181A20"),
                                int(item.get("outline_width", 5)), int(item.get("shadow_radius", 3)),
                                int(item.get("margin_v", 440))
                            ))
                    except Exception:
                        pass

    def save_voice_preset(self, name: str, config: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                INSERT OR REPLACE INTO voice_presets 
                (preset_name, language, speaker_or_profile, voice_type, instruct_prompt, speed_rate, pitch, temperature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, config.get("language", "English"), config.get("speaker_or_profile", "Ryan"),
                config.get("voice_type", "CUSTOM"), config.get("instruct", ""),
                float(config.get("speed", 1.0)), float(config.get("pitch", 0.0)),
                float(config.get("temp", 0.7))
            ))

    def save_subtitle_preset(self, name: str, config: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                INSERT OR REPLACE INTO subtitle_presets
                (preset_name, font_name, font_size, is_all_caps, animation_style,
                 primary_color_hex, highlight_color_hex, outline_color_hex, outline_width, shadow_radius, margin_v)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, config.get("font_name", "Montserrat Black"), int(config.get("font_size", 68)),
                int(bool(config.get("is_all_caps", True))), config.get("animation_style", "WORD_POP"),
                config.get("primary_color_hex", "#DCE0EA"), config.get("highlight_color_hex", "#BFA175"),
                config.get("outline_color_hex", "#181A20"), int(config.get("outline_width", 5)),
                int(config.get("shadow_radius", 3)), int(config.get("margin_v", 440))
            ))

    def get_voice_presets(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM voice_presets ORDER BY preset_name ASC").fetchall()
            return [dict(r) for r in rows]

    def get_subtitle_presets(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM subtitle_presets ORDER BY preset_name ASC").fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def clamp_audio_demo_to_5s(raw_wav_path: str, output_demo_path: str, max_sec: float = 5.0):
        """Taglia rigorosamente l'audio sintetizzato a un massimo di 5.0 secondi con micro fadeout."""
        data, sr = SileroVADSilenceTrimmer._read_wav(raw_wav_path)
        max_samples = int(max_sec * sr)
        if len(data) > max_samples:
            trimmed = data[:max_samples].copy()
            fade_len = int(0.05 * sr)
            if len(trimmed) > fade_len:
                fade = np.linspace(1.0, 0.0, fade_len)
                if trimmed.ndim > 1:
                    fade = np.expand_dims(fade, 1)
                trimmed[-fade_len:] = trimmed[-fade_len:] * fade
            SileroVADSilenceTrimmer._write_wav(output_demo_path, trimmed, sr)
        else:
            SileroVADSilenceTrimmer._write_wav(output_demo_path, data, sr)

