"""AI Short Generator 1.0 - Configurazione Globale & Parametri di Sistema"""

import os
from pathlib import Path
from typing import Optional

# --- DIRECTORY PRINCIPALI ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DATA_DIR = PROJECT_ROOT / "app_data"
ASSETS_DIR = PROJECT_ROOT / "assets"

SCRIPTS_DB_PATH = str(APP_DATA_DIR / "scripts_history.db")
VIDEO_POOL_DIR = APP_DATA_DIR / "video_pool"
BGM_LIBRARY_DIR = APP_DATA_DIR / "bgm_library"
RENDERS_DIR = APP_DATA_DIR / "renders"
CACHE_DIR = APP_DATA_DIR / "cache"
MODELS_DIR = APP_DATA_DIR / "models"
VOICE_PROFILES_DIR = APP_DATA_DIR / "voice_profiles"

FONTS_DIR = ASSETS_DIR / "fonts"
ICONS_DIR = ASSETS_DIR / "icons"
PRESETS_DIR = ASSETS_DIR / "presets"
BGM_SAFE_DIR = ASSETS_DIR / "bgm_safe"

# Assicurazione esistenza cartelle
BIN_DIR = APP_DATA_DIR / "bin"
for directory in [APP_DATA_DIR, BIN_DIR, MODELS_DIR, VIDEO_POOL_DIR, BGM_LIBRARY_DIR, RENDERS_DIR, CACHE_DIR,
                  VOICE_PROFILES_DIR, FONTS_DIR, ICONS_DIR, PRESETS_DIR, BGM_SAFE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Assicura che i binari portabili (ffmpeg, sox, deno) siano prioritari nel PATH di sistema
_bin_str = str(BIN_DIR.resolve())
if _bin_str not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _bin_str + os.pathsep + os.environ.get("PATH", "")

# Assicura caricamento librerie CUDA (cublas64_12.dll per faster-whisper e CTranslate2)
try:
    import torch
    _t_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.exists(_t_lib):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_t_lib)
        if _t_lib not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _t_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

# Patch compatibilità per PyAV (14+) che non accetta metadata_errors in av.open
try:
    import av
    if hasattr(av, "open"):
        _orig_av_open = av.open
        def _safe_av_open(*args, **kwargs):
            kwargs.pop("metadata_errors", None)
            return _orig_av_open(*args, **kwargs)
        av.open = _safe_av_open
except Exception:
    pass


def ensure_deno_binary() -> Optional[Path]:
    """Assicura che il runtime JavaScript Deno sia presente in BIN_DIR per risolvere le sfide anti-bot n-sig di YouTube con yt-dlp."""
    deno_exe = BIN_DIR / "deno.exe"
    if deno_exe.exists():
        return deno_exe
    try:
        import urllib.request, zipfile, io
        url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            z = zipfile.ZipFile(io.BytesIO(resp.read()))
            z.extractall(BIN_DIR)
        return deno_exe if deno_exe.exists() else None
    except Exception:
        return None


# Disabilita warning symlink di Hugging Face su Windows (evita UserWarning a ogni download modello)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# --- METRICHE TEMPORALI & SPEECH UNIFICATO ---
DEFAULT_WPS = 2.50               # 150 WPM / 60 secondi = 2.50 parole/sec (American English)
PADDING_INTRO_SEC = 0.500        # Anticipo video lead-in prima dell'inizio voce
PADDING_OUTRO_SEC = 1.500        # Coda video dopo stacco voce
PADDING_TOTAL_SEC = PADDING_INTRO_SEC + PADDING_OUTRO_SEC # 2.000s esatti

TARGET_VIDEO_MAX_SEC = 45.0      # Durata massima reel video
AUDIO_MAX_SEC = TARGET_VIDEO_MAX_SEC - PADDING_TOTAL_SEC  # 43.0s

ALLOWED_CHUNKING_DELTA_SEC = 7.0 # Finestra discorsiva +-7s
MIN_REEL_VIDEO_SEC = 38.0        # 45.0s - 7.0s
MAX_REEL_VIDEO_SEC = 45.0
MIN_REEL_AUDIO_SEC = MIN_REEL_VIDEO_SEC - PADDING_TOTAL_SEC # 36.0s
MAX_REEL_AUDIO_SEC = MAX_REEL_VIDEO_SEC - PADDING_TOTAL_SEC # 43.0s

# --- TIMING BANNER & REVISIONI ---
INTRO_BANNER_START_SEC = 0.000
INTRO_BANNER_END_SEC = 1.500
OUTRO_CTA_LEAD_TIME_SEC = 1.000  # CTA entra esattamente a T_video - 1.000s
REVIEW_FRAME_TIMESTAMP_SEC = 0.600 # Campionamento a t = 0.600s (+100ms su inizio voce)

