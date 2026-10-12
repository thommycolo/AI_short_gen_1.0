"""AI Short Generator 1.0 - Core TTS Architecture (Base Strategy & Dataclasses)"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class VoiceInfo:
    id: str
    name: str
    gender: str
    language: str
    description: str
    supports_styles: bool = False


@dataclass
class TTSVoiceConfig:
    voice_id: str = "Puck"
    language_code: str = "en-US"
    speed: float = 1.00          # 0.5x - 2.0x
    pitch: float = 0.0           # Semitones (-20.0 to +20.0)
    volume_gain_db: float = 0.0  # Decibels (-10 dB to +10 dB)
    style_prompt: Optional[str] = "High energy viral creator voice, fast paced, emphasizing keywords"
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTSAudioResult:
    output_path: str
    duration_sec: float
    characters_used: int
    tokens_used: int
    provider_name: str
    sample_rate: int = 24000


class BaseTTSProvider(ABC):
    """Interfaccia base (Strategy Pattern) per qualsiasi motore TTS."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Identificatore univoco del provider (es. 'gemini_tts', 'system_tts')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Nome formattato mostrato nell'interfaccia utente."""
        pass

    @abstractmethod
    def synthesize(self, text: str, config: TTSVoiceConfig, output_path: str) -> TTSAudioResult:
        """Sintetizza il testo e scrive il file audio WAV su disco."""
        pass

    @abstractmethod
    def get_available_voices(self) -> List[VoiceInfo]:
        """Restituisce le voci disponibili per questo provider."""
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Verifica se le credenziali/chiave API sono configurate e valide."""
        pass

