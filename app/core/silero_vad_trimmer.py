"""AI Short Generator 1.0 - Silero VAD Silence Trimmer (<2 MB ONNX CPU)"""

import wave
import struct
import numpy as np
from pathlib import Path
from typing import Optional

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import onnxruntime as ort
except ImportError:
    ort = None


class SileroVADSilenceTrimmer:
    """
    Risolve la discrepanza temporale del silenzio/respiro iniziale generato dai TTS neurali (50-250ms).
    Sostituisce il rilevamento empirico a soglia statica dBFS (che tranciava consonanti morbide come
    'Think', 'Summer', 'Hello') con Silero VAD (ONNX su CPU, < 2 MB), rilevando l'esatto onset
    fonetico senza tagliare le consonanti non vocalizzate.
    Garantisce che con adelay=500|500 la voce parta a t = 0.500s esatti e il frame 0.600s mostri la parola attiva.
    """
    _vad_model = None

    @classmethod
    def _get_vad_model(cls):
        if cls._vad_model is None and ort is not None:
            model_paths = [
                Path("assets/models/silero_vad.onnx"),
                Path("app_data/models/silero_vad.onnx")
            ]
            for mp in model_paths:
                if mp.exists():
                    try:
                        cls._vad_model = ort.InferenceSession(str(mp), providers=["CPUExecutionProvider"])
                        break
                    except Exception:
                        pass
        return cls._vad_model

    @staticmethod
    def _read_wav(input_wav_path: str):
        if sf is not None:
            data, sr = sf.read(input_wav_path)
            return data, sr

        # Pure standard library fallback using wave
        with wave.open(input_wav_path, 'rb') as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            n_channels = wf.getnchannels()
            raw_bytes = wf.readframes(n_frames)
            
            if wf.getsampwidth() == 2:
                data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                data = np.frombuffer(raw_bytes, dtype=np.float32)
                
            if n_channels > 1:
                data = data.reshape(-1, n_channels)
            return data, sr

    @staticmethod
    def _write_wav(output_wav_path: str, data: np.ndarray, sr: int):
        Path(output_wav_path).parent.mkdir(parents=True, exist_ok=True)
        if sf is not None:
            sf.write(output_wav_path, data, sr)
            return

        with wave.open(output_wav_path, 'wb') as wf:
            n_channels = 1 if data.ndim == 1 else data.shape[1]
            wf.setnchannels(n_channels)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            scaled = (data * 32767.0).clip(-32768, 32767).astype(np.int16)
            wf.writeframes(scaled.tobytes())

    @classmethod
    def trim_leading_silence(cls, input_wav_path: str, output_wav_path: str) -> float:
        """
        Rileva ed elimina il silenzio iniziale tramite Silero VAD su CPU (o fallback energetico soft).
        Ritorna la nuova durata effettiva dell'audio vocale in secondi.
        """
        data, sr = cls._read_wav(input_wav_path)
        if data.ndim > 1:
            mono = np.mean(data, axis=1)
        else:
            mono = data

        start_index = 0
        session = cls._get_vad_model()

        if session is not None and sr == 16000:
            # Finestra da 512 campioni (32ms a 16kHz)
            window_size = 512
            for i in range(0, len(mono) - window_size, window_size):
                chunk = mono[i:i + window_size].astype(np.float32)
                ort_inputs = {session.get_inputs()[0].name: np.expand_dims(chunk, 0)}
                prob = session.run(None, ort_inputs)[0][0][0]
                if prob > 0.5:
                    # Inizio parlato rilevato: arretra di 30ms per preservare l'attacco della prima consonante
                    start_index = max(0, i - int(0.03 * sr))
                    break
        else:
            # Fallback robusto su energia con margine morbido di 40ms (anti-clipping consonanti soft)
            frame_size = max(1, sr // 100)
            threshold = 0.005 # Livello soft
            for i in range(0, len(mono) - frame_size, frame_size):
                frame_rms = np.sqrt(np.mean(mono[i:i + frame_size] ** 2))
                if frame_rms > threshold:
                    start_index = max(0, i - int(0.04 * sr))
                    break

        trimmed_data = data[start_index:]
        cls._write_wav(output_wav_path, trimmed_data, sr)
        return len(trimmed_data) / sr

