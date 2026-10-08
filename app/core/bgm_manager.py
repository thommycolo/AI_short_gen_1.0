"""AI Short Generator 1.0 - Background Music (BGM), Safe CC0 Library & Mastering with True Peak Limiter"""

import os
import json
import sqlite3
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app.config import (
    SCRIPTS_DB_PATH, BGM_LIBRARY_DIR, BGM_SAFE_DIR,
    BGM_TARGET_LUFS, BGM_DUCKING_DB, BGM_INTRO_OUTRO_DB,
    TRUE_PEAK_LIMITER_DB, PADDING_INTRO_SEC, PADDING_OUTRO_SEC
)
from app.utils.ffmpeg_installer import find_system_ffmpeg, probe_media_duration
from app.utils.logger import log


@dataclass
class BgmTrackInfo:
    id: int
    title: str
    youtube_url: Optional[str]
    file_path: str
    duration_sec: float
    channel_name: str


class BgmManager:
    """
    Gestione Libreria BGM (Safe CC0 integrata & YouTube audio stream),
    normalizzazione Loudness EBU R128 a -24.0 LUFS,
    auto-ducking continuo tri-fase e True Peak Limiter a -1.0 dB.
    """

    def __init__(self, db_path: str = SCRIPTS_DB_PATH, bgm_dir: Path = BGM_LIBRARY_DIR):
        self.db_path = db_path
        self.bgm_dir = Path(bgm_dir)
        self.bgm_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._scan_builtin_safe_tracks()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bgm_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL DEFAULT 'YOUTUBE',
                    youtube_url TEXT NULL,
                    title TEXT NOT NULL,
                    channel_name TEXT NULL,
                    duration_sec REAL NOT NULL,
                    file_path TEXT NOT NULL,
                    target_lufs REAL DEFAULT -24.0,
                    status TEXT NOT NULL DEFAULT 'DISPONIBILE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _scan_builtin_safe_tracks(self):
        """Scansiona la cartella assets/bgm_safe/ per brani CC0 pre-installati."""
        if not BGM_SAFE_DIR.exists():
            return
        ffmpeg_bin, ffprobe_bin = find_system_ffmpeg()
        ffprobe_cmd = ffprobe_bin if ffprobe_bin else "ffprobe"

        for audio_file in BGM_SAFE_DIR.glob("*.*"):
            if audio_file.suffix.lower() in [".mp3", ".wav", ".m4a", ".ogg"]:
                try:
                    duration = probe_media_duration(str(audio_file))
                    if duration > 0.0:
                        with sqlite3.connect(self.db_path) as conn:
                            conn.execute("""
                                INSERT OR IGNORE INTO bgm_tracks (source_type, youtube_url, title, channel_name, duration_sec, file_path, target_lufs)
                                VALUES ('BUILTIN_SAFE', NULL, ?, 'CC0 Safe Library', ?, ?, -24.0)
                            """, (audio_file.stem, duration, str(audio_file.resolve())))
                except Exception:
                    pass

    def download_and_process_bgm(self, youtube_url: str) -> BgmTrackInfo:
        """
        Scarica esclusivamente lo stream audio da un link YouTube,
        normalizza a -24 LUFS con FFmpeg, rimuove i silenzi e memorizza nel DB.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute("SELECT * FROM bgm_tracks WHERE youtube_url = ?", (youtube_url,)).fetchone()
            if existing and os.path.exists(existing["file_path"]):
                return BgmTrackInfo(
                    id=existing["id"],
                    title=existing["title"],
                    youtube_url=existing["youtube_url"],
                    file_path=existing["file_path"],
                    duration_sec=existing["duration_sec"],
                    channel_name=existing["channel_name"] or "Unknown"
                )

        temp_dir = self.bgm_dir / "temp_dl"
        temp_dir.mkdir(parents=True, exist_ok=True)
        raw_audio_template = str(temp_dir / "%(id)s.%(ext)s")

        # 1. Metadati
        cmd_meta = ["yt-dlp", "--dump-json", "--no-playlist", youtube_url]
        meta_res = subprocess.run(cmd_meta, capture_output=True, text=True, check=True)
        info_json = json.loads(meta_res.stdout)
        title = info_json.get("title", "YouTube_BGM")
        channel = info_json.get("uploader", "YouTube")
        video_id = info_json.get("id", "temp_bgm")

        # 2. Download solo stream audio
        cmd_dl = [
            "yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", raw_audio_template, youtube_url
        ]
        subprocess.run(cmd_dl, check=True)
        raw_downloaded = str(temp_dir / f"{video_id}.mp3")

        # 3. Normalizzazione Loudness EBU R128 (-24 LUFS)
        final_filename = f"bgm_{video_id}_{int(info_json.get('duration', 0))}s.mp3"
        final_path = str(self.bgm_dir / final_filename)

        ffmpeg_bin, ffprobe_bin = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"
        ffprobe_cmd = ffprobe_bin if ffprobe_bin else "ffprobe"

        filter_chain = (
            "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-50dB,"
            "loudnorm=I=-24.0:TP=-1.5:LRA=11.0"
        )
        cmd_ffmpeg = [
            ffmpeg_cmd, "-y", "-i", raw_downloaded,
            "-af", filter_chain,
            "-ar", "48000", "-b:a", "320k",
            final_path
        ]
        subprocess.run(cmd_ffmpeg, check=True)

        # 4. Durata
        duration_sec = probe_media_duration(final_path)

        if os.path.exists(raw_downloaded):
            os.remove(raw_downloaded)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                INSERT OR REPLACE INTO bgm_tracks (youtube_url, title, channel_name, duration_sec, file_path, target_lufs)
                VALUES (?, ?, ?, ?, ?, -24.0)
            """, (youtube_url, title, channel, duration_sec, final_path))
            track_id = cur.lastrowid

        return BgmTrackInfo(
            id=track_id,
            title=title,
            youtube_url=youtube_url,
            file_path=final_path,
            duration_sec=duration_sec,
            channel_name=channel
        )

    def prepare_bgm_for_short(self, bgm_file_path: str, target_total_duration: float, output_prepared_wav: str) -> str:
        """Adatta la musica alla durata con loop continuo e fadeout finale 0.8s."""
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"

        fade_start = max(0.0, target_total_duration - 0.8)
        filter_str = (
            f"aloop=loop=-1:size=2e+09,atrim=0:{target_total_duration},"
            f"afade=t=out:st={fade_start}:d=0.8"
        )
        cmd = [
            ffmpeg_cmd, "-y", "-i", bgm_file_path,
            "-af", filter_str,
            "-ar", "48000", output_prepared_wav
        ]
        subprocess.run(cmd, check=True)
        return output_prepared_wav

    def mix_narration_and_bgm_ducking(
        self,
        voice_wav_path: str,
        bgm_wav_path: Optional[str],
        voice_duration_sec: float,
        output_mixed_audio: str,
        ducking_db: float = BGM_DUCKING_DB,
        intro_outro_db: float = BGM_INTRO_OUTRO_DB
    ):
        """
        Mixa la voce con lead-in 0.5s e outro 1.5s (+2.0s totale) e la musica di sottofondo (se presente).
        Applica auto-ducking morbido (150ms attack, 300ms release), normalize=0 e True Peak Limiter a -1.0 dB.
        Se bgm_wav_path è None (modalità No-BGM), applica solo il ritardo e il Limiter.
        """
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"

        total_dur = voice_duration_sec + (PADDING_INTRO_SEC + PADDING_OUTRO_SEC)

        # Caso 1: Nessuna Musica (Ottimizzato per Trend Sound Social)
        if not bgm_wav_path or not os.path.exists(bgm_wav_path):
            filter_chain = (
                f"[0:a]adelay=500|500,atrim=0:{total_dur:.3f},apad=whole_dur={total_dur:.3f},"
                f"alimiter=limit={TRUE_PEAK_LIMITER_DB}dB:attack=5:release=50:asc=1[out]"
            )
            cmd = [
                ffmpeg_cmd, "-y",
                "-i", voice_wav_path,
                "-filter_complex", filter_chain,
                "-map", "[out]",
                "-b:a", "320k",
                output_mixed_audio
            ]
            subprocess.run(cmd, check=True)
            return

        # Caso 2: Con Colonna Sonora e Ducking Morbido
        voice_start = PADDING_INTRO_SEC
        voice_end = voice_start + voice_duration_sec
        att_start = max(0.0, voice_start - 0.150)
        rel_end = min(total_dur, voice_end + 0.300)

        v_intro = 10 ** (intro_outro_db / 20.0)
        v_duck = 10 ** (ducking_db / 20.0)

        volume_expr = (
            f"volume='if(lt(t, {att_start:.3f}), {v_intro:.4f}, "
            f"if(lt(t, {voice_start:.3f}), {v_intro:.4f} + ({v_duck - v_intro:.4f})*(t - {att_start:.3f})/0.150, "
            f"if(lt(t, {voice_end:.3f}), {v_duck:.4f}, "
            f"if(lt(t, {rel_end:.3f}), {v_duck:.4f} + ({v_intro - v_duck:.4f})*(t - {voice_end:.3f})/0.300, "
            f"{v_intro:.4f}))))'"
        )

        filter_complex = (
            f"[0:a]adelay=500|500,apad=whole_dur={total_dur:.3f},atrim=0:{total_dur:.3f}[voice]; "
            f"[1:a]atrim=0:{total_dur:.3f},{volume_expr}[bgm]; "
            f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mixed]; "
            f"[mixed]alimiter=limit={TRUE_PEAK_LIMITER_DB}dB:attack=5:release=50:asc=1[out]"
        )

        cmd = [
            ffmpeg_cmd, "-y",
            "-i", voice_wav_path,
            "-i", bgm_wav_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-b:a", "320k",
            output_mixed_audio
        ]
        subprocess.run(cmd, check=True)

    def get_tracks(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM bgm_tracks WHERE status = 'DISPONIBILE' ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def list_available_tracks(self) -> List[BgmTrackInfo]:
        tracks = self.get_tracks()
        res = []
        for t in tracks:
            res.append(BgmTrackInfo(
                id=t["id"],
                title=t["title"],
                youtube_url=t.get("youtube_url"),
                file_path=t["file_path"],
                duration_sec=float(t["duration_sec"]),
                channel_name=t.get("channel_name") or "Unknown"
            ))
        return res

    def get_track_by_id(self, track_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM bgm_tracks WHERE id = ?", (track_id,)).fetchone()
            return dict(row) if row else None

    def download_and_normalize_youtube_audio(self, youtube_url: str) -> BgmTrackInfo:
        return self.download_and_process_bgm(youtube_url)

