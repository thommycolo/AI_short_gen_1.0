"""AI Short Generator 1.0 - Scene Boundary Detector & Snapping Engine"""

import re
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Optional
from app.config import SCRIPTS_DB_PATH, SCENE_SNAPPING_TOLERANCE_SEC
from app.utils.ffmpeg_installer import find_system_ffmpeg


class SceneBoundaryDetector:
    """
    Rileva e indicizza i cambi di scena del video master continuo tramite FFmpeg
    e fornisce lo snapping intelligente dei tagli entro +-0.200s (200ms assorbiti nel padding).
    """

    def __init__(self, db_path: str = SCRIPTS_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_scene_boundaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES video_sources(id) ON DELETE CASCADE,
                    boundary_time_sec REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scene_boundaries ON video_scene_boundaries(source_id, boundary_time_sec);")

    def detect_and_store_boundaries(self, source_id: int, video_path: str) -> List[float]:
        """Estrae i timestamp dei cambi di inquadratura con FFmpeg per lo Scene Boundary Snapping."""
        ffmpeg_bin, _ = find_system_ffmpeg()
        ffmpeg_cmd = ffmpeg_bin if ffmpeg_bin else "ffmpeg"
        boundaries: List[float] = []

        try:
            cmd = [
                ffmpeg_cmd, "-i", str(video_path),
                "-vf", "select='gt(scene,0.35)',showinfo",
                "-f", "null", "-"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            pts_times = re.findall(r'pts_time:([0-9.]+)', res.stderr)
            boundaries = [float(t) for t in pts_times if float(t) > 1.0]

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA busy_timeout = 30000;")
                for b_time in boundaries:
                    conn.execute("""
                        INSERT INTO video_scene_boundaries (source_id, boundary_time_sec)
                        VALUES (?, ?)
                    """, (source_id, b_time))
        except Exception:
            pass

        return boundaries

    def snap_to_nearest_scene_boundary(
        self,
        source_id: int,
        target_time_sec: float,
        tolerance_sec: float = SCENE_SNAPPING_TOLERANCE_SEC
    ) -> float:
        """
        Aggancia il punto di taglio a un cambio inquadratura SOLO entro una micro-tolleranza di +-0.200s (200ms).
        I <= 200ms di micro-delta vengono assorbiti invisibilmente nei 1.5s di outro padding.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.execute("""
                SELECT boundary_time_sec FROM video_scene_boundaries
                WHERE source_id = ? AND ABS(boundary_time_sec - ?) <= ?
                ORDER BY ABS(boundary_time_sec - ?) ASC LIMIT 1
            """, (source_id, target_time_sec, tolerance_sec, target_time_sec))
            row = cur.fetchone()
            if row:
                return float(row[0])
        return target_time_sec

