import os
import re
import sys
import time
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any, Callable

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from dataclasses import dataclass
from app.config import (
    SCRIPTS_DB_PATH, VIDEO_POOL_DIR, PURGE_BASELINE_SEC,
    PURGE_TOLERANCE_MAX_SEC, PURGE_THRESHOLD_MAX, MIN_REEL_VIDEO_SEC,
    CATEGORIES, SCENE_SNAPPING_TOLERANCE_SEC, BIN_DIR, ensure_deno_binary
)
from app.core.scene_detector import SceneBoundaryDetector
from app.utils.ffmpeg_installer import find_system_ffmpeg, probe_media_duration
from app.utils.logger import log


@dataclass
class MasterVideoInfo:
    id: int
    title: str
    duration_sec: float
    category: str
    file_path: str
    status: str = "DISPONIBILE"



class ContinuousVideoPoolManager:
    """
    Gestisce il video pool continuo con Continuità Tematica per Categoria/Gioco,
    importazione a Ricodifica Zero (ingestion in 2-3s senza degradare il master),
    Scene Boundary Snapping vincolato ai bordi (Bounded Right Edge),
    fallback resiliente multi-browser per i cookie di YouTube,
    Segment Registry non-distruttivo e Garbage Collection (<= 1m 50s).
    """

    def __init__(self, db_path: str = SCRIPTS_DB_PATH, clips_dir: Path = VIDEO_POOL_DIR):
        self.db_path = db_path
        self.clips_dir = Path(clips_dir)
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.scene_detector = SceneBoundaryDetector(db_path=self.db_path)
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL CHECK(source_type IN ('LOCAL_FILE', 'YOUTUBE')),
                    source_uri TEXT NOT NULL,
                    video_title TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'General',
                    total_duration_sec REAL NOT NULL,
                    frontier_playhead_sec REAL DEFAULT 0.0,
                    available_duration_sec REAL NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('DISPONIBILE', 'PARZIALMENTE_USATO', 'ESAURITO', 'EPURATO')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_timeline_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL REFERENCES video_sources(id) ON DELETE CASCADE,
                    script_id INTEGER NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
                    start_time_sec REAL NOT NULL,
                    end_time_sec REAL NOT NULL,
                    allocated_duration_sec REAL NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('RESERVED', 'COMMITTED', 'FREED')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_video_sources_status ON video_sources(status, category, available_duration_sec);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_source_status ON video_timeline_segments(source_id, status);")

    @classmethod
    def classify_category(cls, title_or_filename: str) -> str:
        """Classifica automaticamente la categoria del video tramite parole chiave nel titolo."""
        t = title_or_filename.lower()
        if any(k in t for k in ["minecraft", "mc", "parkour", "bedwars", "hypixel"]):
            return "Minecraft"
        if any(k in t for k in ["subway", "surfer", "surfers"]):
            return "Subway Surfers"
        if any(k in t for k in ["gta", "grand theft auto", "fivem", "los santos", "franklin", "trevor"]):
            return "GTA V"
        if any(k in t for k in ["satisfying", "soap", "kinetic", "slime", "hydraulic", "oddly", "crush", "press"]):
            return "Satisfying"
        if any(k in t for k in ["nature", "drone", "mountain", "ocean", "aerial", "forest", "landscape", "waterfall"]):
            return "Drone/Nature"
        return "General"

    @staticmethod
    def _get_media_duration(file_path: str) -> float:
        return probe_media_duration(str(file_path))

    def import_local_video(self, local_file_path: str, category_override: Optional[str] = None) -> int:
        """
        INGESTION ULTRA-VELOCE A RICODIFICA ZERO (< 3 secondi):
        Non ricodifica il video locale all'importazione. Esegue ffprobe per la durata,
        determina la categoria e indicizza i cambi di scena in background.
        """
        path = Path(local_file_path)
        if not path.exists():
            raise FileNotFoundError(f"File video locale non trovato: {local_file_path}")

        total_dur = self._get_media_duration(str(path))
        if total_dur < MIN_REEL_VIDEO_SEC:
            raise ValueError(f"Il video dura meno di {MIN_REEL_VIDEO_SEC}s e non può ospitare uno Short.")

        video_title = path.stem
        category = category_override or self.classify_category(video_title)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.execute("""
                INSERT INTO video_sources (
                    source_type, source_uri, video_title, category,
                    total_duration_sec, frontier_playhead_sec, available_duration_sec,
                    file_path, status
                ) VALUES ('LOCAL_FILE', ?, ?, ?, ?, 0.0, ?, ?, 'DISPONIBILE')
            """, (str(path.resolve()), video_title, category, total_dur, total_dur, str(path.resolve())))
            source_id = cur.lastrowid

        # Analisi confini di scena senza transcodifica
        self.scene_detector.detect_and_store_boundaries(source_id, str(path.resolve()))
        return source_id

    def ingest_master_video(self, local_file_path: str, category: Optional[str] = None) -> MasterVideoInfo:
        """
        Ingestion a ricodifica zero (< 3s) del video master locale:
        Restituisce MasterVideoInfo contenente metadati completi (title, duration_sec, category, file_path).
        """
        source_id = self.import_local_video(local_file_path, category_override=category)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM video_sources WHERE id = ?", (source_id,)).fetchone()
            if row:
                return MasterVideoInfo(
                    id=row["id"],
                    title=row["video_title"],
                    duration_sec=float(row["total_duration_sec"]),
                    category=row["category"],
                    file_path=row["file_path"],
                    status=row["status"]
                )
        p = Path(local_file_path)
        return MasterVideoInfo(
            id=source_id,
            title=p.stem,
            duration_sec=self._get_media_duration(local_file_path),
            category=category or self.classify_category(p.stem),
            file_path=str(p.resolve())
        )

    def _resolve_browser_cookies(self, preferred_browser: Optional[str] = "firefox", cookies_file: Optional[str] = None) -> List[str]:
        """Fallback progressivo per i cookie YouTube: cookies.txt -> Firefox -> Chrome -> Edge -> Brave."""
        if cookies_file and os.path.exists(cookies_file):
            return ["--cookies", cookies_file]
        candidate_browsers = [preferred_browser, "firefox", "chrome", "edge", "brave"]
        seen = set()
        unique_browsers = [b for b in candidate_browsers if b and not (b in seen or seen.add(b))]
        for b in unique_browsers:
            try:
                test_cmd = ["yt-dlp", "--cookies-from-browser", b, "--dump-user-agent"]
                res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=3.0)
                if res.returncode == 0:
                    return ["--cookies-from-browser", b]
            except Exception:
                continue
        return []

    def download_youtube_video(
        self,
        youtube_url: str,
        preferred_browser: Optional[str] = "firefox",
        cookies_file: Optional[str] = None,
        category_override: Optional[str] = None,
        progress_callback: Optional[Callable[[dict], None]] = None
    ) -> int:
        """
        Download resiliente da YouTube con yt_dlp nativo Python, fallback cookie e zero ricodifica.
        Elimina alla radice WinError 2 e 'Could not write header' per codec/nomi file non validi su Windows.
        """
        temp_id = int(time.time() * 1000) % 10000000
        # Assicura presenza del runtime JS Deno in BIN_DIR per risolvere i challenge anti-bot di YouTube
        ensure_deno_binary()

        # Nome file pulito e sicuro su Windows (evita caratteri come ':', '?', ecc. nel titolo)
        out_template = str(self.clips_dir / f"yt_master_{temp_id}.%(ext)s")
        video_title = "YouTube_Master_Video"
        downloaded_file = None

        ffmpeg_bin, _ = find_system_ffmpeg()

        if yt_dlp is not None:
            # Priorità a video AVC/H.264 e audio AAC per muxing immediato compatibile senza ricodifica
            base_opts = {
                'format': 'bv*[vcodec*=avc]+ba[acodec*=mp4a]/bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best',
                'outtmpl': out_template,
                'merge_output_format': 'mp4',
                'windowsfilenames': True,
                'restrictfilenames': True,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'remote_components': ['ejs:github'],
            }
            if ffmpeg_bin:
                base_opts['ffmpeg_location'] = ffmpeg_bin
                base_opts['postprocessor_args'] = {
                    'Merger': ['-c:v', 'copy', '-c:a', 'aac']
                }

            if progress_callback:
                def _yt_progress_hook(d):
                    try:
                        progress_callback(d)
                    except Exception:
                        pass

                def _yt_pp_hook(d):
                    try:
                        pp_status = d.get('status')
                        if pp_status == 'started':
                            progress_callback({'status': 'postprocessing', 'msg': 'Muxing MP4 / Post-elaborazione...'})
                        elif pp_status == 'finished':
                            progress_callback({'status': 'postprocessing', 'msg': 'Muxing completato.'})
                    except Exception:
                        pass

                base_opts['progress_hooks'] = [_yt_progress_hook]
                base_opts['postprocessor_hooks'] = [_yt_pp_hook]

            if cookies_file and os.path.exists(cookies_file):
                base_opts['cookiefile'] = cookies_file

            ydl_opts = dict(base_opts)
            if preferred_browser and preferred_browser != "cookies.txt":
                ydl_opts['cookiesfrombrowser'] = (preferred_browser,)

            info = None
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_url, download=True)
            except Exception as e_browser:
                log.info(f"Tentativo con browser cookies non riuscito ({e_browser}), procedo con download diretto...")
                if 'cookiesfrombrowser' in ydl_opts:
                    with yt_dlp.YoutubeDL(base_opts) as ydl:
                        info = ydl.extract_info(youtube_url, download=True)
                else:
                    raise e_browser

            if info:
                video_title = info.get("title", video_title)
                if "requested_downloads" in info and info["requested_downloads"]:
                    downloaded_file = info["requested_downloads"][0].get("filepath")
                elif "_filename" in info:
                    downloaded_file = info["_filename"]
        else:
            cookie_args = []
            if cookies_file and os.path.exists(cookies_file):
                cookie_args = ["--cookies", cookies_file]
            elif preferred_browser and preferred_browser != "cookies.txt":
                cookie_args = ["--cookies-from-browser", preferred_browser]

            out_path = str(self.clips_dir / f"yt_master_{temp_id}.mp4")
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", "bv*[vcodec*=avc]+ba[acodec*=mp4a]/bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "--windows-filenames",
                "--restrict-filenames",
                "--remote-components", "ejs:github",
                *cookie_args,
                "-o", out_path,
            ]
            if ffmpeg_bin:
                cmd.extend(["--ffmpeg-location", ffmpeg_bin])
            cmd.append(youtube_url)

            if progress_callback:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in proc.stdout:
                    m = re.search(r"\[download\]\s+([\d\.]+)%\s+of\s+([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)", line)
                    if m:
                        pct = float(m.group(1))
                        progress_callback({
                            'status': 'downloading',
                            '_percent_str': f"{pct:.1f}%",
                            '_total_bytes_str': m.group(2),
                            '_speed_str': m.group(3),
                            '_eta_str': m.group(4),
                            'downloaded_bytes': int(pct),
                            'total_bytes': 100,
                        })
                proc.wait()
                if proc.returncode != 0:
                    raise RuntimeError(f"yt-dlp subprocess fallito con codice {proc.returncode}")
            else:
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0 and cookie_args:
                    cmd_no_cookie = [c for c in cmd if c not in cookie_args]
                    subprocess.run(cmd_no_cookie, check=True)
            downloaded_file = out_path

        # Localizza file scaricato su disco
        if not downloaded_file or not os.path.exists(downloaded_file):
            matched = list(self.clips_dir.glob(f"*{temp_id}*"))
            if matched:
                downloaded_file = str(matched[0].resolve())
            else:
                raise FileNotFoundError(f"Download non riuscito: file video non trovato su disco per {youtube_url}")

        final_video_path = str(Path(downloaded_file).resolve())
        category = category_override or self.classify_category(video_title)

        total_dur = self._get_media_duration(final_video_path)
        if total_dur < MIN_REEL_VIDEO_SEC:
            if os.path.exists(final_video_path):
                os.remove(final_video_path)
            raise ValueError(f"Il video dura meno di {MIN_REEL_VIDEO_SEC}s.")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.execute("""
                INSERT INTO video_sources (
                    source_type, source_uri, video_title, category,
                    total_duration_sec, frontier_playhead_sec, available_duration_sec,
                    file_path, status
                ) VALUES ('YOUTUBE', ?, ?, ?, ?, 0.0, ?, ?, 'DISPONIBILE')
            """, (youtube_url, video_title, category, total_dur, total_dur, final_video_path))
            source_id = cur.lastrowid

        if progress_callback:
            progress_callback({
                'status': 'ingestion',
                'msg': 'Rilevamento confini di scena e registrazione nel pool...'
            })

        self.scene_detector.detect_and_store_boundaries(source_id, final_video_path)
        return source_id

    def find_free_interval_in_pool(self, source_id: int, required_duration: float) -> Optional[Tuple[float, float]]:
        """
        Temporal Free-List Allocation (Best-Fit):
        Cerca tra i 'buchi' temporali liberati da annullamenti precedenti uno slot contiguo
        [gap_start, gap_end] con ampiezza >= required_duration.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.execute("""
                SELECT start_time_sec, end_time_sec FROM video_timeline_segments
                WHERE source_id = ? AND status = 'COMMITTED'
                ORDER BY start_time_sec ASC
            """, (source_id,))
            committed = cur.fetchall()

            src = conn.execute("SELECT frontier_playhead_sec FROM video_sources WHERE id = ?", (source_id,)).fetchone()
            if not src:
                return None

            gaps: List[Tuple[float, float, float]] = []
            last_end = 0.0
            for seg in committed:
                if seg["start_time_sec"] > last_end + 0.1:
                    gap_size = seg["start_time_sec"] - last_end
                    if gap_size >= required_duration:
                        gaps.append((last_end, seg["start_time_sec"], gap_size))
                last_end = max(last_end, seg["end_time_sec"])

            if gaps:
                gaps.sort(key=lambda g: g[2]) # Best-fit: buco più piccolo che soddisfa
                best_gap = gaps[0]
                return best_gap[0], best_gap[1]

        return None

    def reserve_segment_for_story(
        self,
        source_id: int,
        script_id: int,
        duration_sec: float
    ) -> Tuple[float, float]:
        """
        Riserva un intervallo temporale continuo:
        1. Verifica prima la Free-List per riutilizzare gap orfani (Best-Fit).
        2. In caso di slot libero da gap, applica il VINCOLO BORDO DESTRO LIMITATO:
           end_time_sec = min(snapped_end, slot_right_boundary)
        3. Se nessun gap soddisfa la durata, avanza frontier_playhead_sec.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            src = conn.execute("SELECT * FROM video_sources WHERE id = ?", (source_id,)).fetchone()
            if not src:
                raise ValueError(f"Sorgente video #{source_id} non trovata.")

            # Tentativo 1: Free-List Gap con Bounded Right Edge
            free_slot = self.find_free_interval_in_pool(source_id, duration_sec)
            if free_slot:
                start_t, slot_right_boundary = free_slot
                raw_end_t = start_t + duration_sec
                snapped_end_t = self.scene_detector.snap_to_nearest_scene_boundary(
                    source_id, raw_end_t, tolerance_sec=SCENE_SNAPPING_TOLERANCE_SEC
                )
                end_t = min(snapped_end_t, slot_right_boundary)
                actual_dur = end_t - start_t
                conn.execute("""
                    INSERT INTO video_timeline_segments (
                        source_id, script_id, start_time_sec, end_time_sec, allocated_duration_sec, status
                    ) VALUES (?, ?, ?, ?, ?, 'COMMITTED')
                """, (source_id, script_id, start_t, end_t, actual_dur))
                return start_t, end_t

            # Tentativo 2: Espansione frontiera lineare
            start_t = src["frontier_playhead_sec"]
            raw_end_t = start_t + duration_sec
            end_t = self.scene_detector.snap_to_nearest_scene_boundary(
                source_id, raw_end_t, tolerance_sec=SCENE_SNAPPING_TOLERANCE_SEC
            )
            actual_dur = end_t - start_t

            if actual_dur > src["available_duration_sec"]:
                raise RuntimeError(f"Durata continua insufficiente su sorgente #{source_id}.")

            new_frontier = end_t
            new_avail = max(0.0, src["total_duration_sec"] - new_frontier)

            conn.execute("""
                INSERT INTO video_timeline_segments (
                    source_id, script_id, start_time_sec, end_time_sec, allocated_duration_sec, status
                ) VALUES (?, ?, ?, ?, ?, 'COMMITTED')
            """, (source_id, script_id, start_t, end_t, actual_dur))

            # Verifica Garbage Collection (<= 110s)
            if new_avail <= PURGE_THRESHOLD_MAX:
                conn.execute("""
                    UPDATE video_sources
                    SET frontier_playhead_sec = ?, available_duration_sec = 0.0, status = 'EPURATO'
                    WHERE id = ?
                """, (new_frontier, source_id))
            else:
                conn.execute("""
                    UPDATE video_sources
                    SET frontier_playhead_sec = ?, available_duration_sec = ?, status = 'PARZIALMENTE_USATO'
                    WHERE id = ?
                """, (new_frontier, new_avail, source_id))

            return start_t, end_t

    def get_sources(self, category: Optional[str] = None, available_only: bool = True) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            q = "SELECT * FROM video_sources WHERE 1=1"
            params = []
            if available_only:
                q += " AND status IN ('DISPONIBILE', 'PARZIALMENTE_USATO') AND available_duration_sec >= ?"
                params.append(MIN_REEL_VIDEO_SEC)
            if category and category != "General":
                q += " AND category = ?"
                params.append(category)
            q += " ORDER BY id DESC"
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]

    def get_all_sources(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 30000;")
            rows = conn.execute("SELECT * FROM video_sources ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_source(self, source_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("DELETE FROM video_sources WHERE id = ?", (source_id,))

    def get_pool_status_for_category(self, category: str) -> Dict[str, Any]:
        """Ritorna statistiche e miglior video disponibile per la categoria."""
        sources = self.get_sources(category=category, available_only=True)
        if not sources and category != "General":
            sources = self.get_sources(category="General", available_only=True)
            if not sources:
                sources = self.get_sources(category=None, available_only=True)

        total_avail = sum(s.get("available_duration_sec", 0.0) for s in sources)
        best_title = sources[0]["video_title"] if sources else "Nessun video idoneo"
        best_path = sources[0]["file_path"] if sources else ""

        return {
            "total_available_sec": total_avail,
            "best_video_title": best_title,
            "best_master_path": best_path,
            "source_count": len(sources)
        }
