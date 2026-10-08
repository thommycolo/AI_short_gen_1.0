"""AI Short Generator 1.0 - Zero-Latency Native Audio Player Helper"""

import os
import sys
from pathlib import Path
from typing import Optional

def play_wav_file(wav_path: str):
    """
    Riproduce un file WAV con latenza zero (~0ms) su Windows tramite Win32 PlaySound.
    Non avvia processi PowerShell pesanti né blocca il main thread della GUI.
    """
    if not wav_path or not os.path.exists(wav_path):
        return

    if sys.platform == "win32":
        try:
            import winsound
            winsound.PlaySound(str(wav_path), winsound.SND_ASYNC | winsound.SND_FILENAME)
            return
        except Exception:
            pass

    # Fallback con ffplay
    try:
        from app.utils.ffmpeg_installer import find_system_ffmpeg
        import subprocess
        ff = find_system_ffmpeg()
        if isinstance(ff, tuple):
            ff = ff[0]
        if ff:
            ffplay = str(Path(ff).parent / "ffplay.exe") if sys.platform == "win32" else "ffplay"
            if os.path.exists(ffplay) or sys.platform != "win32":
                creationflags = 0x08000000 if sys.platform == "win32" else 0
                subprocess.Popen(
                    [ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)],
                    creationflags=creationflags
                )
    except Exception:
        pass


def stop_wav_playback():
    """Arresta immediatamente l'audio in riproduzione."""
    if sys.platform == "win32":
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

