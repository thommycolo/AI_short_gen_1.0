"""AI Short Generator 1.0 - File Management Utilities & Windows Anti-Lock Safeguards"""

import os
import gc
import time
import glob
from pathlib import Path
from typing import Union, List

def safe_delete_file_with_retry(file_path: Union[str, Path], retries: int = 6, delay: float = 0.35) -> bool:
    """
    Risolve il blocco file esclusivo di Windows (WinError 32: 'The process cannot access the file...').
    Esegue una garbage collection forzata per rilasciare handle aperti di soundfile/wave/ffmpeg,
    seguita da retry con backoff esponenziale.
    """
    p = Path(file_path)
    if not p.exists():
        return True

    gc.collect()
    current_delay = delay
    for attempt in range(retries):
        try:
            p.unlink(missing_ok=True)
            return True
        except PermissionError:
            time.sleep(current_delay)
            current_delay *= 1.5
            gc.collect()
        except OSError:
            time.sleep(current_delay)
            gc.collect()
    return not p.exists()

def cleanup_story_temp_files(story_id: int):
    """Pulisce tutti i file intermedi temporanei associati a uno script/storia."""
    patterns = [
        f"app_data/cache/*{story_id}*.*",
        f"app_data/renders/temp_output_{story_id}.part.mp4",
        f"app_data/cache/review_{story_id}_*.jpg",
        f"app_data/cache/story_{story_id}_*.jpg",
        f"app_data/cache/temp_{story_id}*.ass",
        f"app_data/cache/temp_audio_{story_id}*.wav"
    ]
    for pattern in patterns:
        for file_match in glob.glob(pattern):
            safe_delete_file_with_retry(file_match)

def sanitize_ffmpeg_path(file_path: Union[str, Path]) -> str:
    """
    Normalizza i percorsi Windows per i filtri FFmpeg (subtitles=...):
    1. Converte tutti i backslash in slash /.
    2. Esegue l'escape dei due punti dell'unità disco (C: -> C\\:),
       scongiurando l'errore 'Unable to parse option value'.
    """
    posix = Path(file_path).resolve().as_posix()
    return posix.replace(":", r"\:")

