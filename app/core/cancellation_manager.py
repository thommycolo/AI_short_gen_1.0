"""AI Short Generator 1.0 - Production Cancellation Manager & Atomic Granular Rollback"""

import os
import glob
import sqlite3
import subprocess
import threading
from pathlib import Path
from typing import List, Optional

from app.config import SCRIPTS_DB_PATH, PURGE_THRESHOLD_MAX
from app.utils.file_manager import safe_delete_file_with_retry, cleanup_story_temp_files


class ProductionCancellationManager:
    """
    Gestisce l'interruzione immediata dei processi di generazione
    e il rollback atomico non-distruttivo tramite Segment Registry e Free-List.
    Risolve le collisioni di lock file Windows (WinError 32) tramite retry ed exponential backoff.
    """

    def __init__(self, db_path: str = SCRIPTS_DB_PATH):
        self.db_path = db_path
        self._cancel_requested = threading.Event()
        self._current_ffmpeg_popen: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def reset(self):
        self._cancel_requested.clear()
        self._current_ffmpeg_popen = None

    def request_cancellation(self):
        """Segnala la richiesta di stop immediato e termina forzatamente l'albero di processi FFmpeg attivo."""
        self._cancel_requested.set()
        with self._lock:
            if self._current_ffmpeg_popen and self._current_ffmpeg_popen.poll() is None:
                pid = self._current_ffmpeg_popen.pid
                try:
                    # Chiusura albero processi su Windows (/T = tree, /F = force)
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                except Exception:
                    try:
                        self._current_ffmpeg_popen.kill()
                    except Exception:
                        pass

    def is_cancelled(self) -> bool:
        return self._cancel_requested.is_set()

    def register_ffmpeg_process(self, popen_instance: subprocess.Popen):
        with self._lock:
            self._current_ffmpeg_popen = popen_instance

    def unregister_ffmpeg_process(self):
        with self._lock:
            self._current_ffmpeg_popen = None

    def execute_granular_rollback(
        self,
        completed_story_ids: List[int],
        uncompleted_story_ids: List[int]
    ):
        """
        Esegue il rollback non-distruttivo con Segment Registry:
        1. Mantiene lo stato UTILIZZATO per le storie completate al 100%.
        2. Ripristina DISPONIBILE per gli script non completati (o parziali).
        3. Rimuove chirurgicamente i soli segmenti assegnati alle storie annullate;
           gli intervalli liberati diventano immediatamente disponibili per la Free-List (Best-Fit).
        4. Se la sorgente non ha segmenti successivi, arretra frontier_playhead_sec.
        5. Cancella file temporanei e Short parziali con safe_delete_file_with_retry (anti WinError 32).
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("BEGIN IMMEDIATE TRANSACTION;")
            try:
                for script_id in uncompleted_story_ids:
                    # A. Ripristino Script non completato -> DISPONIBILE
                    conn.execute("""
                        UPDATE scripts SET status = 'DISPONIBILE', used_at = NULL WHERE id = ?
                    """, (script_id,))

                    # B. Individuazione sorgenti coinvolte nei segmenti da annullare
                    cur = conn.execute("""
                        SELECT DISTINCT source_id FROM video_timeline_segments WHERE script_id = ?
                    """, (script_id,))
                    affected_sources = [r[0] for r in cur.fetchall()]

                    # C. Eliminazione chirurgica dei soli segmenti appartenenti allo script annullato
                    conn.execute("""
                        DELETE FROM video_timeline_segments WHERE script_id = ?
                    """, (script_id,))

                    # D. Ricalcolo non-distruttivo della frontiera per ciascuna sorgente
                    for src_id in affected_sources:
                        cur = conn.execute("""
                            SELECT COALESCE(MAX(end_time_sec), 0.0) FROM video_timeline_segments
                            WHERE source_id = ? AND status = 'COMMITTED'
                        """, (src_id,))
                        max_committed_end = cur.fetchone()[0]

                        cur_src = conn.execute("SELECT total_duration_sec, frontier_playhead_sec FROM video_sources WHERE id = ?", (src_id,))
                        src_row = cur_src.fetchone()
                        if src_row:
                            total_dur = src_row[0]
                            current_frontier = src_row[1]

                            new_frontier = max_committed_end if max_committed_end < current_frontier else current_frontier
                            new_avail = max(0.0, total_dur - new_frontier)

                            status_val = 'EPURATO' if new_avail <= PURGE_THRESHOLD_MAX and new_frontier > 0 else (
                                'PARZIALMENTE_USATO' if new_frontier > 0 else 'DISPONIBILE'
                            )

                            conn.execute("""
                                UPDATE video_sources
                                SET frontier_playhead_sec = ?,
                                    available_duration_sec = ?,
                                    status = ?
                                WHERE id = ?
                            """, (new_frontier, new_avail, status_val, src_id))

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e

        # E. Pulizia file su disco con protezione anti-lock Windows
        for script_id in uncompleted_story_ids:
            cleanup_story_temp_files(script_id)
            mp4_pattern = f"app_data/renders/*story_{script_id}*.mp4"
            for mp4_file in glob.glob(mp4_pattern):
                safe_delete_file_with_retry(mp4_file)
            part_pattern = f"app_data/renders/*part*_{script_id}.mp4"
            for mp4_file in glob.glob(part_pattern):
                safe_delete_file_with_retry(mp4_file)

