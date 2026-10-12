"""AI Short Generator 1.0 - System / Offline TTS Provider (Windows SAPI / Synthetic)"""

import os
import sys
import subprocess
import numpy as np
from pathlib import Path
from typing import List, Optional

from app.core.tts.base import BaseTTSProvider, TTSVoiceConfig, TTSAudioResult, VoiceInfo
from app.utils.logger import log


class SystemTTSProvider(BaseTTSProvider):
    DISPLAY_NAME = "Microsoft Windows Speech (SAPI / Offline)"

    VOICES = [
        VoiceInfo("David", "Microsoft David (English Male)", "male", "en-US", "Desktop Offline Male Voice"),
        VoiceInfo("Zira", "Microsoft Zira (English Female)", "female", "en-US", "Desktop Offline Female Voice"),
    ]

    @property
    def provider_id(self) -> str:
        return "system_tts"

    @property
    def display_name(self) -> str:
        return self.DISPLAY_NAME

    def get_available_voices(self) -> List[VoiceInfo]:
        return self.VOICES

    def validate_credentials(self) -> bool:
        return True

    def synthesize(self, text: str, config: TTSVoiceConfig, output_path: str) -> TTSAudioResult:
        clean_text = text.strip()
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        success = self._synthesize_sapi(clean_text, str(out_p))
        if not success:
            self._synthesize_sine_fallback(clean_text, str(out_p))

        # Calcola durata
        duration = 3.0
        try:
            import soundfile as sf
            data, sr = sf.read(str(out_p))
            duration = float(len(data) / sr)
        except Exception:
            pass

        return TTSAudioResult(
            output_path=str(out_p),
            duration_sec=duration,
            characters_used=len(clean_text),
            tokens_used=int(len(clean_text) / 4),
            provider_name=self.provider_id,
            sample_rate=24000
        )

    def _synthesize_sapi(self, text: str, output_path: str) -> bool:
        if sys.platform != "win32":
            return False
        try:
            escaped = text.replace("'", "''").replace('"', '""')
            out_esc = output_path.replace("'", "''")
            ps_script = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.SetOutputToWaveFile('{out_esc}'); "
                f"$s.Speak('{escaped}'); "
                f"$s.Dispose();"
            )
            res = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                timeout=20
            )
            return res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 100
        except Exception as e:
            log.warning(f"SAPI non disponibile: {e}")
            return False

    def _synthesize_sine_fallback(self, text: str, output_path: str):
        import soundfile as sf
        words = len(text.split())
        est_dur = max(2.0, float(words) / 2.5)
        sr = 24000
        t = np.linspace(0, est_dur, int(sr * est_dur), endpoint=False)
        audio = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        sf.write(output_path, audio, sr)

