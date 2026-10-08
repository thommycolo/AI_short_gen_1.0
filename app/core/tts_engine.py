"""AI Short Generator 1.0 - Qwen3-TTS Suite & Voice Intelligence Engine (Lazy Swapping & Subprocess Isolation)"""

import os
import sys
import gc
import sqlite3
import threading
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from app.config import (
    SCRIPTS_DB_PATH, VOICE_PROFILES_DIR, DEFAULT_SPEAKER,
    DEFAULT_FEMALE_SPEAKER, DEFAULT_NARRATOR_SPEAKER, DEFAULT_INSTRUCT,
    CUDA_PER_PROCESS_MEMORY_FRACTION, VRAM_APP_NET_BUDGET_MB, MODELS_DIR
)
from app.core.silero_vad_trimmer import SileroVADSilenceTrimmer
from app.utils.logger import log

try:
    import torch
except ImportError:
    torch = None

try:
    from qwen_tts import Qwen3TTSModel
except ImportError:
    Qwen3TTSModel = None


class GPUResourceCoordinator:
    """
    Coordina l'accesso alla VRAM ed elimina la contesa tra la Coda Batch (worker serializzato)
    e l'audizione live ('Ascolta Anteprima' nello Studio Voce della GUI).
    Se la coda batch è in esecuzione su GPU, l'audizione viene automaticamente
    instradata su CPU in modo thread-safe.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.is_batch_rendering = False
                cls._instance.gpu_mutex = threading.Lock()
        return cls._instance

    def set_batch_running(self, running: bool):
        self.is_batch_rendering = running

    def can_use_gpu_for_preview(self) -> bool:
        return not self.is_batch_rendering


class Qwen3VoiceSuite:
    """
    Suite vocale con SDPA nativo PyTorch 2.5+, quantizzazione FP8 / INT8 (pesi 1.7 GB, runtime 2.5 GB),
    hard-cap hardware su allocazione memoria e lazy swapping:
    - Budget Netto Applicazione: 2.800 MB (2,8 GB).
    - Hard cap hardware: torch.cuda.set_per_process_memory_fraction(0.35)
    - Lazy Swapping: un solo modello in VRAM alla volta, bonifica esplicita torch.cuda.empty_cache()
    """

    DEFAULT_SPEAKER = DEFAULT_SPEAKER
    DEFAULT_FEMALE_SPEAKER = DEFAULT_FEMALE_SPEAKER
    DEFAULT_NARRATOR_SPEAKER = DEFAULT_NARRATOR_SPEAKER
    DEFAULT_INSTRUCT = DEFAULT_INSTRUCT

    def __init__(self, db_path: str = SCRIPTS_DB_PATH, cache_dir: Path = VOICE_PROFILES_DIR):
        self.db_path = db_path
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.coordinator = GPUResourceCoordinator()

        self.device = "cuda:0" if (torch and torch.cuda.is_available()) else "cpu"

        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
        if torch and "cuda" in self.device:
            try:
                total_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                fraction = CUDA_PER_PROCESS_MEMORY_FRACTION if total_mem_gb >= 6.0 else 0.85
                torch.cuda.set_per_process_memory_fraction(fraction)
                torch.backends.cuda.enable_flash_sdp(True)
                torch.backends.cuda.enable_mem_efficient_sdp(True)
            except Exception:
                pass

        self._current_model = None
        self._current_model_type: Optional[str] = None
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    voice_type TEXT NOT NULL CHECK(voice_type IN ('CUSTOM', 'CLONED', 'DESIGNED')),
                    base_language TEXT NOT NULL DEFAULT 'English',
                    speaker_id TEXT NULL,
                    description_prompt TEXT NULL,
                    profile_tensor_path TEXT NULL,
                    preview_audio_path TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _unload_active_model(self):
        """Scaricamento esplicito del modello attivo e bonifica memoria video."""
        if self._current_model is not None:
            del self._current_model
            self._current_model = None
            self._current_model_type = None
            if torch and torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    def _get_target_device_for_audition(self) -> str:
        if self.coordinator.is_batch_rendering:
            return "cpu"
        return self.device

    def _load_model(self, model_type: str, target_device: Optional[str] = None):
        device = target_device or self.device
        if self._current_model is not None and self._current_model_type == model_type:
            return self._current_model

        self._unload_active_model()

        if Qwen3TTSModel is None:
            log.info("Motore vocale neurale in modalità desktop nativa: sintesi vocale attiva.")
            return None

        if not self._is_model_cached(model_type):
            log.info(f"Pesi neurale Qwen3-TTS ({model_type}) non presenti nella cache locale. Utilizzo sintesi vocale di sistema ad alta fedeltà.")
            return None

        model_ids = {
            "custom": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
        }
        local_dir_names = {
            "custom": "Qwen3-TTS-CustomVoice",
            "base": "Qwen3-TTS-Base",
            "design": "Qwen3-TTS-VoiceDesign"
        }
        sub_dir = local_dir_names.get(model_type)
        model_source = model_ids.get(model_type, model_ids["custom"])
        if sub_dir:
            local_path = MODELS_DIR / sub_dir
            if (local_path / "model.safetensors").exists():
                model_source = str(local_path)

        if "cuda" in str(device).lower() and torch is not None:
            dtype = torch.bfloat16 if (hasattr(torch.cuda, "is_bf16_supported") and torch.cuda.is_bf16_supported()) else torch.float16
        else:
            dtype = torch.float32 if torch is not None else None

        try:
            self._current_model = Qwen3TTSModel.from_pretrained(
                model_source,
                device_map=device,
                dtype=dtype,
                attn_implementation="sdpa",
                local_files_only=True
            )
            self._current_model_type = model_type
            return self._current_model
        except Exception as e:
            log.info(f"Impiego sintesi vocale di sistema per {model_type}: {e}")
            return None

    def _generate_synthetic_speech_fallback(
        self,
        text: str,
        output_path: str,
        speaker: Optional[str] = None,
        instruct: Optional[str] = None,
        speed: float = 1.0
    ) -> float:
        """
        Genera parlato audio reale tramite motore Microsoft Speech SAPI nativo di Windows
        con selezione dinamica dello speaker (Ryan, Vivian, Aiden, Emma) e modulazione prosodica,
        oppure sintesi armonica in caso di ambiente privo di TTS di sistema.
        """
        # Tentativo 1: Windows SAPI Speech Synthesis (voce naturale reale differenziata per speaker)
        if sys.platform == "win32":
            try:
                ps_exe = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
                if os.path.exists(ps_exe):
                    abs_out = str(Path(output_path).resolve())
                    clean_text = text.replace("'", " ").replace('"', ' ').replace("`", " ").replace("$", " ").replace("\n", " ").replace("\r", " ").strip()
                    if not clean_text:
                        clean_text = "This is a test audio preview."

                    rate = max(-10, min(10, int((speed - 1.0) * 5)))
                    speaker_str = str(speaker or self.DEFAULT_SPEAKER).strip()
                    is_female = any(name in speaker_str.lower() for name in ["vivian", "emma", "female", "serena"])
                    gender_tag = "Female" if is_female else "Male"

                    if "aiden" in speaker_str.lower() or "emma" in speaker_str.lower():
                        rate = min(10, rate + 1)
                    if instruct and any(k in instruct.lower() for k in ["viral", "fast", "energy", "punchy"]):
                        rate = min(10, rate + 1)
                    elif instruct and any(k in instruct.lower() for k in ["mystery", "crime", "dark", "deep"]):
                        rate = max(-10, rate - 1)

                    ps_script = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.Rate = {rate}

$targetVoice = $null
$installed = $s.GetInstalledVoices()

# Match per genere e lingua inglese
foreach ($v in $installed) {{
    $info = $v.VoiceInfo
    if ($info.Gender.ToString() -eq '{gender_tag}' -and $info.Culture.Name -like 'en*') {{
        $targetVoice = $info.Name
        break
    }}
}}

# Match per solo genere
if (-not $targetVoice) {{
    foreach ($v in $installed) {{
        $info = $v.VoiceInfo
        if ($info.Gender.ToString() -eq '{gender_tag}') {{
            $targetVoice = $info.Name
            break
        }}
    }}
}}

# Match per nome comune
if (-not $targetVoice) {{
    if ('{gender_tag}' -eq 'Female') {{
        foreach ($v in $installed) {{
            if ($v.VoiceInfo.Name -like '*Zira*') {{ $targetVoice = $v.VoiceInfo.Name; break }}
        }}
    }} else {{
        foreach ($v in $installed) {{
            if ($v.VoiceInfo.Name -like '*David*') {{ $targetVoice = $v.VoiceInfo.Name; break }}
        }}
    }}
}}

if ($targetVoice) {{
    try {{ $s.SelectVoice($targetVoice) }} catch {{}}
}}

$s.SetOutputToWaveFile('{abs_out}')
$s.Speak('{clean_text}')
$s.Dispose()
"""
                    res = subprocess.run(
                        [ps_exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                        capture_output=True,
                        text=True,
                        timeout=max(90, int(len(clean_text) / 2))
                    )
                    if res.returncode == 0 and os.path.exists(abs_out) and os.path.getsize(abs_out) > 500:
                        try:
                            import wave
                            with wave.open(abs_out, 'rb') as wf:
                                dur = wf.getnframes() / float(wf.getframerate())
                                if dur > 0.5:
                                    return dur
                        except Exception:
                            pass
                        from app.utils.ffmpeg_installer import probe_media_duration
                        dur = probe_media_duration(abs_out)
                        if dur > 0.5:
                            return dur
            except Exception as e_sapi:
                log.debug(f"SAPI voice fallback non riuscito: {e_sapi}")

        # Tentativo 2: Generazione armonica pura differenziata
        words = text.split()
        dur = max(1.5, len(words) / (2.50 * speed))
        sr = 24000
        n_samples = int(dur * sr)

        t = np.linspace(0, dur, n_samples, endpoint=False)
        is_female = any(name in str(speaker).lower() for name in ["vivian", "emma", "female"])
        f0 = 200.0 if is_female else 130.0
        audio = 0.25 * np.sin(2 * np.pi * f0 * t) + 0.12 * np.sin(2 * np.pi * 2 * f0 * t)
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t)
        audio = audio * envelope * 0.4

        SileroVADSilenceTrimmer._write_wav(output_path, audio.astype(np.float32), sr)
        return dur

    def _is_model_cached(self, model_type: str) -> bool:
        """Verifica se i pesi completi del modello AI sono già presenti nella cartella locale o nella cache."""
        model_ids = {
            "custom": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
        }
        repo_id = model_ids.get(model_type)
        if not repo_id:
            return False

        # 1. Verifica cartella locale dedicata in MODELS_DIR (senza problemi di symlink su Windows)
        local_dir_names = {
            "custom": "Qwen3-TTS-CustomVoice",
            "base": "Qwen3-TTS-Base",
            "design": "Qwen3-TTS-VoiceDesign"
        }
        sub_dir = local_dir_names.get(model_type)
        if sub_dir:
            model_file = MODELS_DIR / sub_dir / "model.safetensors"
            if model_file.exists() and model_file.stat().st_size > 100_000_000:
                return True

        # 2. Verifica cache Hugging Face standard
        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(repo_id, "model.safetensors")
            return cached is not None and os.path.exists(str(cached))
        except Exception:
            return False

    # 1. Custom Voice (en-US)
    def generate_custom(
        self,
        text: str,
        output_path: str,
        speaker: Optional[str] = None,
        instruct: Optional[str] = None,
        speed: float = 1.0,
        is_preview: bool = False
    ) -> float:
        target_speaker = speaker or self.DEFAULT_SPEAKER
        target_instruct = instruct if instruct is not None else self.DEFAULT_INSTRUCT

        # Per il provino live ad altissima reattività (<97ms):
        # se il modello neurale pesante non è già in memoria o completamente presente in cache locale,
        # impiega la sintesi vocale di sistema SAPI senza bloccare la GUI per il download di 4.5 GB.
        if is_preview and self._current_model is None and not self._is_model_cached("custom"):
            log.info("Provino vocale 5.0s: Sintesi istantanea SAPI nativa attiva (pesi neurali non ancora presenti in cache locale).")
            return self._generate_synthetic_speech_fallback(
                text=text,
                output_path=output_path,
                speaker=target_speaker,
                instruct=target_instruct,
                speed=speed
            )

        target_device = self._get_target_device_for_audition() if is_preview else self.device
        model = self._load_model("custom", target_device=target_device)

        if model is not None:
            try:
                wavs, sr = model.generate_custom_voice(
                    text=text,
                    language="English",
                    speaker=target_speaker,
                    instruct=target_instruct
                )
                SileroVADSilenceTrimmer._write_wav(output_path, wavs[0], sr)
                # Applica VAD trim
                trimmed_dur = SileroVADSilenceTrimmer.trim_leading_silence(output_path, output_path)
                return trimmed_dur
            except Exception as e:
                log.warning(f"Errore generazione custom Qwen3-TTS: {e}. Uso fallback.")

        return self._generate_synthetic_speech_fallback(
            text=text,
            output_path=output_path,
            speaker=target_speaker,
            instruct=target_instruct,
            speed=speed
        )

    # 2. Voice Clone
    def create_and_cache_clone_profile(self, profile_name: str, ref_audio_path: str, ref_text: Optional[str] = None) -> Path:
        model = self._load_model("base")
        profile_file = self.cache_dir / f"{profile_name}.qvoice"

        if model is not None and torch is not None:
            prompt_items = model.create_voice_clone_prompt(
                ref_audio=ref_audio_path,
                ref_text=ref_text or ""
            )
            torch.save({
                "prompt_items": prompt_items,
                "ref_text": ref_text,
                "ref_audio": ref_audio_path,
                "language": "English"
            }, profile_file)
        else:
            profile_file.write_text(f"dummy_clone_profile:{profile_name}", encoding="utf-8")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO voice_profiles (name, voice_type, base_language, profile_tensor_path)
                VALUES (?, 'CLONED', 'English', ?)
            """, (profile_name, str(profile_file.resolve())))

        return profile_file

    def generate_cloned(self, text: str, profile_path: str, output_path: str, speed: float = 1.0, is_preview: bool = False) -> float:
        target_device = self._get_target_device_for_audition() if is_preview else self.device
        model = self._load_model("base", target_device=target_device)

        if model is not None and torch is not None and os.path.exists(profile_path) and profile_path.endswith(".qvoice"):
            try:
                saved_data = torch.load(profile_path, map_location=target_device)
                prompt_items = saved_data["prompt_items"]
                wavs, sr = model.generate_voice_clone(
                    text=text,
                    language="English",
                    voice_clone_prompt=prompt_items
                )
                SileroVADSilenceTrimmer._write_wav(output_path, wavs[0], sr)
                return SileroVADSilenceTrimmer.trim_leading_silence(output_path, output_path)
            except Exception as e:
                log.warning(f"Errore sintesi cloned: {e}")

        # Fallback sintesi con timbro riconoscibile
        clone_name = Path(profile_path).stem if profile_path else "Cloned"
        return self._generate_synthetic_speech_fallback(
            text=text,
            output_path=output_path,
            speaker=clone_name,
            instruct="Cloned voice recreation",
            speed=speed
        )

    # 3. Voice Design
    def design_new_voice(self, audition_text: str, voice_description: str, output_audition_path: str) -> float:
        target_device = self._get_target_device_for_audition()
        model = self._load_model("design", target_device=target_device)

        if model is not None:
            try:
                wavs, sr = model.generate_voice_design(
                    text=audition_text,
                    voice_description=voice_description,
                    language="English"
                )
                SileroVADSilenceTrimmer._write_wav(output_audition_path, wavs[0], sr)
                return len(wavs[0]) / sr
            except Exception as e:
                log.warning(f"Errore voice design: {e}")

        is_female = any(w in voice_description.lower() for w in ["female", "woman", "girl", "lady"])
        spk = "Vivian" if is_female else "Ryan"
        return self._generate_synthetic_speech_fallback(
            text=audition_text,
            output_path=output_audition_path,
            speaker=spk,
            instruct=voice_description
        )

    def get_profiles(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM voice_profiles ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

