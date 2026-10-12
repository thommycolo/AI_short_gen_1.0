"""AI Short Generator 1.0 - Modular TTS Package"""

from app.core.tts.base import BaseTTSProvider, TTSVoiceConfig, TTSAudioResult, VoiceInfo
from app.core.tts.factory import TTSFactory
from app.core.tts.quota_tracker import QuotaTracker, QuotaSafeguardExceededError
from app.core.tts.key_manager import APIKeyManager
from app.core.tts.gemini_provider import GeminiTTSProvider
from app.core.tts.system_provider import SystemTTSProvider

# Registrazione automatica dei provider disponibili
TTSFactory.register("gemini_tts", GeminiTTSProvider)
TTSFactory.register("system_tts", SystemTTSProvider)

# Impostazione provider di default
TTSFactory.set_default_provider("gemini_tts")

__all__ = [
    "BaseTTSProvider",
    "TTSVoiceConfig",
    "TTSAudioResult",
    "VoiceInfo",
    "TTSFactory",
    "QuotaTracker",
    "QuotaSafeguardExceededError",
    "APIKeyManager",
    "GeminiTTSProvider",
    "SystemTTSProvider",
]

