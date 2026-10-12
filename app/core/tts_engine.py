"""AI Short Generator 1.0 - Modular Voice Intelligence Engine (Gemini TTS & Multi-Provider Architecture)"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.config import (
    DEFAULT_SPEAKER, DEFAULT_FEMALE_SPEAKER, DEFAULT_NARRATOR_SPEAKER,
    DEFAULT_INSTRUCT, CACHE_DIR, APP_DATA_DIR
)
from app.core.tts.base import TTSVoiceConfig, TTSAudioResult
from app.core.tts.factory import TTSFactory
from app.core.tts.quota_tracker import QuotaTracker, QuotaSafeguardExceededError
from app.core.tts.key_manager import APIKeyManager
from app.core.silero_vad_trimmer import SileroVADSilenceTrimmer
from app.utils.logger import log


class GPUResourceCoordinator:
    """
    Coordinatore risorse legacy. Con i provider Cloud TTS (Gemini), l'impatto VRAM è nullo (0 MB),
    eliminando la contesa con Faster-Whisper e l'encoding NVENC.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.is_batch_rendering = False
        return cls._instance

    def set_batch_running(self, running: bool):
        self.is_batch_rendering = running

    def can_use_gpu_for_preview(self) -> bool:
        return True


class VoiceIntelligenceEngine:
    """
    Motore di orchestrazione vocale modulare di AI Short Generator 1.0.
    Supporta Gemini Expressive TTS e provider multipli tramite Factory/Strategy pattern.
    """

    DEFAULT_SPEAKER = DEFAULT_SPEAKER
    DEFAULT_FEMALE_SPEAKER = DEFAULT_FEMALE_SPEAKER
    DEFAULT_NARRATOR_SPEAKER = DEFAULT_NARRATOR_SPEAKER
    DEFAULT_INSTRUCT = DEFAULT_INSTRUCT

    def __init__(self, default_provider_id: str = "gemini_tts"):
        self.default_provider_id = default_provider_id
        self.quota_tracker = QuotaTracker()
        self.coordinator = GPUResourceCoordinator()
        self.vad_trimmer = SileroVADSilenceTrimmer()

    def generate_custom(
        self,
        text: str,
        output_path: str,
        speaker: Optional[str] = None,
        instruct: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 0.0,
        temperature: float = 0.70,
        is_preview: bool = False,
        provider_id: Optional[str] = None,
        volume_gain_db: float = 0.0
    ) -> float:
        """
        Genera l'audio sintetizzato utilizzando il provider configurato.
        Ritorna la durata in secondi dell'audio generato e trimmato con Silero VAD.
        """
        clean_text = text.strip()
        if not clean_text:
            return 0.0

        target_provider = (provider_id or self.default_provider_id).lower()
        target_speaker = speaker or self.DEFAULT_SPEAKER
        target_instruct = instruct if instruct is not None else self.DEFAULT_INSTRUCT

        # Mappatura compatibilità vecchi speaker Qwen -> Gemini
        legacy_speaker_map = {
            "ryan": "Puck",
            "aiden": "Charon",
            "vivian": "Kore",
            "serena": "Aoede",
            "dylan": "Fenrir",
            "eric": "Puck",
            "ono_anna": "Kore",
            "sohee": "Aoede",
            "uncle_fu": "Charon"
        }
        spk_key = str(target_speaker).strip().lower()
        if spk_key in legacy_speaker_map:
            target_speaker = legacy_speaker_map[spk_key]

        cfg = TTSVoiceConfig(
            voice_id=target_speaker,
            language_code="en-US",
            speed=float(speed or 1.0),
            pitch=float(pitch or 0.0),
            volume_gain_db=float(volume_gain_db or 0.0),
            style_prompt=target_instruct,
            extra_params={"temperature": temperature, "is_preview": is_preview}
        )

        try:
            # 1. Istanziazione provider primario (es. Gemini)
            tts_provider = TTSFactory.create(target_provider)

            # Verifica preventiva chiave se Gemini
            if target_provider == "gemini_tts" and not APIKeyManager.has_api_key("gemini"):
                if is_preview:
                    # In anteprima rapida senza chiave, usa fallback di sistema trasparente
                    log.warning("[TTS] API Key non configurata: fallback automatico su sintesi locale di sistema.")
                    tts_provider = TTSFactory.create("system_tts")
                else:
                    # In fase di produzione batch, richiede la chiave
                    APIKeyManager.get_api_key("gemini", allow_interactive=True)

            raw_temp_path = str(Path(output_path).with_suffix(".raw.wav"))
            result: TTSAudioResult = tts_provider.synthesize(clean_text, cfg, raw_temp_path)

            # 2. Rifinitura acustica Silero VAD (rimozione micro-silenzi di attacco e stacco)
            final_duration = self._trim_silence_and_finalize(raw_temp_path, output_path)
            return final_duration

        except QuotaSafeguardExceededError as q_err:
            log.error(f"[TTS] {q_err}")
            raise
        except Exception as e:
            log.warning(f"[TTS] Errore generazione con provider '{target_provider}': {e}. Fallback su sintesi di sistema...")
            # Fallback resiliente di sistema per non bloccare la pipeline
            try:
                fallback_provider = TTSFactory.create("system_tts")
                fallback_res = fallback_provider.synthesize(clean_text, cfg, output_path)
                return fallback_res.duration_sec
            except Exception as e_fallback:
                log.error(f"[TTS] Anche il fallback di sistema è fallito: {e_fallback}")
                raise RuntimeError(f"Generazione vocale fallita: {e}") from e

    def _trim_silence_and_finalize(self, temp_wav: str, final_wav: str) -> float:
        """Rimuove silenzi con Silero VAD e garantisce salvataggio in final_wav."""
        if not os.path.exists(temp_wav):
            return 0.0

        try:
            # Silero VAD trimming
            duration = SileroVADSilenceTrimmer.trim_leading_silence(temp_wav, final_wav)
            if os.path.exists(temp_wav) and os.path.abspath(temp_wav) != os.path.abspath(final_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
            return duration
        except Exception as e:
            log.warning(f"[TTS] Silero VAD trimming non applicato: {e}")

        # Se il trimming fallisce o non modifica il file, sposta temp in final
        if os.path.abspath(temp_wav) != os.path.abspath(final_wav):
            if os.path.exists(final_wav):
                os.remove(final_wav)
            os.rename(temp_wav, final_wav)

        try:
            import soundfile as sf
            data, sr = sf.read(final_wav)
            return float(len(data) / sr)
        except Exception:
            return 3.0

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Restituisce l'elenco delle voci disponibili dal provider attivo."""
        provider = TTSFactory.create(self.default_provider_id)
        voices = provider.get_available_voices()
        return [
            {
                "id": v.id,
                "name": v.name,
                "gender": v.gender,
                "language": v.language,
                "description": v.description
            }
            for v in voices
        ]


# Alias retrocompatibilità per il resto dell'applicazione
Qwen3VoiceSuite = VoiceIntelligenceEngine