# --- DIMENSIONI VIDEO & TIPOGRAFIA (9:16) ---
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
TARGET_FPS = 60

SUBTITLE_SAFE_WIDTH_PX = 880     # Larghezza massima geometrica linea (ImageFont.getlength)
SUBTITLE_MAX_WORDS_PER_LINE = 3
SUBTITLE_MAX_LINES = 2
DEFAULT_MARGIN_V = 440           # Basso Alignment 2 per TikTok / Reels / Shorts

DEFAULT_FONT_NAME = "Montserrat Black"
DEFAULT_FONT_SIZE = 68
DEFAULT_TEXT_COLOR = "#DCE0EA"      # Perla Morbido
DEFAULT_HIGHLIGHT_COLOR = "#DCE0EA" # Uniforme con il colore del testo (Nessuna evidenziazione)
DEFAULT_OUTLINE_COLOR = "#181A20"   # Ardesia Scura
DEFAULT_OUTLINE_WIDTH = 0
DEFAULT_SHADOW_RADIUS = 0

# --- GARBAGE COLLECTOR VIDEO & SNAPPING ---
PURGE_BASELINE_SEC = 90.0          # 1 minuto e 30 secondi
PURGE_TOLERANCE_MAX_SEC = 20.0     # +20 secondi
PURGE_THRESHOLD_MAX = PURGE_BASELINE_SEC + PURGE_TOLERANCE_MAX_SEC # 110.0s (1m 50s)
SCENE_SNAPPING_TOLERANCE_SEC = 0.200 # Micro-snapping entro 200ms

CATEGORIES = [
    "Minecraft",
    "Subway Surfers",
    "Satisfying",
    "GTA V",
    "Drone/Nature",
    "General"
]

# --- AUDIO & MASTERING BGM ---
BGM_TARGET_LUFS = -24.0
BGM_DUCKING_DB = -22.0
BGM_INTRO_OUTRO_DB = -14.0
BGM_DUCKING_ATTACK_SEC = 0.150
BGM_DUCKING_RELEASE_SEC = 0.300
TRUE_PEAK_LIMITER_DB = -1.0

# --- HARDWARE & VRAM LIFECYCLE (LA MATEMATICA DEI 4.0 GB) ---
VRAM_MAX_CEILING_MB = 4000.0       # Tetto massimo totale scheda GPU
VRAM_WINDOWS_DWM_MB = 1200.0       # Riserva DWM Windows 11 + PySide6
VRAM_APP_NET_BUDGET_MB = 2800.0    # Budget netto applicazione: 2.800 MB (2,8 GB)
CUDA_PER_PROCESS_MEMORY_FRACTION = 0.70 # Cap allocatore PyTorch 70% su 8GB (5.6 GB max) per modello neurale Qwen3-TTS (3.89 GB) lasciando >2.4 GB a DWM

# --- SPEAKER DEFAULT & PRESET QWEN3-TTS (en-US) ---
DEFAULT_SPEAKER = "Ryan"           # American Natural Warm Male
DEFAULT_FEMALE_SPEAKER = "Vivian"  # American Warm Female
DEFAULT_NARRATOR_SPEAKER = "Aiden" # Dynamic Young US Narrator
DEFAULT_INSTRUCT = "High energy viral creator voice, fast paced, emphasizing keywords"

# --- COMPATIBILITY ALIASES ---
MIN_SHORT_DURATION_SEC = MIN_REEL_VIDEO_SEC
MAX_SHORT_DURATION_SEC = MAX_REEL_VIDEO_SEC
TOTAL_PADDING_SEC = PADDING_TOTAL_SEC
TARGET_WIDTH = CANVAS_WIDTH
TARGET_HEIGHT = CANVAS_HEIGHT
GC_DISCARD_BASELINE_SEC = PURGE_BASELINE_SEC
GC_UPPER_TOLERANCE_SEC = PURGE_TOLERANCE_MAX_SEC
GC_MAX_THRESHOLD_SEC = PURGE_THRESHOLD_MAX
HARDWARE_VRAM_NET_LIMIT_MB = int(VRAM_APP_NET_BUDGET_MB)
HARDWARE_VRAM_TOTAL_BUDGET_MB = int(VRAM_MAX_CEILING_MB)
NVENC_PRESET = "p5"
NVENC_CQ = 18
WHISPER_MODEL_NAME = "large-v3-turbo"
MODELS_DIR = APP_DATA_DIR / "models"
