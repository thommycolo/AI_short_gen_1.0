"""AI Short Generator 1.0 - Gemini Expressive TTS Provider (google-genai SDK)"""

import os
import io
import wave
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.core.tts.base import BaseTTSProvider, TTSVoiceConfig, TTSAudioResult, VoiceInfo
from app.core.tts.quota_tracker import QuotaTracker
from app.core.tts.key_manager import APIKeyManager
from app.utils.logger import log

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GeminiTTSProvider(BaseTTSProvider):
    DISPLAY_NAME = "Gemini Expressive TTS (Google AI Studio)"

    # Voci native ad alta fedeltà di Google Gemini
    SUPPORTED_VOICES = [
        VoiceInfo(
            id="Puck",
            name="Puck (Energetic & Dynamic Male)",
            gender="male",
            language="en-US",
            description="Dynamic, engaging American male voice with strong rhythmic delivery",
            supports_styles=True
        ),
        VoiceInfo(
            id="Charon",
            name="Charon (Authoritative & Deep Male)",
            gender="male",
            language="en-US",
            description="Deep, resonant, calm and informative authoritative timbre",
            supports_styles=True
        ),
        VoiceInfo(
            id="Kore",
            name="Kore (Bright & Warm Female)",
            gender="female",
            language="en-US",
            description="Warm, clear and conversational natural American female voice",
            supports_styles=True
        ),
        VoiceInfo(
            id="Fenrir",
            name="Fenrir (Intense & Dramatic Male)",
            gender="male",
            language="en-US",
            description="Fast-paced, high-tension storytelling narrator voice",
            supports_styles=True
        ),
        VoiceInfo(
            id="Aoede",
            name="Aoede (Expressive & Emotional Female)",
            gender="female",
            language="en-US",
            description="Expressive, gentle and emotional voice with rich nuance",
            supports_styles=True
        ),
    ]

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.8-flash-tts"):
        self.quota_tracker = QuotaTracker()
        self.model_name = model_name
        self._explicit_key = api_key
        self._client: Optional[Any] = None

    @property
    def provider_id(self) -> str:
        return "gemini_tts"

    @property
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        if genai is None:
            raise ImportError("Modulo 'google-genai' non installato. Esegui 'pip install google-genai'.")

        key = self._explicit_key or APIKeyManager.get_api_key("gemini", allow_interactive=True)
        if not key:
            raise ValueError("Chiave API Google/Gemini non presente o non valida.")

        self._client = genai.Client(api_key=key)
        return self._client

    def get_available_voices(self) -> List[VoiceInfo]:
        return self.SUPPORTED_VOICES

    def validate_credentials(self) -> bool:
        """Verifica la validità della chiave API con una chiamata minima al modello TTS."""
        try:
            client = self._get_client()
            resp = client.models.generate_content(
                model=self.model_name,
                contents=[{
                    "role": "user",
                    "parts": [{"text": "Hello"}]
                }],
                config={
                    "response_modalities": ["AUDIO"],
                    "speech_config": {
                        "voice_config": {"voice": "Puck"}
                    }
                }
            )
            return resp is not None and bool(resp.candidates)
        except Exception as e:
            log.warning(f"[GeminiTTS] Validazione API Key non riuscita con {self.model_name}: {e}")
            return False

    def synthesize(self, text: str, config: TTSVoiceConfig, output_path: str) -> TTSAudioResult:
        """
        Sintetizza il testo utilizzando il modello vocale Gemini 3.8 Flash TTS.
        Blocca automaticamente se viene superata la soglia di sicurezza del 95%.
        """
        clean_text = text.strip()
        text_len = len(clean_text)
        if not clean_text:
            raise ValueError("Il testo da sintetizzare non può essere vuoto.")

        # 1. Quota Tracking & Safeguard (Blocco al 95%)
        self.quota_tracker.check_and_reserve(self.provider_id, text_len)

        # 2. Risoluzione parametri voce
        valid_voice_ids = {v.id for v in self.SUPPORTED_VOICES}
        voice_id = config.voice_id if config.voice_id in valid_voice_ids else "Puck"
        style_prompt = config.style_prompt or "High energy viral creator voice, fast paced, emphasizing keywords"

        log.info(f"[GeminiTTS] Richiesta sintesi ({text_len} car.) con {self.model_name}: voce '{voice_id}', stile '{style_prompt[:40]}...'")

        client = self._get_client()

        # 3. Invio richiesta API a Gemini TTS (gemini-3.8-flash-tts)
        request_contents = [{
            "role": "user",
            "parts": [{
                "text": clean_text,
                "speech_metadata": {"style": style_prompt}
            }]
        }]
        gen_config = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "voice": voice_id
                }
            }
        }

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=request_contents,
                config=gen_config
            )
        except Exception as e:
            # Se il modello primario fallisce, prova fallback su gemini-3.8-flash-lite-tts
            fallback_model = "gemini-3.8-flash-lite-tts"
            log.warning(f"[GeminiTTS] Errore con {self.model_name}: {e}. Tentativo con {fallback_model}...")
            try:
                response = client.models.generate_content(
                    model=fallback_model,
                    contents=request_contents,
                    config=gen_config
                )
            except Exception as e2:
                log.error(f"[GeminiTTS] Errore critico generazione Gemini TTS: {e2}")
                raise RuntimeError(f"Errore Gemini TTS: {e2}") from e2

        # 4. Estrazione e salvataggio audio
        audio_bytes = None
        mime_type = "audio/wav"

        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    audio_bytes = part.inline_data.data
                    mime_type = getattr(part.inline_data, "mime_type", "audio/wav") or "audio/wav"
                    break

        if not audio_bytes:
            raise RuntimeError("Nessun flusso audio restituito da Gemini API.")

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        self._save_audio_stream(audio_bytes, mime_type, str(out_path))

        # 5. Post-elaborazione acustica dinamica (pitch, speed, volume gain)
        duration_sec = self._apply_acoustic_adjustments(str(out_path), config)

        # 6. Registrazione atomica consumo quota
        token_est = max(1, text_len // 4)
        self.quota_tracker.record_usage(self.provider_id, text_len, tokens_count=token_est)

        log.info(f"[GeminiTTS] Generazione completata con successo ({duration_sec:.2f}s) in {out_path.name}")

        return TTSAudioResult(
            output_path=str(out_path),
            duration_sec=duration_sec,
            characters_used=text_len,
            tokens_used=token_est,
            provider_name=self.provider_id,
            sample_rate=24000
        )

    def _save_audio_stream(self, data: bytes, mime_type: str, out_path: str):
        """Salva i dati su file assicurando un formato WAV valido (se PCM raw, incapsula header RIFF)."""
        is_riff = len(data) >= 4 and data[:4] == b"RIFF"
        is_mp3 = len(data) >= 3 and (data[:3] == b"ID3" or data[:2] == b"\xff\xfb")

        if is_riff:
            with open(out_path, "wb") as f:
                f.write(data)
            return

        if is_mp3 or "mp3" in mime_type.lower():
            # Converte mp3 in wav tramite soundfile / ffmpeg
            tmp_mp3 = Path(out_path).with_suffix(".temp.mp3")
            with open(tmp_mp3, "wb") as f:
                f.write(data)
            try:
                import soundfile as sf
                audio_arr, sr = sf.read(str(tmp_mp3))
                sf.write(out_path, audio_arr, sr)
            finally:
                if tmp_mp3.exists():
                    tmp_mp3.unlink()
            return

        # Tratta come PCM raw 16-bit 24kHz mono (default Gemini Live / TTS PCM)
        try:
            with wave.open(out_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2) # 16-bit
                wf.setframerate(24000)
                wf.writeframes(data)
        except Exception:
            # Fallback scrittura binaria diretta
            with open(out_path, "wb") as f:
                f.write(data)

    def _apply_acoustic_adjustments(self, wav_path: str, config: TTSVoiceConfig) -> float:
        """Applica regolazioni parametriche su pitch, volume e velocità se impostate dall'utente."""
        try:
            import soundfile as sf
            data, sr = sf.read(wav_path)
            modified = False

            # 1. Pitch shifting
            if abs(config.pitch) >= 0.05:
                try:
                    import librosa
                    data = librosa.effects.pitch_shift(data.astype(np.float32), sr=sr, n_steps=float(config.pitch))
                    modified = True
                except Exception as e:
                    log.warning(f"[GeminiTTS] Pitch shift fallito: {e}")

            # 2. Volume Gain (dB)
            if abs(config.volume_gain_db) >= 0.1:
                gain_linear = 10.0 ** (float(config.volume_gain_db) / 20.0)
                data = data * gain_linear
                modified = True

            # 3. Speed / Speaking Rate
            if abs(config.speed - 1.0) >= 0.02:
                try:
                    import librosa
                    data = librosa.effects.time_stretch(data.astype(np.float32), rate=float(config.speed))
                    modified = True
                except Exception as e:
                    log.warning(f"[GeminiTTS] Time stretch fallito: {e}")

            if modified:
                # Normalizza per evitare distorsioni e clipping
                peak = np.max(np.abs(data))
                if peak > 0.98:
                    data = data * (0.98 / peak)
                sf.write(wav_path, data, sr)

            return float(len(data) / sr)
        except Exception as e:
            log.warning(f"[GeminiTTS] Errore calcolo durata/post-processing: {e}")
            return 3.0

