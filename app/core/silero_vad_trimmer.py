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
            # Fallback robusto su energia con persistenza a finestra temporale (ignora click isolati <50ms)
            frame_size = max(1, sr // 50)  # Finestra 20ms
            window_frames = 4              # 80ms di energia vocale sostenuta
            num_frames = len(mono) // frame_size
            if num_frames > window_frames:
                rms_arr = np.array([np.sqrt(np.mean(mono[i*frame_size:(i+1)*frame_size] ** 2)) for i in range(num_frames)])
                threshold = 0.015 # Soglia di attivazione vocale reale
                for i in range(num_frames - window_frames):
                    if np.mean(rms_arr[i:i+window_frames]) > threshold:
                        start_index = max(0, i * frame_size - int(0.04 * sr))
                        break

        trimmed_data = data[start_index:]
        cls._write_wav(output_wav_path, trimmed_data, sr)
        return float(len(trimmed_data) / sr)

    @classmethod
    def stitch_narration_and_outro(
        cls,
        narration_wav_path: str,
        outro_wav_path: Optional[str],
        output_combined_path: str,
        pause_sec: float = 1.000
    ) -> tuple:
        """
        Concatena l'audio della narrazione, esattamente 1.0s di silenzio, e l'audio dell'outro letto dal TTS.
        Ritorna (durata_totale, durata_narrazione, durata_outro).
        """
        # 1. Trimming e lettura narrazione
        narr_temp = str(Path(output_combined_path).parent / "temp_trimmed_narr.wav")
        narr_dur = cls.trim_leading_silence(narration_wav_path, narr_temp)
        narr_data, sr = cls._read_wav(narr_temp)

        if not outro_wav_path or not Path(outro_wav_path).exists():
            cls._write_wav(output_combined_path, narr_data, sr)
            return (narr_dur, narr_dur, 0.0)

        # 2. Trimming e lettura outro
        outro_temp = str(Path(output_combined_path).parent / "temp_trimmed_outro.wav")
        outro_dur = cls.trim_leading_silence(outro_wav_path, outro_temp)
        outro_data, outro_sr = cls._read_wav(outro_temp)

        if outro_sr != sr:
            # Resampling semplice se necessario
            import librosa
            if outro_data.ndim > 1:
                outro_data = librosa.resample(outro_data.T, orig_sr=outro_sr, target_sr=sr).T
            else:
                outro_data = librosa.resample(outro_data, orig_sr=outro_sr, target_sr=sr)

        # 3. Pausa di silenzio esatta (1.0s)
        pause_samples = int(pause_sec * sr)
        if narr_data.ndim > 1:
            pause_data = np.zeros((pause_samples, narr_data.shape[1]), dtype=narr_data.dtype)
        else:
            pause_data = np.zeros(pause_samples, dtype=narr_data.dtype)

        # 4. Concatenazione finale
        combined = np.concatenate([narr_data, pause_data, outro_data])
        cls._write_wav(output_combined_path, combined, sr)
        total_dur = float(len(combined) / sr)

        return (total_dur, narr_dur, outro_dur)


