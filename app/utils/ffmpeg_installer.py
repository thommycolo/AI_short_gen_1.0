"""AI Short Generator 1.0 - FFmpeg & FFprobe Runtime Discovery and Installer"""

import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from app.utils.logger import log

FFMPEG_PORTABLE_DIR = Path("app_data/bin")

def find_system_ffmpeg() -> Tuple[Optional[str], Optional[str]]:
    """Cerca ffmpeg e ffprobe nel sistema, dando precedenza a FFmpeg moderno locale o imageio-ffmpeg."""
    # 1. Cartella locale app_data/bin
    local_ffmpeg = FFMPEG_PORTABLE_DIR / "ffmpeg.exe"
    local_ffprobe = FFMPEG_PORTABLE_DIR / "ffprobe.exe"
    if local_ffmpeg.exists():
        _add_to_path(str(FFMPEG_PORTABLE_DIR.resolve()))
        return str(local_ffmpeg.resolve()), (str(local_ffprobe.resolve()) if local_ffprobe.exists() else None)

    # 2. imageio-ffmpeg se disponibile nell'ambiente Python
    try:
        import imageio_ffmpeg
        img_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if img_exe and os.path.exists(img_exe):
            _add_to_path(str(Path(img_exe).parent.resolve()))
            return str(img_exe), None
    except Exception:
        pass

    # 3. PATH di sistema
    ffmpeg_exe = shutil.which("ffmpeg")
    ffprobe_exe = shutil.which("ffprobe")
    if ffmpeg_exe and ffprobe_exe:
        return ffmpeg_exe, ffprobe_exe
    elif ffmpeg_exe:
        return ffmpeg_exe, None

    # 4. Posizioni note su Windows (KeyShot9 solo come ultimissimo fallback)
    known_locations = [
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links",
        Path("C:/Program Files/KeyShot9/bin"),
    ]
    for loc in known_locations:
        if (loc / "ffmpeg.exe").exists():
            ff = str(loc / "ffmpeg.exe")
            fp = str(loc / "ffprobe.exe") if (loc / "ffprobe.exe").exists() else None
            _add_to_path(str(loc.resolve()))
            return ff, fp

    return None, None

def find_system_ffprobe() -> Optional[str]:
    """Cerca ffprobe nel sistema."""
    ff, fp = find_system_ffmpeg()
    return fp

def _add_to_path(directory: str):
    if directory not in os.environ.get("PATH", ""):
        os.environ["PATH"] = directory + os.pathsep + os.environ.get("PATH", "")

def ensure_ffmpeg() -> bool:
    """Verifica la disponibilità di FFmpeg ed esegue un test di chiamata."""
    ffmpeg, ffprobe = find_system_ffmpeg()
    if ffmpeg:
        try:
            res = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True)
            if res.returncode == 0:
                log.info(f"FFmpeg rilevato correttamente: {ffmpeg}")
                return True
        except Exception as e:
            log.warning(f"Errore durante l'esecuzione di FFmpeg: {e}")
    return False

def probe_media_duration(file_path: str) -> float:
    """Rileva la durata di un file multimediale tramite ffprobe o fallback robusto su ffmpeg -i."""
    import json
    import re
    ffmpeg_bin, ffprobe_bin = find_system_ffmpeg()

    if ffprobe_bin:
        try:
            cmd = [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(file_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                dur = data.get("format", {}).get("duration")
                if dur:
                    return float(dur)
        except Exception:
            pass

    ffmpeg_cmd = ffmpeg_bin or "ffmpeg"
    try:
        cmd = [ffmpeg_cmd, "-i", str(file_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
        if m:
            hours = float(m.group(1))
            mins = float(m.group(2))
            secs = float(m.group(3))
            return hours * 3600 + mins * 60 + secs
    except Exception as e:
        log.warning(f"Errore rilevamento durata con FFmpeg: {e}")

    return 0.0

